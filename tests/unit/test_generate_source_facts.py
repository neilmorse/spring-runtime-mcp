"""Registered source facts remain partial and feed existing diagnostic handlers."""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest

from scripts import generate_source_facts as generator
from spring_runtime_mcp.adapters.source_catalog import load_source_catalog
from spring_runtime_mcp.models.common import AnalysisBudget
from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.tools.registry import call_tool


@pytest.fixture
def registered_source(tmp_path: Path) -> Path:
    if shutil.which("javac") is None or shutil.which("java") is None:
        pytest.skip("JDK unavailable")
    (tmp_path / "Example.java").write_text(
        """package example;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
interface PaymentGateway {}
@Configuration class StripeConfiguration {
 @Bean PaymentGateway paymentGateway() { throw new Error("DO_NOT_EXECUTE"); }
}
@RestController class Orders {
 @GetMapping("/orders") String orders() { throw new Error("DO_NOT_EXECUTE"); }
}
""",
        encoding="utf-8",
    )
    return tmp_path


def test_generated_facts_feed_existing_catalog_and_drift(
    registered_source: Path,
) -> None:
    bundle = generator.generate(
        registered_source,
        ["Example.java"],
        target_id="local",
        context_id="application",
    )
    catalog = load_source_catalog(
        bundle["catalog"],
        target_id="local",
        budget=AnalysisBudget(),
    )
    assert len(catalog.producers) == 1
    assert catalog.producers[0].implementation_type is None
    assert catalog.producers[0].condition_sources == ()
    arguments = bundle["driftArguments"]
    assert arguments["expectedScopeComplete"] is False
    assert arguments["expectedBeans"] == [
        {"name": "paymentGateway", "contextId": "application"}
    ]
    assert arguments["expectedRoutes"] == [
        {"path": "/orders", "httpMethod": "GET", "contextId": "application"}
    ]
    services = services_for("boot-3.4-servlet")
    services.catalog = catalog
    result = asyncio.run(call_tool("springboot_detect_drift", arguments, services))
    assert result["status"] in {"ok", "partial"}
    assert result["data"]["unexpectedInRuntime"] == []
    assert any(
        row["dimension"] == "beans" for row in result["data"]["missingInRuntime"]
    )
    # A declared interface is not the concrete runtime object type. Existing
    # named instances must not become type-drift false positives.
    services.reader.bodies["beans"]["contexts"]["application"]["beans"][
        "paymentGateway"
    ] = {
        "type": "example.OtherImplementation",
        "scope": "singleton",
        "dependencies": [],
    }
    second = asyncio.run(call_tool("springboot_detect_drift", arguments, services))
    assert not any(
        row["dimension"] == "beans" for row in second["data"]["missingInRuntime"]
    )
    assert bundle["report"]["coverage"] == "partial"
    assert "CONDITION_SOURCES_UNBOUND" in bundle["report"]["gaps"]
    assert "DO_NOT_EXECUTE" not in json.dumps(bundle)


def test_explicit_condition_bindings_are_preserved_and_typos_rejected(
    registered_source: Path,
) -> None:
    bindings = {"example.StripeConfiguration#paymentGateway": ["Verified#source"]}
    bundle = generator.generate(
        registered_source,
        ["Example.java"],
        target_id="local",
        context_id="application",
        condition_sources=bindings,
    )
    assert bundle["catalog"]["producers"][0]["conditionSources"] == ["Verified#source"]
    assert "CONDITION_SOURCES_UNBOUND" not in bundle["report"]["gaps"]
    with pytest.raises(ValueError, match="unmatched condition binding"):
        generator.generate(
            registered_source,
            ["Example.java"],
            target_id="local",
            context_id="application",
            condition_sources={"Typo#method": []},
        )


@pytest.mark.parametrize(
    "relative", ["../Outside.java", "/Outside.java", "a/../Outside.java"]
)
def test_registration_rejects_outside_paths(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ValueError):
        generator.generate(tmp_path, [relative], target_id="local", context_id="app")


def test_symlink_sources_are_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Private.java").write_text("class Private {}")
    project = tmp_path / "project"
    project.mkdir()
    (project / "Link.java").symlink_to(outside / "Private.java")
    (project / "linked").symlink_to(outside, target_is_directory=True)
    for relative in ("Link.java", "linked/Private.java"):
        with pytest.raises(OSError):
            generator.generate(project, [relative], target_id="local", context_id="app")


def test_type_only_scope_does_not_generate_empty_drift_expectations(
    tmp_path: Path,
) -> None:
    if shutil.which("javac") is None or shutil.which("java") is None:
        pytest.skip("JDK unavailable")
    (tmp_path / "Type.java").write_text("class Type {}")
    bundle = generator.generate(
        tmp_path, ["Type.java"], target_id="local", context_id="app"
    )
    assert bundle["driftArguments"] is None
    assert bundle["report"]["driftArgumentsState"] == "notGenerated"


def test_cli_failure_never_prints_source_or_leaves_success_artifacts(
    registered_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (registered_source / "Broken.java").write_text("class Broken { SECRET_CANARY = ; }")
    output = registered_source / "result"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generator",
            "--project-root",
            str(registered_source),
            "--source",
            "Broken.java",
            "--context-id",
            "application",
            "--output-dir",
            str(output),
        ],
    )
    assert generator.main() == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "SOURCE_FACTS_GENERATION_FAILED\n"
    assert not output.exists()
