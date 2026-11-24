"""Bounded supplemental Bean evidence for one operator-registered component."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..adapters.beans import normalize_beans
from ..adapters.health import component_status
from ..analyzers.bean_graph import build_dependency_graph
from ..diagnostics import error, partial
from ..models.bean_graph import ContextKey
from ..models.common import (
    AnalysisBudget,
    NormalizationError,
    ParsedObservation,
    remaining_seconds,
)
from ..models.queries import HealthQuery
from ..policy.sanitization import MARKER, SanitizerPipeline
from ..services import HealthBeanBinding, Services
from ..transport.response_gate import EndpointReadError
from .support import read_checked

_LIMIT = 8
_INCOMPLETE = "HEALTH_BEAN_EVIDENCE_INCOMPLETE"
_BUDGET = "HEALTH_BEAN_EVIDENCE_BUDGET"


def _summary(
    observation: ParsedObservation,
    binding: HealthBeanBinding,
    sanitizer: SanitizerPipeline,
    deadline: float,
) -> tuple[dict[str, Any] | None, list[str]]:
    budget = AnalysisBudget(deadline_monotonic=deadline, monotonic=time.monotonic)
    graph = build_dependency_graph(
        normalize_beans(observation, budget=budget), budget=budget
    )
    context = ContextKey(
        observation.target_id, observation.snapshot_id, binding.context_id
    )
    keys = [
        key
        for key in graph.names.get(context, {}).get(binding.bean_name, ())
        if key.canonical_name == binding.bean_name
    ]
    if len(keys) != 1 or not graph.contexts[context].complete:
        return None, ["HEALTH_BOUND_BEAN_UNOBSERVED"]

    key = keys[0]
    bean = graph.beans[key]
    clean = sanitizer.identifier
    name, context_id = clean(key.canonical_name), clean(key.context.context_id)
    if MARKER in (name, context_id):
        return None, ["REDACTED_IDENTIFIERS"]
    gaps = set(graph.gaps)
    edges = sorted(graph.forward.get(key, ()), key=lambda edge: edge.requested_name)
    dependencies = []
    for edge in edges[:_LIMIT]:
        target = (
            edge.resolution.candidates[0]
            if edge.resolution.state == "resolved"
            else None
        )
        requested = clean(edge.requested_name)
        target_name = clean(target.canonical_name) if target else None
        target_context = clean(target.context.context_id) if target else None
        if MARKER in (requested, target_name, target_context):
            gaps.add("REDACTED_IDENTIFIERS")
        dependencies.append(
            {
                "requestedName": requested,
                "targetName": target_name if target_name != MARKER else None,
                "targetContextId": target_context if target_context != MARKER else None,
                "resolution": edge.resolution.state,
            }
        )
    reported_type = clean(bean.reported_type.value)
    if reported_type == MARKER:
        gaps.add("REDACTED_IDENTIFIERS")
        reported_type = None
    elif bean.reported_type.state != "known":
        gaps.add("TYPE_NOT_REPORTED")
    bounded_gaps = sorted(gaps)[:10]
    if len(edges) > _LIMIT:
        bounded_gaps = sorted([*bounded_gaps[:9], "HEALTH_BEAN_EVIDENCE_LIMIT"])
    return {
        "name": name,
        "contextId": context_id,
        "type": reported_type,
        "dependencies": dependencies,
    }, bounded_gaps


async def collect_bean_evidence(
    query: HealthQuery,
    health_body: Any,
    items: list[dict[str, Any]],
    services: Services,
) -> dict[str, Any]:
    binding = services.health_bean_binding
    evidence: dict[str, Any] = {
        "state": "unknown",
        "componentPath": list(binding.component_path) if binding else None,
        "source": None,
        "coverage": {"state": "unavailable", "gaps": []},
        "bean": None,
        "errors": [],
    }
    coverage = evidence["coverage"]
    if binding is None:
        coverage["gaps"] = ["HEALTH_BEAN_BINDING_UNAVAILABLE"]
        return evidence
    path = binding.component_path
    if path[: len(query.component_path)] != query.component_path or (
        len(path) <= query.max_depth and component_status(health_body, path) == "UP"
    ):
        evidence["state"] = "notApplicable"
        coverage["state"] = "complete"
        return evidence
    component = next(
        (item for item in items if tuple(item["componentPath"]) == path), None
    )
    if (
        component is None
        or component["status"] not in {"DOWN", "OUT_OF_SERVICE"}
        or "REVIEW_HEALTH_DETAILS_VISIBILITY" in component["remediationCodes"]
    ):
        coverage["gaps"] = ["HEALTH_BOUND_COMPONENT_UNOBSERVED"]
        return evidence
    # Keep time for the primary result, even when the optional reader stalls.
    allowance = min(5.0, remaining_seconds() - 1.0)
    if allowance <= 0:
        coverage["gaps"] = [_BUDGET]
        return evidence
    try:
        async with asyncio.timeout(allowance):
            deadline = time.monotonic() + allowance
            observation = await read_checked(
                services, query.target_id, "beans", uuid4().hex
            )
            evidence["source"] = {
                "endpointId": "beans",
                "observationId": services.sanitizer.identifier(
                    observation.observation_id, max_length=96
                ),
                "snapshotId": observation.snapshot_id,
                "observedAt": datetime.fromisoformat(
                    observation.observed_at.replace("Z", "+00:00")
                )
                .astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
            }
            bean, gaps = await services.analyze(
                _summary, observation, binding, services.sanitizer, deadline
            )
    except NormalizationError as exc:
        evidence["errors"] = [
            error(
                exc.code,
                "beans",
                exc.http_status if isinstance(exc, EndpointReadError) else None,
            )
        ]
        coverage["gaps"] = [_INCOMPLETE]
    except TimeoutError:
        evidence["errors"] = [error("TARGET_TIMEOUT", "beans")]
        coverage["gaps"] = [_INCOMPLETE]
    else:
        evidence["bean"] = bean
        coverage["gaps"] = gaps
        if bean is not None:
            evidence["state"] = "observed"
            coverage["state"] = "partial" if gaps else "complete"
    return evidence


def trim_bean_evidence(page: dict[str, Any]) -> bool:
    evidence = page["data"].get("beanEvidence")
    if evidence is None:
        return False
    bean = evidence["bean"]
    if bean is not None and bean["dependencies"]:
        bean["dependencies"] = []
        evidence["coverage"]["state"] = "partial"
    elif bean is not None:
        evidence["bean"] = None
        evidence["state"] = "unknown"
        evidence["coverage"]["state"] = "unavailable"
    elif (
        evidence["componentPath"] is not None
        or evidence["source"] is not None
        or evidence["errors"]
    ):
        evidence["componentPath"] = None
        evidence["source"] = None
        evidence["errors"] = []
        evidence["state"] = "unknown"
        evidence["coverage"]["state"] = "unavailable"
    else:
        return False
    gaps = evidence["coverage"]["gaps"]
    evidence["coverage"]["gaps"] = sorted(set(gaps[:9]) | {_BUDGET})
    page["truncated"] = True
    page["truncationReasons"] = sorted(set(page["truncationReasons"][:7]) | {_BUDGET})
    if page["nextAction"]["kind"] in {"page", "remediate"}:
        next_action = page["nextAction"]
        partial(page, [_BUDGET])
        page["nextAction"] = next_action
    else:
        partial(page, [_BUDGET])
    return True
