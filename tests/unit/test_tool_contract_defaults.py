"""Contract defaults must retain root-local references and their constraints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import validate_tool_contract as contract


@pytest.mark.parametrize("default", [1, 50, 0, 51, "999", True])
def test_defaults_follow_root_reference_constraints(default: Any) -> None:
    node = {"$ref": "#/$defs/Alias", "default": default}
    root = {
        "$defs": {
            "Alias": {"$ref": "#/$defs/Count"},
            "Count": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "properties": {"count": node},
    }
    if type(default) is int and 1 <= default <= 50:
        contract._validate_default_in_range(node, root)
    else:
        with pytest.raises(AssertionError, match="violates schema constraints"):
            contract._validate_default_in_range(node, root)


def test_ref_default_also_obeys_sibling_constraints_and_pointer_escaping() -> None:
    node = {"$ref": "#/$defs/a~1b~0c", "maximum": 3, "default": 2}
    root = {
        "$defs": {"a/b~c": {"type": "integer", "minimum": 1}},
        "properties": {"count": node},
    }
    contract._validate_default_in_range(node, root)
    node["default"] = 4
    with pytest.raises(AssertionError, match="violates schema constraints"):
        contract._validate_default_in_range(node, root)


@pytest.mark.parametrize("default", [1, "999"])
def test_full_contract_gate_checks_ref_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, default: Any
) -> None:
    source = contract.ROOT / "src/spring_runtime_mcp/schemas/tools-contract.json"
    bundle = json.loads(source.read_text())
    schema = bundle["tools"][0]["inputSchema"]
    schema["$defs"] = {"Limit": {"type": "integer", "minimum": 1, "maximum": 50}}
    schema["properties"]["maxResults"].update(
        {"$ref": "#/$defs/Limit", "default": default}
    )
    destination = tmp_path / source.relative_to(contract.ROOT)
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(bundle))
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    if default == 1:
        contract.main()
    else:
        with pytest.raises(AssertionError, match="violates schema constraints"):
            contract.main()


def test_gate_rejects_remote_ref_before_validating_any_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = contract.ROOT / "src/spring_runtime_mcp/schemas/tools-contract.json"
    bundle = json.loads(source.read_text())
    schema = bundle["tools"][0]["inputSchema"]
    schema["$defs"] = {"Limit": {"$ref": "https://unregistered.invalid/schema"}}
    schema["properties"]["maxResults"].update({"$ref": "#/$defs/Limit", "default": 1})
    destination = tmp_path / source.relative_to(contract.ROOT)
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(bundle))
    monkeypatch.setattr(contract, "ROOT", tmp_path)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("defaults checked before the reference preflight completed")

    monkeypatch.setattr(contract, "_validate_default_in_range", forbidden)
    with pytest.raises(AssertionError, match="must resolve within local"):
        contract.main()
