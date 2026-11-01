"""Synthetic regressions for observed Boot named-bean condition grammar."""

from dataclasses import replace

import pytest

from spring_runtime_mcp.adapters.conditions import normalize_conditions
from spring_runtime_mcp.analyzers.condition_failures import analyze_missing_beans
from spring_runtime_mcp.models.common import AnalysisBudget, ParsedObservation
from test_condition_failures import fixture, observation, setup_case


def named_report(message, *, outcome="notMatched", condition="OnBeanCondition"):
    branches = {"positiveMatches": {}, "negativeMatches": {}}
    row = {"condition": condition, "message": message}
    if outcome == "matched":
        branches["positiveMatches"]["example.Consumer#consumer"] = [row]
    else:
        branches["negativeMatches"]["example.Consumer#consumer"] = {
            "matched": [],
            "notMatched": [row],
        }
    return normalize_conditions(
        observation({"contexts": {"application": branches}}), budget=AnalysisBudget()
    )


def missing(name="syntheticFeature", kind="Bean", search="all"):
    return (
        f"@ConditionalOn{kind} (names: {name}; SearchStrategy: {search}) "
        f"did not find any beans named {name}"
    )


@pytest.mark.parametrize("search", ["all", "current", "parents"])
@pytest.mark.parametrize("name", ["syntheticFeature", "synthetic-feature"])
def test_single_named_missing_is_explicit_evidence(name, search):
    report = named_report(missing(name, search=search))
    node = next(iter(report.nodes.values()))
    assert node.reason_code == "REQUIRED_BEAN_MISSING"
    assert node.derived_outcome == "notMatched"
    assert node.required_names == (name,)
    assert node.required_types == ()
    assert node.search == search.upper()
    assert node.children_complete
    assert report.coverage == "complete"
    assert not hasattr(node, "message")


def test_named_missingbean_direction_and_report_conflict():
    report = named_report(missing(kind="MissingBean"), outcome="matched")
    node = next(iter(report.nodes.values()))
    assert node.derived_outcome == "matched"
    assert node.reason_code == "CONDITION_MATCH"
    conflict = named_report(missing(), outcome="matched")
    assert "CONDITION_PARSE_CONFLICT" in conflict.gaps
    assert not next(iter(conflict.nodes.values())).children_complete


@pytest.mark.parametrize(
    "message,condition",
    [
        (
            missing().replace("named syntheticFeature", "named otherFeature"),
            "OnBeanCondition",
        ),
        (
            missing().replace("names: syntheticFeature", "types: syntheticFeature"),
            "OnBeanCondition",
        ),
        (
            missing().replace(
                "names: syntheticFeature", "names: syntheticFeature, other"
            ),
            "OnBeanCondition",
        ),
        (
            missing().replace(
                "names: syntheticFeature",
                "names: syntheticFeature; types: example.Feature",
            ),
            "OnBeanCondition",
        ),
        (missing() + " trailing", "OnBeanCondition"),
        (missing()[:-1], "OnBeanCondition"),
        (missing("x" * 257), "OnBeanCondition"),
        (missing("x" * 9000), "OnBeanCondition"),
        (missing(), "example.OtherCondition"),
        (missing(), None),
        (missing("bad#type"), "OnBeanCondition"),
    ],
)
def test_unproven_named_requirement_stays_unknown(message, condition):
    report = named_report(message, condition=condition)
    node = next(iter(report.nodes.values()))
    assert node.derived_outcome == "unknown"
    assert not node.children_complete
    assert report.coverage == "partial"


@pytest.mark.parametrize(
    "message,outcome,reason",
    [
        (
            "@ConditionalOnBean (types: example.Feature; SearchStrategy: all) did not find any beans of type example.Feature",
            "notMatched",
            "REQUIRED_BEAN_MISSING",
        ),
        (
            "@ConditionalOnBean (names: syntheticFeature; SearchStrategy: all) found bean 'syntheticFeature'",
            "matched",
            "CONDITION_MATCH",
        ),
        (
            "@ConditionalOnMissingBean (names: syntheticFeature; SearchStrategy: all) found bean 'syntheticFeature'",
            "notMatched",
            "BEAN_PRESENT",
        ),
    ],
)
def test_existing_type_and_positive_grammars_preserved(message, outcome, reason):
    node = next(iter(named_report(message, outcome=outcome).nodes.values()))
    assert node.reason_code == reason
    assert node.derived_outcome == outcome
    assert node.children_complete


def test_named_requirement_uses_existing_factory_property_chain():
    query, graph, _, catalog, budget = setup_case()
    payload = fixture("stripe-missing/conditions.json")
    row = payload["contexts"]["application"]["negativeMatches"][
        "example.StripePaymentGateway"
    ]["notMatched"][0]
    row["message"] = missing("stripeApiClient")  # Catalog alias, not a type.
    report = normalize_conditions(observation(payload), budget=budget)
    result = analyze_missing_beans(query, graph, report, catalog, budget=budget)
    nodes = {node.id: node for node in result.conditions}
    assert result.state == "explained", result.gaps
    assert [nodes[n].reason_code for n in result.blocking_paths[0]] == [
        "REQUIRED_BEAN_MISSING",
        "SOURCE_FACTORY_NOT_CREATED",
        "PROPERTY_NOT_FOUND",
    ]
    assert all(not node.child_ids for node in result.conditions)
    # The same name observed at runtime contradicts evaluation-time absence.
    from spring_runtime_mcp.adapters.beans import normalize_beans

    beans = fixture("parent-child/beans.json")
    beans["contexts"]["application"]["beans"]["clientForConflict"] = {
        "type": "example.StripeClient",
        "aliases": ["stripeApiClient"],
        "scope": "singleton",
        "dependencies": [],
    }
    runtime = normalize_beans(observation(beans, "beans"), budget=AnalysisBudget())
    conflict = analyze_missing_beans(
        query, runtime, report, catalog, budget=AnalysisBudget()
    )
    assert "CONDITION_RUNTIME_CONFLICT" in conflict.gaps
    assert not conflict.blocking_paths
    assert conflict.state == "partial"


def test_named_type_and_source_validation_remain_separate():
    malformed = "@ConditionalOnBean (types: example.Bad-Type; SearchStrategy: all) did not find any beans of type example.Bad-Type"
    assert named_report(malformed).coverage == "partial"
    report = named_report(missing())
    source = next(iter(report.nodes.values())).source
    raw = ParsedObservation(
        "local",
        "snapshot",
        "observation",
        "2026-11-01T00:00:00Z",
        "conditions",
        {
            "contexts": {
                "application": {
                    "positiveMatches": {},
                    "negativeMatches": {
                        source.replace("Consumer", "Bad-Consumer"): {
                            "matched": [],
                            "notMatched": [
                                {"condition": "OnBeanCondition", "message": missing()}
                            ],
                        }
                    },
                }
            }
        },
    )
    invalid = normalize_conditions(raw, budget=AnalysisBudget())
    assert "INVALID_CONDITION_SOURCE" in invalid.gaps
    assert not invalid.nodes


def test_condition_boundary_characterization():
    from spring_runtime_mcp.models.common import AnalysisLimit, NormalizationError

    with pytest.raises(NormalizationError, match="INVALID_CONDITIONS_SHAPE"):
        normalize_conditions(observation({}), budget=AnalysisBudget())
    with pytest.raises(AnalysisLimit, match="GRAPH_LIMIT_REACHED"):
        normalize_conditions(
            observation({"contexts": {"application": {}}}),
            budget=AnalysisBudget(max_visits=0),
        )
    for text in (None, "x" * 8193, "AnyNestedCondition 1 matched 0 did not"):
        node = next(iter(named_report(text).nodes.values()))
        assert not node.children_complete
        assert node.derived_outcome == "unknown"


@pytest.mark.parametrize(
    "boundary", ["missingParent", "contextCycle", "ambiguous", "depth", "fuel"]
)
def test_named_chain_incomplete_boundaries_never_explain(boundary):
    from spring_runtime_mcp.adapters.beans import normalize_beans

    query, graph, _, catalog, budget = setup_case()
    payload = fixture("stripe-missing/conditions.json")
    payload["contexts"]["application"]["negativeMatches"][
        "example.StripePaymentGateway"
    ]["notMatched"][0]["message"] = missing("stripeApiClient")
    report = normalize_conditions(observation(payload), budget=budget)
    if boundary in ("missingParent", "contextCycle"):
        beans = fixture("parent-child/beans.json")
        beans["contexts"]["infrastructure"]["parentId"] = (
            "unobserved" if boundary == "missingParent" else "application"
        )
        graph = normalize_beans(observation(beans, "beans"), budget=AnalysisBudget())
    elif boundary == "ambiguous":
        catalog = replace(
            catalog,
            producers=(*catalog.producers, replace(catalog.producers[1], id="other")),
        )
    elif boundary == "depth":
        query = replace(query, condition_depth=0)
    elif boundary == "fuel":
        budget = AnalysisBudget(max_visits=0)
    result = analyze_missing_beans(query, graph, report, catalog, budget=budget)
    assert result.state != "explained"
    assert not result.blocking_paths
    assert result.gaps
    from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
    from spring_runtime_mcp.tools.inspect_beans import _failure

    public = _failure(result, SanitizerPipeline())
    retained = {n["id"] for n in public["conditions"]}
    assert all(set(n["childIds"]) <= retained for n in public["conditions"])
    assert all(set(p) <= retained for p in public["blockingPaths"])
