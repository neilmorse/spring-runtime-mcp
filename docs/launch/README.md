# Validation, builds, and releases

This workflow follows [pyproject.toml](../../pyproject.toml), [shared CI](../../.github/workflows/checks.yml), and release workflows. Documented commands/gates do not mean they ran on the current tree. Real-instance acceptance, tag pushes, and public publication require their respective authorization.

## Local offline validation

The complete default suite also needs a full JDK (`java` and `javac`; static-fact cases were verified with Java 21). These tests compile repository helpers and parse synthetic source; they do not start Spring Boot or require Maven/Docker. Missing JDK tests may be skipped by ordinary pytest, but the formal release gate rejects skips. Check `java -version` and `javac -version`, then synchronize the locked development environment:

```bash
uv sync --dev --locked
```

Once tool/dependency caches are complete, add `--offline` to sync. Default checks use synthetic data and self-hosted loopback fixtures only, never production or real Spring Boot instances:

```bash
uv run --no-sync python -m pytest -q
uv run --no-sync python -m mypy src/spring_runtime_mcp
uv run --no-sync python scripts/validate_tool_contract.py
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
```

Python changes require pytest and Ruff lint/format; src type changes also require mypy; Schema/contract-validator changes require contract checks. Documentation-only changes need wording, path, anchor, and link checks. Packaging/resource changes require builds and artifact resource checks. Stop expanding validation once the appropriate checks pass; see [AGENTS.md](../../AGENTS.md).

## Builds and local distribution checks

```bash
uv build
```

The wheel must contain `spring_runtime_mcp/schemas/tools-contract.json`, `py.typed`, and replay resources. The sdist contains current source, tests, scripts, and docs. `.human/` remains in Git but is explicitly excluded from wheel/sdist. `examples/` holds ignored local application fixtures and diagnostic results and is not distributed. Maintenance scripts depending on it require separately prepared fixtures; default synthetic tests and release gates do not depend on that directory.

Development self-check entry point:

```bash
uv run --no-sync python scripts/pre_release_check.py --allow-dirty
```

The script checks the worktree, secrets, versions, offline tests, and static quality; builds wheel/sdist; and independently verifies clean installation, resources/versions, two SDK modes, self-hosted loopback HTTP tool calls, and offline replay. Installing verification environments may use an index/cache, but never real diagnostic targets.

`--audit` enables a network dependency vulnerability audit; the complete release gate uses `--audit --output-dir dist`. Failure exits 1. Incomplete checks such as skipped audit/build, dirty-tree allowance, or accepted skipped tests exit 2. Only a fully successful gate supports formal publication.

## PyPI publication

[Candidate validation](../../.github/workflows/release-check.yml) runs the full gate on `codex/release-*` branches or manual dispatch. [Formal publication](../../.github/workflows/release.yml) is triggered by `v*` tags; shared CI checks Python 3.11–3.14, validates tag/package/server.json version agreement, and uploads verified artifacts.

The publish job uses OIDC in GitHub's `pypi` environment. Maintainers must inspect live approvals/protections; repository YAML alone cannot establish current settings. Pushes, approvals, and publication require explicit authorization for that release; running a local gate does not grant it.

For authorized releases, check the unique version source, `server.json`, installation examples, CHANGELOG, and candidate digests. Existing tags/artifacts remain immutable. Verify public-package installation in a new environment outside the checkout, recording index, platform, Python/SDK versions, and evidence scope. Source execution cannot substitute for a public-package install.

See the [publication verification record](publication-verification.json) for current channels, artifact digests, and public-package environments. It records executed checks and does not replace future release gates.

## MCP Registry and source containers

The [Registry workflow](../../.github/workflows/publish-registry.yml) is a fixed-release task manually dispatched on master. It verifies repository identity, exact tag/commit, version, and PyPI ownership marker. It downloads a pinned, digest-checked official publisher, publishes with GitHub OIDC, then reads back the exact entry. Its actual constants define the approved version/commit; it is not a generic publisher accepting arbitrary versions.

Review the workflow's fixed version/commit and package verification before obtaining Registry authorization for a later release. Keep the README `mcp-name` marker consistent with `server.json`. Do not republish existing versions or infer namespace ownership from repository redirects.

See the [container guide](glama/README.md) for Glama's source-build recipe. Remote listing, rating, and PR status must be checked separately for each task; local build success does not establish them.
