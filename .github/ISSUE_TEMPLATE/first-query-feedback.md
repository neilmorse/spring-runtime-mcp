---
name: First query feedback
about: Report a successful or blocked first query, or a synthetic replay.
title: "[Trial] "
---

Thanks for trying the project. Successful queries and blocked first attempts are both useful. English or Chinese is welcome.

Share only minimal, reviewed information suitable for a public issue. Omit credentials, raw Actuator bodies, env/configprops value trees, full logs, and stack traces. Vulnerabilities belong in the [security reporting process](https://github.com/neilmorse/spring-runtime-mcp/blob/master/SECURITY.md).


## Environment

- Package version (`spring-runtime-mcp --version`):
- Installation command and index (omit credentials):
- OS and architecture:
- Execution environment: local host / container / remote workspace
- Python version:
- MCP client and version (or not applicable):
- Spring Boot / Java version (if known; not applicable for synthetic replay):
- Existing authentication mode: Bearer / none / other / unknown (no credential values)
- Evidence type (choose one): live authorized application / synthetic replay / setup only

## Progress

Use passed / failed / not attempted / unknown / not applicable. Registration alone does not establish a successful connection.

| Stage | Result | Minimal evidence or fixed error code |
| --- | --- | --- |
| Package installation | | |
| Client loaded the server registration | | |
| MCP initialized and discovered eight tools | | |
| Authorized access to the required fixed endpoint | | |
| Query result independently checked | | |

## Question and reproduction

- What question were you trying to answer?
- Tool name and minimal arguments (redact identifying route/context names):
- Steps already attempted:
- What did you expect, and how was that expectation established?
- What actually happened?

For a blocked attempt, include only the fixed error code and a short reviewed description. Do not paste full stderr or upstream bodies.

## Selected query evidence

Fill only what was observed; use unknown or not attempted rather than guessing.

- `status`:
- `errors` code(s), if any:
- `coverage.state` / `coverage.gaps` code(s):
- `totalMatched` (preserve null if returned):
- `truncated`:
- `nextAction.kind` / `nextAction.reasonCode`:
- Did the reported path, HTTP method and handler agree with your approved source or another independent observation? Describe briefly, or write not checked:

## Friction

- Which instruction was unclear or missing?
- Did you need to consult anything outside the guide?
- What single change would most improve this first query?

## Citation permission (optional)

Default: no permission to reuse this report as a case study or testimonial. Select at most one option if you want to grant permission:

- [ ] The maintainer may cite this report anonymously, without identifying application details.
- [ ] The maintainer may link this report and credit my GitHub handle, without identifying application details.

An issue is public. The maintainer should not infer a testimonial, production adoption, or compatibility beyond the exact versions and evidence described here.
