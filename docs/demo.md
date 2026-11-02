# Reproduce a route query without a running Spring application

[First live query](first-query.md) · [Chinese overview](../README.zh-CN.md) · [Trial feedback](trial-feedback.md)

This demo uses the **0.2.12 Alpha public package** and its bundled synthetic data. It needs Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/) on Linux, with package-index access for installation. After installation, the replay commands read package resources offline. No source checkout, `examples/` directory, JDK, Docker, Spring process, or model API is required.

The replay entry point invokes the actual tool handlers and emits a serialized JSON-RPC-shaped result. It does not start a STDIO MCP session or make HTTP requests. This demonstrates normalization and result semantics, not application authentication, MCP-client interoperability, or real-version Spring compatibility. `boot-3.4-servlet` is a synthetic scenario label, not evidence that Boot 3.4 was run.

## 1. Install in a new directory

Run the blocks in this page in the same terminal; `demo_dir` identifies the new environment and output files.

```bash
demo_dir="$(mktemp -d /tmp/spring-runtime-demo.XXXXXX)"
uv venv "$demo_dir/venv"
uv pip install --python "$demo_dir/venv/bin/python" --default-index https://pypi.org/simple spring-runtime-mcp==0.2.12
"$demo_dir/venv/bin/spring-runtime-mcp" --version
```

Expect `spring-runtime-mcp 0.2.12` before continuing.

## 2. Ask whether GET /orders is registered

The scenario contains a synthetic MVC mapping from `GET /orders` to `example.OrderController.list`. Inspect the [bundled mapping fixture](../src/spring_runtime_mcp/replay_data/conformance/boot-3.4-servlet/mappings.json) to compare the input with the normalized output.

```bash
"$demo_dir/venv/bin/python" -I -m spring_runtime_mcp.replay \
  --scenario boot-3.4-servlet \
  --tool springboot_verify_mappings \
  --arguments-json '{"pathPattern":"/orders","httpMethod":"GET","maxResults":1}' \
  > "$demo_dir/get-route.json"
"$demo_dir/venv/bin/python" -m json.tool "$demo_dir/get-route.json"
```

Read the envelope at `result.structuredContent`; the MCP text content contains the same envelope. Snapshot IDs may differ between runs.

| Selected evidence | Expected value for this synthetic scenario |
| --- | --- |
| `status` | `ok` |
| `coverage.state` / `coverage.gaps` | `complete` / `[]` |
| `totalMatched` / `truncated` | `1` / `false` |
| `data.items[0].paths` / `httpMethods` | `["/orders"]` / `["GET"]` |
| `data.items[0].controllerClass` / `handlerMethod` | `example.OrderController` / `list` |
| `nextAction.kind` / `reasonCode` | `done` / `COMPLETE` |

## 3. Change the selector to POST

```bash
"$demo_dir/venv/bin/python" -I -m spring_runtime_mcp.replay \
  --scenario boot-3.4-servlet \
  --tool springboot_verify_mappings \
  --arguments-json '{"pathPattern":"/orders","httpMethod":"POST","maxResults":1}' \
  > "$demo_dir/post-route.json"
"$demo_dir/venv/bin/python" -m json.tool "$demo_dir/post-route.json"
```

The second result has `status: ok`, complete coverage with no gaps, `totalMatched: 0`, `data.items: []`, and `truncated: false`. This means the complete synthetic mapping evidence contains no match for that path/method selector. The `POST` selector is a metadata filter: the replay sends no POST or other HTTP request.

For a live target, missing endpoint permissions, partial coverage, null counts, or truncation can prevent the same conclusion. Keep those gaps visible.

## 4. Check the recorded result

```bash
"$demo_dir/venv/bin/python" - "$demo_dir" <<'PY'
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1])
for name, count in (("get-route", 1), ("post-route", 0)):
    packet = json.loads((directory / f"{name}.json").read_text())
    result = packet["result"]
    envelope = result["structuredContent"]
    assert json.loads(result["content"][0]["text"]) == envelope
    assert result["isError"] is False
    assert envelope["status"] == "ok" and envelope["errors"] == []
    assert envelope["coverage"]["state"] == "complete"
    assert envelope["coverage"]["gaps"] == []
    assert envelope["totalMatched"] == count
    assert envelope["truncated"] is False
    assert len(envelope["data"]["items"]) == count
    assert envelope["nextAction"]["kind"] == "done"
    assert envelope["nextAction"]["reasonCode"] == "COMPLETE"
    if count:
        item = envelope["data"]["items"][0]
        assert item["paths"] == ["/orders"]
        assert item["httpMethods"] == ["GET"]
        assert item["controllerClass"] == "example.OrderController"
        assert item["handlerMethod"] == "list"
    print(f"{name}: passed (synthetic replay)")
PY
```

Expect `get-route: passed (synthetic replay)` and `post-route: passed (synthetic replay)`.

The documented installation blocks and GET/POST expectations, including equality of the text/structured envelopes, were checked with the public 0.2.12 package in fresh environments outside the repository, using Python 3.12.15 and MCP SDK 2.3.0 on Linux. For the current release installation and protocol evidence, see the [publication record](launch/publication-verification.json). These synthetic checks do not extend the live compatibility matrix.

To try the same question through an MCP client against your own authorized application, follow the [first-query guide](first-query.md). The application must already grant read access to the fixed mappings endpoint. The [feedback template](trial-feedback.md) distinguishes synthetic replay from a live query; a replay success alone is not a live integration or external-adoption claim.
