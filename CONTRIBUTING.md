# Contributing

English and Chinese reports and contributions are welcome. Start with the [first-query guide](docs/first-query.md) ([Chinese overview](README.zh-CN.md)) or the [synthetic route demo](docs/demo.md).

## Report an observation

Use the [trial feedback template](.github/ISSUE_TEMPLATE/first-query-feedback.md) for a successful or blocked first query. Include versions, the stage reached, minimal reproduction steps, and independently checked evidence. Mark offline replay as synthetic. See the [feedback guide](docs/trial-feedback.md) for the report format and optional citation permission.

For a bug or feature request, describe the concrete problem, expected and observed behavior, and the smallest reproducible example. Keep public examples synthetic or manually reviewed and redacted. Follow [SECURITY.md](SECURITY.md) for vulnerabilities.

## Make a focused change

Read [AGENTS.md](AGENTS.md) and the relevant page in the [documentation index](docs/README.md). Keep changes focused on the reported problem and update current behavior documents when code behavior changes. Public JSON field names come from the [tool contract](src/spring_runtime_mcp/schemas/tools-contract.json).

Work from a source checkout and use the locked environment:

```bash
uv sync --dev --locked
```

After the dependencies are cached, add `--offline` to the sync command. Runtime use needs no JDK; the full source test suite needs a full JDK with `java` and `javac`. See the [validation guide](docs/launch/README.md) for details and release requirements.

## Validate the change you made

For documentation-only changes, check wording, local links, anchors, and the relevant command/configuration examples. Run synthetic demo commands when changing their steps. A documentation change alone does not require a complete pytest run.

For Python changes, run:

```bash
uv run --no-sync python -m pytest -q
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
```

For source type changes, also run:

```bash
uv run --no-sync python -m mypy src/spring_runtime_mcp
```

For tool Schema or contract-validator changes, also run:

```bash
uv run --no-sync python scripts/validate_tool_contract.py
```

The default checks use synthetic data and disposable loopback fixtures. A test result is not evidence that a real Spring application or a particular client/version combination was verified. Preserve gaps, null counts, unknown/partial results, and failing security evidence. Follow the existing project rules for protected core code, dependency changes, endpoint configuration, packaging, and releases.

## Describe the pull request

Use the PR template to explain the problem, resulting behavior, actual validation, and remaining limits. State which checks were not run or were skipped and why. For integration work, identify the evidence type and the exact versions exercised. Maintainers can then review the change without relying on a private conversation or local files.

`examples/` holds ignored local application fixtures and diagnostic results and is not distributed. Public reproduction steps should work with repository/package resources or an explicitly documented external prerequisite.
