# Red-Team Regression Suite

Run the requested TypeScript entry with Node 22+ (no npm dependencies):

```bash
node --test tests/security/redteam-audit.test.ts
```

It uses Node's built-in runner to execute five Python test modules
through cached, offline uv environments; the table also includes the separate boundaries suite. TAP is test output, not MCP STDIO.
Run the same cases directly with:

```bash
uv run --no-sync python -m pytest -q tests/security
```

| Module | Attack surface |
| --- | --- |
| `test_redteam_network.py` | Dynamic host fields, metadata/private/mapped/noncanonical IP inputs, mutable registration, redirects, malformed responses, zero-DNS rebinding input and safe client exceptions |
| `test_redteam_readonly.py` | Fixed GET constructor, startup, path/encoding aliases for forbidden endpoints, immutable capabilities, method overrides and exhaustive production-call AST inventory |
| `test_redteam_leakage.py` | Normal/embedded JSON, descriptor taint, URI credentials, JOSE/PEM, encoding variants, serializer/cache bypasses, raw errors, filter-count oracle and policy-change eviction |
| `test_redteam_injection.py` | Raw descriptions/comments/details, local-only messages/recipes, long prose, second serialization, Bean labels, condition suffixes and no request to runtime-provided links |
| `test_redteam_boundaries.py` | Confusable SSRF origins cannot reach DNS/transport, HTTP error bodies are not parsed or echoed, secret-bearing config/health/migration-shaped fields fail closed, static GET and stdout/logger inventory |
| `test_redteam_stdio.py` | Valid JSON-RPC, invalid argv, exceptions/cancellation, Python/native/cached stdout, atexit, confined file reads and symlink/byte-limit attacks |

All credentials are synthesized in test code; no SSH file, real diagnostic host,
DNS service or external HTTP endpoint is accessed. The parent conftest prohibits
network connections. Do not weaken a failing case to accept raw output or a
request; fix the corresponding production boundary.

Current network and output boundaries are described in the
[security architecture](../../docs/architecture/security-and-sanitization.md).
These synthetic suites do not establish a complete live TLS/SNI, platform or
third-party client matrix. Validation requirements are in the
[release guide](../../docs/launch/README.md).
