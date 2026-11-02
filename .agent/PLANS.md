# Task: Release 0.2.12 Alpha

Scope: merge the reviewed English documentation and onboarding changes, prepare an immutable 0.2.12 release, run complete gates, publish verified artifacts, and record public installation checks. Preserve the Chinese README, ignored local examples, existing protection rules, and older release tags/artifacts. Historical record access is limited to the current release entry and required gate scanning.

- [x] Verify and merge documentation PR #33 after Python 3.11–3.14 and lint checks.
- [x] Prepare version metadata and current release notes.
- [x] Run the complete clean-source release gate and candidate CI; compare artifact digests. All six gate stages and 1,224 tests passed; local, candidate, and formal artifacts match.
- [x] Merge release PR #34 and push v0.2.12 at af8a4ac4cf8a6552a61f33e0e54a0b0379099a47; publish PyPI, GitHub Alpha Release, and Registry metadata. Release run 41463903203 and Registry run 41464773287 succeeded; public digests and exact Registry version match.
- [x] Verify public digests, fresh installation outside the checkout, both SDK modes, eight-tool HTTP fixture checks, all seven packaged scenarios, and the exact guide/demo commands. Record Python 3.12.15, MCP SDK 2.3.0, Linux x86_64, synthetic evidence scope, and observed index/download failures. An independent uncached public installation succeeded with system certificates and two concurrent downloads; its full protocol/fixture/replay checks also passed. Validate publication JSON and changed documentation links.

Runtime code, tool Schemas, runtime dependencies, target configuration, and real Spring applications are outside the change scope. Public descriptions cover technical changes and actual evidence only.
