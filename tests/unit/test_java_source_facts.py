"""Synthetic parse-only checks for the standalone JDK source helper."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def helper(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("javac") is None or shutil.which("java") is None:
        pytest.skip("JDK unavailable")
    directory = tmp_path_factory.mktemp("source-facts-helper")
    result = subprocess.run(
        [
            "javac",
            "-proc:none",
            "-d",
            str(directory),
            str(ROOT / "scripts/java/SourceFacts.java"),
        ],
        capture_output=True,
        env={key: os.environ[key] for key in ("PATH",) if key in os.environ},
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, "helper compilation failed"
    return directory


def invoke(helper: Path, *sources: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["java", "-cp", str(helper), "SourceFacts", *(str(p) for p in sources)],
        capture_output=True,
        env={key: os.environ[key] for key in ("PATH",) if key in os.environ},
        text=True,
        timeout=30,
        check=False,
    )


def test_extracts_only_known_symbols_and_literal_routes(
    helper: Path, tmp_path: Path
) -> None:
    source = tmp_path / "Example.java"
    source.write_text(
        """package sample;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.GetMapping;
import sample.api.Service;
@Configuration class Config {
  @Bean(name={"service", "alias"}) Service build() { throw new Error("secret"); }
}
@RestController @RequestMapping("/api") class Controller {
  @GetMapping(path={"/one", "/two"}) String get() { return "secret"; }
}
class Child extends Service {}
""",
        encoding="utf-8",
    )
    result = invoke(helper, source)
    assert result.returncode == 0 and result.stderr == ""
    assert "secret" not in result.stdout and str(source) not in result.stdout
    data = json.loads(result.stdout)
    assert data["gaps"] == []
    assert data["producers"] == [
        {
            "beanName": "service",
            "aliases": ["alias"],
            "declaredType": "sample.api.Service",
            "implementationType": None,
            "configurationClass": "sample.Config",
            "factoryMethod": "build",
            "sourceIndex": 0,
            "sourceLine": 9,
        }
    ]
    assert {item["path"] for item in data["routes"]} == {"/api/one", "/api/two"}
    assert all(item["httpMethod"] == "GET" for item in data["routes"])
    assert {item["name"]: item["directSupertypes"] for item in data["types"]}[
        "sample.Child"
    ] == ["sample.api.Service"]


def test_ambiguous_and_conditional_constructs_do_not_create_facts(
    helper: Path, tmp_path: Path
) -> None:
    source = tmp_path / "Ambiguous.java"
    source.write_text(
        """package sample;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.GetMapping;
import example.Service;
@Configuration class Config {
 @Bean Service same() { return null; }
 @Bean Service same(int n) { return null; }
 @Bean("duplicate") Service a() { return null; }
 @Bean("duplicate") Service b() { return null; }
 @Bean Service generic() { return null; }
}
@RestController @RequestMapping(value="/api", method=OTHER) class Controller {
 @GetMapping("/x") Service x() { return null; }
}
class Unknown extends Missing {}
""",
        encoding="utf-8",
    )
    result = invoke(helper, source)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert [p["factoryMethod"] for p in data["producers"]] == ["generic"]
    assert data["routes"] == []
    assert "sample.Unknown" not in {item["name"] for item in data["types"]}
    assert {
        "UNRESOLVED_SUPERTYPE",
        "UNRESOLVED_BEAN",
        "CONFLICTING_BEAN_NAME",
        "UNRESOLVED_ROUTE",
    } <= set(data["gaps"])


def test_parse_failure_is_fixed_and_never_echoes_source(
    helper: Path, tmp_path: Path
) -> None:
    source = tmp_path / "Invalid.java"
    source.write_text("class Invalid { String SECRET_CANARY = ; }", encoding="utf-8")
    result = invoke(helper, source)
    assert result.returncode == 2 and result.stdout == ""
    assert result.stderr == "SOURCE_PARSE_FAILED\n"


def test_fact_limit_does_not_emit_partial_empty_coverage_as_complete(
    helper: Path, tmp_path: Path
) -> None:
    source = tmp_path / "Many.java"
    source.write_text(
        "\n".join(f"class Type{i} {{}}" for i in range(1001)), encoding="utf-8"
    )
    result = invoke(helper, source)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["types"] == data["producers"] == data["routes"] == []
    assert "FACT_LIMIT_EXCEEDED" in data["gaps"]


def test_explicit_request_mapping_and_unresolved_expressions(
    helper: Path, tmp_path: Path
) -> None:
    source = tmp_path / "Routes.java"
    source.write_text(
        """package example;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.GetMapping;
@RestController @RequestMapping("/v1") class Routes {
 @RequestMapping(value="/thing", method={RequestMethod.GET, RequestMethod.POST}) String both() {return null;}
 @RequestMapping(value="/filtered", method=RequestMethod.GET, params="secret") String filtered() {return null;}
 @GetMapping("/conditional") @Custom String conditional() {return null;}
}
class Generic<T> {}
""",
        encoding="utf-8",
    )
    result = invoke(helper, source)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert {(r["httpMethod"], r["path"]) for r in data["routes"]} == {
        ("GET", "/v1/thing"),
        ("POST", "/v1/thing"),
    }
    assert "UNRESOLVED_ROUTE" in data["gaps"]
    assert "GENERIC_TYPE_UNSUPPORTED" in data["gaps"]
    assert "secret" not in result.stdout


def test_duplicate_types_and_multiple_mappings_are_not_reported(
    helper: Path, tmp_path: Path
) -> None:
    first = tmp_path / "First.java"
    second = tmp_path / "Second.java"
    first.write_text(
        """package sample;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
class Duplicate {}
@RestController class Controller {
 @GetMapping("/a") @PostMapping("/a") String a() {return null;}
 @RequestMapping(method=RequestMethod.GET) @GetMapping("/b") String b() {return null;}
 @RequestMapping(method=org.springframework.web.bind.annotation.RequestMethod.GET) String c() {return null;}
}
""",
        encoding="utf-8",
    )
    second.write_text("package sample; class Duplicate {}", encoding="utf-8")
    result = invoke(helper, first, second)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "sample.Duplicate" not in {row["name"] for row in data["types"]}
    assert data["routes"] == []
    assert {"DUPLICATE_SOURCE_TYPE", "UNRESOLVED_ROUTE"} <= set(data["gaps"])
