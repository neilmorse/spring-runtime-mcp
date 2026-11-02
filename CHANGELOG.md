# Changelog

## [0.2.12] - 2026-11-02

### Documentation and onboarding

- Standardize current product, architecture, tool, setup, troubleshooting, validation, and release documentation in English while retaining README.zh-CN.md as the Chinese overview.
- Add a canonical first-query guide, a reproducible public-package route replay, and feedback/contribution/Issue/PR templates.
- Clarify pagination, upstream collection, error attribution, and compatibility limits; remove unverified performance claims from decision notes and pin historical example links to v0.2.10.
- Preserve runtime behavior, public tool Schemas, runtime dependencies, fixed endpoints, security boundaries, and ignored local examples.


## [0.2.11] - 2026-11-02

- Published to PyPI, GitHub Alpha Release, and MCP Registry at source tag `e7ad1e79fed8ce81812928c7461f8c6d4d71d1dc`. Public artifact digests match and exclude `examples/`; uncached official-PyPI clean installation, both SDK modes, eight-tool loopback HTTP, and seven replays passed. See the [publication verification record](docs/launch/publication-verification.json).

### Distribution contents

- Ignore root `examples/` and stop tracking it while retaining maintainers' local copies; explicitly exclude it from the sdist.
- Remove current-document demo links and document separately prepared local fixtures for real-project maintenance scripts. Default synthetic tests and release gates use repository test data.
- Preserve the eight-tool public contract, runtime dependencies, and runtime behavior.

## v0.2.10 Alpha — 2026-11-02 (contract validation and benchmark fixes)

- Published to PyPI, GitHub Alpha Release, and MCP Registry at source tag `f293193a29123dda52178418efb0b3b80543fa96`. Formal artifact digests match local, candidate, and public downloads. Uncached official-PyPI clean installation, both SDK modes, eight-tool loopback HTTP, and seven replays passed. See the [publication verification record](docs/launch/publication-verification.json).

- Contract maintenance validates descriptions, defaults, and local references. Default validation retains the root Schema reference context and rejects nonlocal references first. Added 10 default and full-entry-point regressions.
- Added synthetic benchmarks for calls, snapshots, Bean dependency depth, and serialization within 16 KiB. Each Bean measurement checks nonempty results and actual resolved 1–4-hop dependencies; timing reference values are warning thresholds only.
- Added/corrected troubleshooting, configuration registration, authentication, timeout layers, and architecture notes. Preserved tool Schema, runtime dependencies, fixed endpoints, and security boundaries.

## v0.2.9 Alpha — 2026-11-02 (tool documentation and rerun protection)

- Published to PyPI, GitHub Alpha Release, and MCP Registry; `v0.2.9` points to `96d1c53c512480f2d01b15513d3b51ec89ca1b0c`. Local, candidate, formal, and public digests match. Uncached public installation, both SDK modes, eight-tool loopback checks, and seven replays passed; see the [publication record](docs/launch/publication-verification.json).
- Added human-readable eight-tool fields, common envelopes, and argument-validated examples aligned with existing Schema fields, defaults, and selector constraints.
- Clarified default-disabled configuration diagnostics and both value-output permissions; consolidated existing Bearer access, JDK prerequisites, Maven arguments, and historical references.
- Nacos reruns exclusively reserve result files before resource initialization, rejecting existing files, directories, symlinks, and identical paths to preserve historical evidence. Added 9 synthetic regressions.
- Demo and Node security checks use the synchronized locked project environment. Preserved public Schemas, runtime dependencies, fixed endpoints, and security boundaries.

## v0.2.8 Alpha — 2026-11-01 (static facts and isolated fault acceptance)

- Added a JDK AST maintenance script that parses explicitly registered Java files into existing Source catalogs and drift arguments. Unknown types and complex conditions/mappings retain partial/gaps.
- Added local source/artifact digest evidence distinguishing unbuilt source from rebuilt artifacts without a process restart; local jar digests are not represented as runtime identity.
- Added build, live-runtime, and synthetic protocol fault-acceptance scripts for migration errors, constructor cycles, conditional Beans, routes, health, response safety, and recovery.
- Acceptance covered the demo and Spring Boot Admin: 1195 tests and 48 MCP calls passed. Static Java checks cover the supported AST subset and tested warnings only, not a full version/project matrix.
- Preserved eight-tool public contracts, fixed endpoints, and Python runtime dependencies. The source-maintenance generator requires a full JDK and is excluded from wheel runtime.


## v0.2.7 Alpha — 2026-11-01 (documentation and distribution cleanup)

- Published to PyPI, GitHub Release, and MCP Registry; `v0.2.7` points to `4a7a7c74b869d3aa13f64bd5b4786c7d08085fa2`. Local/candidate/formal/public digests match. Uncached public installation, both modes, eight tools, and seven replays passed; see the [release record](.human/releases/release-0.2.7.md).
- Added task-based docs/README.md navigation; rewrote product, architecture, and calling descriptions, moving out unimplemented designs and stage-by-stage logs.
- Reduced AGENTS.md to 29 lines. English/Chinese READMEs introduce the tools through practical questions; full client templates moved to a separate guide.
- Consolidated the human archive into decisions, ideas, final reports, unique machine summaries, and release records; removed Git-recoverable duplicates and pinned historical references to original commits.
- Explicitly excluded .human/ from wheel/sdist; set version 0.2.7 without changing diagnostics, public Schema, dependencies, or security policy.

## v0.2.6 Alpha — 2026-11-01 (named Bean conditions)

- Published to PyPI, GitHub Release, and MCP Registry; v0.2.6 points to `60a4bea4434413fd140ef9bddf7d5bf4133d7b68`. Full gate, uncached public installation, and named-condition/blocking-chain regressions passed with all four artifact batches matching. Preserved older tags/artifacts.
- Recognize single names-selector `did not find any beans named <name>` messages only with exact name agreement, connecting existing factory/property transitive analysis without expanding compound/unknown attribution.
- Added 29 offline regressions; independent P4 source-patch acceptance had 1172 passed. Persisted same-instance baseline/candidate and A–E positive/negative evidence; actual gaps remain partial/unknown.
- Preserved CGLIB correlation, graphs, public Schema, runtime dependencies, error codes, network/authentication/TLS, sanitization, and budgets. See [0.2.6 release scope](.human/releases/release-0.2.6.md).

## v0.2.5 Alpha — 2026-11-01 (WebFlux functional handlers)

- Published to PyPI, GitHub Release, and MCP Registry; v0.2.5 points to `f3f99310967b50dbee847ef82228f87ac8beba27`. Full gate, uncached public installation, and function-class filtering regressions passed with four matching artifact batches.
- Preserve Actuator's structured `details.handlerFunction.className` in existing `controllerClass`, fixing functional-route misses under `controllerClassPattern` without inventing business methods or descriptors.
- Added 9 offline regressions. Persisted P3 rerun evidence for live MVC/JWT startup and independent WebFlux/Bearer; source-patch acceptance had 1143 passed. Complex predicates and the 500-step analysis cap remain explicitly partial.
- Merged the M8ven publisher-verification badge branch; the badge is not security or compatibility-matrix certification.
- Public Schema, error codes, runtime dependencies, target/IP/endpoint boundaries, HTTP/TLS, sanitization, and budgets were unchanged. See [0.2.5 release scope](.human/releases/release-0.2.5.md).

## v0.2.4 Alpha — 2026-11-01 (first-query experience)

- Published to PyPI, GitHub Release, and MCP Registry; v0.2.4 points to `4e9e571aac001fc6fa9f95026688b54ae767202c`. Full gate, public installation, and new-message checks passed; artifact digests match.

- Clarified the public-package-to-first-query path, layered troubleshooting, and forced editable-install metadata refresh, retaining unverified client-template scope.
- Missing/empty Bearer-variable messages direct users to the parent environment and env_vars using fixed wording that reveals no variable names or values. Strengthened unit/process regressions; 1134 tests passed.
- Preserved tool Schema, error-code meanings, dependencies, algorithms, security policy, and budgets; see the [0.2.4 release record](.human/releases/release-0.2.4.md).

## v0.2.3 Alpha — 2026-11-01 (source catalog Context IDs)

- Published to PyPI, GitHub Release, and MCP Registry; v0.2.3 points to `3f752dc46f8f5b9344bdfbde15597b95f3dd6670`. Full gate and new public installation passed; three artifact batches and public PyPI digests match.

- Fixed source catalogs treating Context IDs as Java symbols. Valid identities such as shop-product now correlate exactly, retaining length/C0/DEL restrictions and Java type/factory validation.
- Added 16 regressions; independent acceptance had 1134 passed with mypy/Ruff/format checks. Limited TDD positive/negative and legacy STDIO evidence established catalog factory/property-negative correlation; proxy/named-OnBean transitive limits remain.
- Added the source catalog guide without changing public Schema, dependencies, safety guards, or budgets. See the [0.2.3 release record](.human/releases/release-0.2.3.md).

## v0.2.2 Alpha — 2026-10-31 (diagnostic remediation guidance)

- Pushed `v0.2.2` (`d4388d39b2ec57160836c602bf97f4875f7f6fe3`) and published to PyPI, GitHub Release, and MCP Registry. Full local/remote gates and new public-PyPI installation passed; digests match. See the [release record](.human/releases/release-0.2.2.md).

- INVALID_ARGUMENT now provides an argument-correction recipe: inspect actual inputSchema names/types/constraints and maxResults 1–50, without echoing input. Correcting arguments needs no approval.
- startup GET 5xx preserves the code/status while suggesting exposure, Boot-version, and startup-collection checks. Status alone does not establish a cause; configuration/restarts still need authorization, with no POST fallback.
- English/Chinese READMEs gained public-package Codex Bearer forwarding and route-argument examples. Public Schema, runtime dependencies, target configuration, and safety guards were unchanged; see the [0.2.2 record](.human/releases/release-0.2.2.md).
- Added 18 regressions; full offline suite: **1118 passed / 44.90 seconds**. mypy, Ruff, and eight-tool contracts passed. HTTP regressions used self-hosted loopback services only, without restarting/contacting TDD or rerunning real-project acceptance.
- Subsequently authorized targeted source-based live regressions on the TDD development copy verified anonymous JWT rejection, invalid/corrected arguments, MVC mappings, and startup 500 guidance. A temporary Codex session performed erroneous, corrected, and subsequent calls. Three complete STDIO responses peaked at 2677 bytes. Temporary instances/database were cleaned up, original worktree preserved; the full real-project matrix was not rerun.

## v0.2.1 Alpha — 2026-10-31 (metadata correction)

- Published to [PyPI](https://pypi.org/project/spring-runtime-mcp/0.2.1/); `v0.2.1` points to `2d8567ba9ae10ac143a24d4ec443909a9e8997cb`.
- Unified Registry name and README ownership marker as `io.github.neilmorse/spring-runtime-mcp`, with project URLs pointing to the current owner. Published using short-lived GitHub OIDC and independently read back the Registry entry.
- Full local/remote gates, 1100 tests, isolated wheel/sdist installs, and uncached public-PyPI installation without lock constraints passed. Version, both SDK modes, eight-tool loopback calls, and seven replays passed; see the [release record](.human/releases/release-0.2.1.md).
- Preserved production diagnostics, public Schema, runtime dependencies, and security boundaries. The dynamic project's uv.lock entry does not fix its version; lock verification passed with unchanged bytes. Preserved 0.2.0 tags/artifacts.
- Submitted the directory PR as a draft; Glama account/listing steps were deferred by user choice, without claiming formal listing.

## v0.2.0 Alpha — 2026-10-31 (formal publication)

- Published to [PyPI](https://pypi.org/project/spring-runtime-mcp/0.2.0/); `v0.2.0` points to `2394b29a84a5fcd8210d3934eee1a94e1d3fc0ac`.
- The full local gate on a clean commit exited 0. Formal Release passed Python 3.11–3.14, static/contract checks, vulnerability audit, builds, both isolated artifact installs, and publication.
- A fresh environment outside the checkout installed from public PyPI and passed both SDK modes, eight-tool loopback calls, and seven replays. Public digests match the verified batch. The initial release remains Alpha, loopback-only, and limited in compatibility; see the [release record](.human/releases/release-0.2.0.md).
- The following Unreleased entries retain each implementation round's historical status. Their delivered changes were included in this release; historical wording does not mean they remain unpublished. The 2026-10-22 v0.2.0 entry is a development milestone, not the initial PyPI publication date.

## Unreleased — 2026-10-31 release workflow completion

- Prepared reviewed production fixes, tests, resources, scripts, and historical evidence as one release commit. Raw Nacos logs/minute JSONL remained local with exact ignore rules; aggregate evidence was retained.
- Added the validation-only `Release validation only` branch workflow, reusing the full gate without OIDC or a PyPI publish environment. Formal tags still require matching versions and operator approval.
- Fixed special-filename omissions in Git inventories using binary `git ls-files -z` and `os.fsdecode`; added 14 real-Git regressions. The preceding offline suite had 1100 passed; final-commit gates/digests were recorded outside the repository rather than reusing earlier batches.
- Confirmed neilmorse as repository owner and updated publication-account checks. PyPI account access was blocked and no GitHub pypi environment existed at that stage; release readiness was not claimed.

## Unreleased — 2026-10-31 formal release preparation

- Release CI reuses the full pre-release script with mandatory network vulnerability audit, sensitive-file/source checks, contract validation, and isolated sdist installation. Upload the same verified wheel/sdist batch without rebuilding; remote execution was pending.
- Unified Chinese standalone commands on the locked project environment. Retained 0.2.0 Alpha, corrected tag claims, and distinguished public-package/client acceptance from SDK checks.
- Excluded logs, JSONL, caches, and environment files from sdist while retaining user source. Scope, evidence, deliverable relationships, and manual work are in the [readiness report](.human/reports/release-readiness-2026-10-31.md).

## Unreleased — 2026-10-30 locked build dependencies

- Pinned Hatchling/build dependencies to exact versions and included them in the development lock. Pre-release checks reject unpinned or unaudited build dependencies. Added no runtime dependencies.
- Offline locked wheel/sdist builds independently passed isolated installation, CLI, both SDK modes, eight-tool loopback calls, and seven replays. Added 2 build-lock regressions; final suite **1084 passed / 44.43 seconds**, mypy 53 source files, Ruff 124 files, and eight-tool contracts passed. `uv audit --locked` found no known vulnerabilities in 43 packages, representing that query only.

## Unreleased — 2026-10-30 HTTP read boundaries

- Added a cumulative 32 KiB header budget covering status, interim, and final responses, returning `RESPONSE_HEADERS_TOO_LARGE` on overflow. Incremental single-member gzip decoding separately bounds encoded/decoded bodies and rejects corruption, truncation, trailing data, and multiple members; other encodings remain rejected.
- Early disconnect before Content-Length completion returns `INCOMPLETE_RESPONSE`, never treating accidentally valid JSON fragments as complete evidence. Resolved addresses share a 2-second socket connection deadline, then restore the remaining read deadline. Python still cannot forcibly terminate system DNS resolution.
- Added synthetic/self-hosted loopback regressions for headers, gzip, health 503, chunking, dual size limits, truncated bodies, and connection budgets. Full suite **1082 passed / 44.67 seconds**; mypy 53 files, Ruff 124 files, and eight-tool contracts passed. Extra local Python 3.11/3.14 checks covered header parsing only.
- Self-hosted TLS checks used disposable synthetic certificates and in-memory files: trusted certificates succeeded; hostname mismatch, untrusted/expired certificates, and IP-name mismatches were rejected before HTTP requests. Hostname cases used registered-host SNI; IP literals sent no SNI. These limited loopback samples do not establish a full TLS/SNI matrix.
- Historical LS-01 and PC-01/PC-02 offline repair probes passed again with `--expect-repaired`. Temporary outputs were cleaned up; the historical live-project matrix was not rerun.

## Unreleased — 2026-10-30 clean sdist installation acceptance

- The clean-install gate requires one wheel and one sdist, checking version/resources independently. sdist additionally rejects caches, build outputs, sensitive environment files, and symlinks. Both artifacts install runtime dependencies under lock constraints in separate environments and exercise CLI version, both SDK modes, eight-tool loopback paths, and seven replays.
- Added 6 sdist failure regressions for missing artifacts, version/resource mismatch, caches, dangerous links, and install failures. The real clean-install stage passed; full suite **1055 passed / 38.85 seconds**, Ruff 123 files passed. Build backend resolution still used its declared range/local cache rather than runtime constraints; this round was not published.

## Unreleased — 2026-10-30 HTTP content-encoding guard

- JSON with declared nonidentity Content-Encoding returns `UNSUPPORTED_CONTENT_ENCODING` before body reads. Errors retain registered endpoint/status without echoing encoding/body. Absent/identity encodings continue; gzip decoding was not yet implemented at that stage.
- Added 12 offline regressions for encoding chains, unknown encodings, identity, error envelopes, and slow loopback responses. Initial full tests exposed inaccurate header mocks and a fixture event race; corrected the environment without weakening assertions. Final suite **1049 passed / 40.51 seconds**; mypy 53 files, Ruff 123 files, and contracts passed. No Schema/runtime dependency changes.

## Unreleased — 2026-10-30 rejected HTTP response reads

- The connector checks status/Content-Type before body reads, avoiding error pages for redirects, authentication failures, unavailable endpoints, and non-JSON types while retaining fixed response-gate errors. Valid health 503 JSON remains readable; connector and gate share acceptable-JSON checks.
- Reproduced error-page reads with synthetic responses, then verified slow loopback bodies no longer convert 302, 401, or invalid Content-Type into timeouts. Added 17 regressions: targeted network suite 118 passed; full suite **1037 passed / 36.78 seconds**. mypy 53 files, Ruff 123 files, and contracts passed. Read-only boundaries, Schema, and runtime dependencies were unchanged.

## Unreleased — 2026-10-30 health evidence counts

- Unreadable health components or missing status retain coverage gaps and now set `totalMatched` to null while preserving readable components/unknown states. Previous partial responses could expose a definite count of 0 or of readable items, implying complete matching scope.
- Added 7 synthetic regressions for unreadable components, path filters, valid peers, missing status, complete empty results, and MCP snapshot continuation. Full suite **1020 passed / 36.38 seconds**; mypy 53 files, Ruff 122 files, and contracts passed. Public Schema/target policy unchanged; no real Spring instances contacted.

## Unreleased — 2026-10-30 pre-release checks and worktree inventory

- The pre-release script reads Hatch dynamic versions, checks source-version agreement, and compares wheel metadata/CLI versions during clean installs. Wheels use offline constraints exported from `uv.lock`; skipped builds, dirty-tree allowances, and accepted skipped tests are incomplete.
- Independent `--audit` runs `uv audit --locked`, blocking on failure/unavailability and explicitly recording when not run. Exit codes are 0 complete, 1 failed, and 2 incomplete.
- Added 14 offline gate regressions for audit findings, timeout/missing tools, dynamic-version conflicts, wheel/CLI mismatch, skipped checks, lock constraints, and unreadable Git state/tracked files. Full suite **1013 passed / 34.54 seconds**; mypy 53 files, Ruff 121 files, contracts, and `git diff --check` passed. Independent `uv audit --locked` found no known vulnerabilities in 40 packages at that time, not a substitute for later audits.
- The clean stage built and verified wheel resources, locked installation, CLI version, both official SDK modes, eight-tool loopback paths, and seven replays. Initial end-to-end checks found the pytest executable could not import project scripts required by new tests; switched to the prescribed `python -m pytest` entry point.
- See the [worktree inventory](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/worktree-inventory-2026-10-30.md), which does not replace file-content review. Public Schema, production diagnostics, and runtime dependencies were unchanged; not committed or published in that round.

## Unreleased — 2026-10-23 four-hour Nacos soak

- Added the [Nacos four-hour simulation](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/nacos-soak-matrix/README.md), randomly selecting alibaba/nacos 2.4.3 commit `f4f8b189cf16186669de5b692d43630ed2c3fda2` from Nacos/PowerJob/Sentinel candidates: 2,391 Java files, 1,526 main Java files, 22 Maven modules, Boot 2.7.18/Java 21/MariaDB 11.2. Ran four hours on loopback with disposable MariaDB and a separate management port. Removed the incompatible SOFA Hessian 3.3.6 from a copied jar because Nacos needs 4.0.63. Management Bearer, 8192-step buffering, and disabled business authentication were test-only settings.
- Formal soak: **14,401.542 seconds**, **68,260 live calls satisfied every assertion**. Baseline 519 visible Beans across 52 pages; three cycles exhausted 44 pages each without drift. Target restart recovery at 1/2.5 hours took 9.964/10.623 seconds. MariaDB pauses at 1.5/3 hours timed out readiness and recovered on the first post-unpause check. Peak frame 15,242 bytes; median/p95 242.754/945.435 ms; 240 minute samples, no unexpected errors. See [audit](.human/reports/nacos-four-hour-2026-10-23.md), [sanitized aggregate](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.json), and [build/patch hashes](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23-build.json).
- Retained a target health blind spot: Actuator db observed embedded Derby, so external MariaDB pauses timed out readiness while MCP diagnose_health remained UP. `actuatorObservedExternalDbOutage=false` prevents treating it as external DB health evidence. Verified the pinned single-node standalone only, not cluster/HA, configuration publishing, registration, UI, long-lived client connections, or multinode JRaft. No production Python changes, commit, or publication in that round; offline suite then had **999 passed**.

## Unreleased — 2026-10-23 XXL-JOB scheduler acceptance

- Added the [scheduler matrix](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/xxl-job-matrix/README.md) for XXL-JOB v3.4.0 commit `555b48f2edf0e51cd77971565342d80c15c9f18d`: 157 Java/136 main Java files, Boot 4.0.5/Java 21 runtime/MariaDB 11.2. Exercised eight-tool functionality, stability, and availability. No production Python changes; SSO Actuator allowance, management Bearer filter, and Logback masking were temporary test settings.
- Formal 300-second run: **2449 live calls satisfied every assertion**. 356 Beans/402 dependencies; exhausted 356 visible Beans in 35 pages. Routes/db health ok/complete without bypassing native SSO UI. Pausing MariaDB produced DOWN while Bean reads remained available, then UP after recovery. Peak frame 15,638 bytes; target stop/same-host restart recovered. See [audit](.human/reports/xxl-job-2026-10-23.md) and [sanitized aggregate](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/xxl-job-matrix/results/xxl-job-final-300s.json).
- Startup trees remained partial and migration endpoints returned negative 404 evidence. Executor jobs, alerts, production scheduler clusters, and UI were not verified. Suite then had **925 passed**; not committed or published in that round.

## Unreleased — 2026-10-23 HertzBeat acceptance

- Added the [niche-project matrix](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/niche-project-matrix/README.md) for Apache HertzBeat v1.7.3 commit `67ad4b04ef1b06b62f0e5030a26d0ca069294fa3`: 1387 Java/975 main Java files, Java 17/Boot 3.4.2/Maven/embedded H2. Exercised eight-tool functionality, stability, and availability without production Python changes. Diagnostic Bearer Servlet Filter, Sureness `/actuator/**` allowance, and 2048-step buffering existed only in temporary copies.
- Formal 300-second run: **1594 live calls satisfied every assertion**. 875 Beans/1167 dependencies; exhausted 873 visible Beans in 87 pages. Flyway had 5 APPLIED records; routes/db health ok/complete. Startup trees remained partial with node/depth gaps. Peak frame 15,072 bytes; target stop/same-host restart recovered. See [audit](.human/reports/niche-project-hertzbeat-2026-10-23.md) and [sanitized aggregate](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/niche-project-matrix/results/hertzbeat-final-300s.json).
- Kept HertzBeat's native Spring AI MCP server enabled without external model calls; initially disabling it caused a missing dependency Bean for `webMvcSseServerTransportProvider`. H2 was embedded, so no DB-pause case ran. UI, upstream tests, alert delivery, and production clusters were unverified. Not committed/published in that round.

## Unreleased — 2026-10-23 MCP delivery gate

- The host checks eight-tool contract/handler agreement at startup and rejects missing/extra handlers. Removed placeholder CAPABILITY_DISABLED dispatch fallback; unauthorized configuration diagnostics still return that safe denial from real handlers. Public Schema, dependencies, and target policy were unchanged.
- Clean-install gates compare wheel Schema, `py.typed`, and all replay JSON byte-for-byte. Installed packages run outside the checkout through both official SDK modes, staged raw-pipe handshakes, eight real HTTP tool handlers, unmasked configuration sanitization, 16 KiB frames, and seven replays. replay uses `importlib.resources` while retaining bounded, symlink-rejecting reads.
- Fixed the source catalog STDIO EOF race by reading replies before closing input. Configuration CLI tests now use self-hosted loopback fixtures rather than probing unknown fixed-port services. See [MCP delivery verification](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/mcp-release-gate-2026-10-23.md) for evidence/limits.

## Unreleased — 2026-10-23 final delivery verification

- Source/dependency checks found no production TODO/FIXME/HACK/XXX, `NotImplementedError`, or debug breakpoints. All eight tools bind real handlers. Runtime third-party imports were only declared `mcp` and `jsonschema`; configuration diagnostics remain disabled by default with CAPABILITY_DISABLED when unregistered.
- Hardened --source-catalog to regular files with chunked 256 KiB reads, avoiding unbounded allocation, FIFOs, and device reads. Invalid files, overflow, target mismatch, missing token variables, and invalid arguments exit 2 with specific messages revealing no values/paths. Added --version matching __version__ and wheel metadata.
- Upgraded development pytest 8.4.2 to 9.0.3 to address PYSEC-2026-1845 reported by uv audit; 40 resolved packages had no known findings. Git history/worktree scans found no real credentials; PEM/Bearer matches were synthetic vectors.
- Wheel/sdist include tools-contract.json, py.typed, and replay_data, excluding test caches, target/, and example jars. Fresh wheel/sdist venvs passed --version, legacy/2026-07-28 MCP modes, and packaged replay. uv lock --check passed.
- Added --version to README/README.zh-CN/SPEC, corrected obsolete mypy src scripts, default-test scope, demo commands, and claims that --version was unimplemented; removed user-home absolute paths from docs.
- Final offline suite **922 passed**; mypy 53 files, Ruff 113 files, and contracts passed, with no skip/xfail. See [final audit](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/final-delivery-audit-2026-10-23.md). Version remained 0.2.0 without release tags at that stage; no commit/publication or expanded real-target/production-matrix claim.

## Unreleased — 2026-10-23 Fineract acceptance

- Added the [ultra-large project matrix](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/ultra-project-matrix/README.md) for Apache Fineract 1.9.0 commit `5d96e8cc32ff63f97d5ac15e19c6fafee0c31357`: 4565 Java/4087 main Java files, Java 17/Boot 3.1.7/Gradle 8.5. Ran the native provider with disposable PostgreSQL 16 and loopback HTTP for eight-tool functionality/stability/availability acceptance. Temporary builds added only a public pluginManagement mirror for documentation-plugin dependencies from retired JCenter; Boot/BOM, runtime dependencies, and diagnostic network boundaries were unchanged.
- Fixed mappings false negatives for JAX-RS routes when Actuator servlets reports Jersey `/api/*` coverage but DispatcherServlet has no matching record. Such results now retain partial, totalMatched=null, and NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED. Added 4 offline regressions; full suite **913 passed**.
- Formal 300-second run: **1202 live calls satisfied every assertion**. 2544 Beans/5626 dependencies; exhausted 2524 visible Beans in 252 pages. Peak frame 15,170 bytes. Pausing the DB made health non-UP while Bean reads remained available, then recovered to UP; target stop/same-host restart recovered. JAX-RS probes remained partial/gap. An 8192-step snapshot hit NORMALIZATION_LIMIT; the test launcher used 2048 steps for positive evidence while retaining the capacity limit. See [audit](.human/reports/ultra-project-fineract-2026-10-23.md) and [sanitized aggregate](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/ultra-project-matrix/results/fineract-final-300s.json).
- The first full gate after heavy load had 1 STDIO process-test failure; isolated and second full runs passed. Retained it as timing variability without modifying tests or weakening assertions. No commit/publication in that round and no production-cluster, full-version-matrix, or long-term-stability claim.

## Unreleased — 2026-10-23 fault-matrix fixes

- Closed PC-01, PC-02, and LS-01; see [investigation, fixes, and verification](.human/reports/production-chaos-remediation-2026-10-23.md). Description/exception name/value descriptors propagate taint, and the independent gate rejects unredacted values. Encoded/unsafe names cannot restore associated values; same-named OpenAPI business Schemas are preserved. Health errors extract fully qualified type shapes only, not original messages.
- Check cursor safety/uniqueness before registration, trying at most 16 candidates without polluting caches on failure. Pagination shares encoded snapshots and offsets, processing only the current page normally. Retained 60-second TTL, 32 MiB/LRU, 16 KiB complete frames, and whole-snapshot revalidation/removal after credential-policy changes.
- Added 28 synthetic regressions; final suite **909 passed**, with mypy/Ruff/contracts. Final runs on three live projects had **425 calls satisfying every assertion**. ThingsBoard exhausted 1255 visible Beans across 125 consecutive pages; instruction canaries were not forwarded and prior failures were preserved. Public Schema, runtime dependencies, and target policy were unchanged; no publication or production/full-version-matrix claim.

## Unreleased — 2026-10-23 live-project fault injection

- Added the [production-adopted project fault matrix](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/production-chaos-2026-10-23.md): native ShenYu, ThingsBoard, and DolphinScheduler backends built/launched in isolation. Selected workflows made 399 live MCP calls covering PostgreSQL pause, pool exhaustion, startup conflicts/missing dependencies/cycles, 1000 extra real Beans, malformed responses, and cancellation recovery. Optional Actuator was added only to a temporary ThingsBoard copy; DolphinScheduler used development Standalone. These were not production-cluster acceptance.
- Confirmed PC-01 instruction forwarding via health name/value details, adding independent canary assertions and preserving failure evidence. PC-02 recorded large ThingsBoard snapshots that could not be exhausted within the absolute 60-second TTL; random-cursor LS-01 remained unfixed. Added offline investigation probes whose exit 0 means defect reproduction. Default suite remained 881 passed, not proof of complete safety/stability. Production implementation, Schema, and Python runtime dependencies were unchanged; no commit/publication in that round.

## Unreleased — 2026-10-22 comprehensive review fixes

- Added the [large native-project stability matrix](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/large-project-stability-2026-10-22.md): pinned Flowable, Spring Cloud Data Flow, and reactive Spring Boot Admin builds/isolated runs made 1748 live calls, exercising full visible pagination, four-way concurrency, both SDK modes, and restart recovery. Reproduced random-cursor/output-gate conflicts, preserving real UNSAFE_OUTPUT failures before production fixes. Default offline tests remained 881 passed; short runs/partial results were not treated as complete stability/compatibility.
- Closed R1–R5: retain nonconflicting PathItem siblings, keep conflict/unreadable counts unknown, fix Schema resource dialect inheritance, and unify restricted RFC3339/exact-time sorting so invalid startup times cannot imply complete drift comparison. Added 44 synthetic regressions; **881 passed**. A reproducible local springdoc 3.1.1 source patch fixed early grouped instantiation/fixed document entry. JHipster separate management-port acceptance had 18 calls; Petclinic REST recheck had 15 passes. Cached jars, public Schema, and Python runtime dependencies were unchanged. See [closure and limits](.human/reports/remaining-findings-remediation-2026-10-22.md).
- Fixed two OpenAPI defects found in larger projects: independently bounded shared-array metadata projections and preservation of business-property description Schemas while still sanitizing original descriptions/credentials. Added 21 regressions; 837 passed, with 15 Petclinic REST rechecks. Native same-port JHipster API-docs/JWT/Liquibase had 18 passing calls; third-party separate-management-port initialization remained unfixed. See [fixes and limits](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/openapi-project-matrix-remediation-2026-10-22.md).
- Added the [larger public-project live matrix](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/project-matrix/README.md), preserving native Petclinic, Petclinic REST, and JHipster Boot versions. The main matrix recorded 43 calls over 416–486 Beans, pagination, DB health, native simple OpenAPI Schemas, JWT 401/403, and 8 applied Liquibase records. Two complex-OpenAPI diagnostic defects and JHipster API-docs startup blockage remained failures, not passes. This round added acceptance evidence without fixing those defects.
- Fixed native WebFlux functional-route nested AND and Accept:/Content-Type: predicate parsing; unknown OR/NOT/custom syntax remains partial. Added 34 offline regressions; 816 passed. 12 live Boot 3.2.4/WebFlux/Java 21 calls passed while preserving original failures. See [fix and recheck](.human/reports/webflux-predicate-remediation-2026-10-22.md).
- Closed CR-01 through CR-13 from the [comprehensive review](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/comprehensive-review-2026-10-22.md); see [per-finding acceptance](.human/reports/comprehensive-remediation-2026-10-22.md). Reject oversized request IDs before the SDK, ending the session with a null ID; the actual SDK tool-send boundary rechecks 16 KiB.
- Shared Services and safe diagnostic envelopes now coordinate two read slots per target and one 15-second deadline across all tools, including queueing, reads, cooperative analysis, and output checks.
- Fixed composed/dictionary OpenAPI Schemas, local PathItem/Response references, and 3.0/3.1 $ref semantics; unknown semantics remain partial. Fixed unsupported migration inference, checksum comparability, Bean type-query parent/child shadowing, successful migration states, and hidden-UP visibility conclusions.
- STDIO tests close input only after replies and use bounded pipe reads. CI/release share validation, with release dependent on all gates and matching tags. No publication was executed in that round.
- Added uv.lock, pinned development tools, and wheel py.typed. Isolated installation passed official SDK 2.3.0 legacy/2026-07-28 discovery and tool-error checks.
- Added trusted local --token-env Bearer binding with format restrictions and known-secret sanitization. No arbitrary header forwarding or Basic support; public Schema, runtime dependencies, and loopback scope were unchanged.
- After explicit approval, verified a committed S8 copy of `<TDD checkout>` with Boot 3.5.16/Java 21/MVC/JWT/disposable PostgreSQL 16. Preserved unfinished business code in the original TDD worktree, adding only an approved optional Actuator Maven profile. Six diagnostic endpoints were read-only with anonymous rejection and env/config value endpoints disabled. See [Shop summary](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.10/examples/tdd-runtime/verification.json). This does not establish a full-version matrix or completion of red-stage TDD business work.
- Full offline suite **782 passed**, with mypy 51 files, Ruff, eight-tool contracts, wheel/sdist builds, and installation checks.
- Additional audit fixes: missing startup evidence yields STARTUP_EVIDENCE_UNAVAILABLE rather than ok in drift; unreadable mappings patterns/methods remain partial without invented unrestricted status. Missing Bean type/scope, truncated health details/startup tags, migration budget exhaustion, and date-time contracts retain explicit evidence. Added --config-prefix/--config-property/--config-profiles/--config-allow-values; packaged replay works after wheel installation. See [audit fixes and verification](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/delivery-audit-remediation-2026-10-22.md).

## v0.2.0 — 2026-10-22

- Closed TC-BUG-01 through 15 from the 2026-10-18 logic/boundary audit. Added numeric-address pinning and peer checks; static safety rules permit socket/http.client imports only in transport/actuator_http.py and prohibit raw socket writes. Full suite: 730 passed.
- Moved tool-contract JSON into src/spring_runtime_mcp/schemas/, loaded with importlib.resources and distributed in the wheel.
- Added hatchling, Apache-2.0, an English README, SECURITY.md, and GitHub Actions CI: Python 3.11–3.14, mypy/ruff, wheel builds, and clean STDIO handshakes. Isolated uv build artifacts completed initialize/tools/list.
- Migrated STDIO to the official mcp Python SDK 2.x lowlevel Server with mcp>=2.3,<3. The SDK handles negotiation, initialization gates, JSON-RPC errors, and cancellation. Tool descriptors, outputSchema validation, sanitization, and 16 KiB budgets remain project logic.
- Client-visible protocol changes:
  - Only ping is accepted before initialize; early tools/* returns JSON-RPC -32602.
  - Unknown tools return -32602, previously -32600 or a failed envelope.
  - Unsupported handshake versions such as 2026-07-28 negotiate to the SDK's latest handshake version, 2025-11-25, rather than echoing the request.
  - Unparseable transport frames (invalid JSON, jsonrpc other than "2.0", unsupported id types, or nonobject params) are discarded without replies. The SDK parse boundary preserves the no-handler/no-I/O safety property, which the corresponding tests now assert.
  - The 16 KiB budget now includes the io.modelcontextprotocol/serverInfo _meta stamp in 2026-era responses.
- Static safety rules restrict mcp/mcp_types imports to server.py and cli.py; transport/stdio.py remains for replay CLI only.
- Added live-application verification with examples/spring-boot-demo (Boot 3.4.5/Java 21, H2/Flyway, separate read-only management port, BufferingApplicationStartup) and scripts/check_demo_app.py. The committed transcript.jsonl covers initialize, tools/list, and six read tools.
- Fixed real /actuator/beans interoperability: Boot emits parentId only for children, so absence means root rather than unknown parent. Previously real single-Context apps were classified partial and could not produce missing-Bean blocking chains. Regressions are in tests/unit/test_bean_graph.py and test_rw06_architecture_regressions.py.
- Updated the count to 730 passed. Live-application checks are outside the default offline gate and require a running demo with loopback management access only.

## v0.1.0 — 2026-10-17

Initial source freeze, with version matching pyproject.toml and MCP serverInfo.version. This records local Git scope, not package publication, deployment, or production acceptance.

### Delivered scope

- Eight name-sorted tools: Beans/conditions, routes, health, migrations, startup, configuration, OpenAPI, and drift.
- Bean aliases/parent-child dependency graphs, three-valued nested conditions, in-document OpenAPI references, and partial/unknown results when evidence is missing.
- A custom STDIO JSON-RPC host, standard-library HTTP connector bound to a startup-registered origin, and fixed-scenario offline replay CLI.
- Fixed GET endpoints, no redirects, field projection/two-layer sanitization, query-bound cursors, and a 16,384-byte complete-response budget including structuredContent and text copies.
- Eight-tool JSON contracts, synthetic multi-version fixtures, offline/loopback integration and security regressions, target setup, and client guides.

### Source-freeze validation

Executed at the repository root with cached dependencies, without real Spring Boot or production targets. HTTP integration used test-created loopback fixture services only.

| Check | Command | Result |
| --- | --- | --- |
| Full suite | `uv run --offline --no-project --with pytest==8.4.2 --with jsonschema==4.25.1 python -m pytest -q` | 639 passed, 22.35 seconds |
| Types | `uv run --offline --no-project --with mypy==1.18.2 --with jsonschema==4.25.1 python -m mypy src/spring_runtime_mcp` | 48 source files passed |
| Lint | `uv run --offline --no-project --with ruff==0.14.1 ruff check src tests scripts` | Passed |
| Format | `uv run --offline --no-project --with ruff==0.14.1 ruff format --check src tests scripts` | 75 files passed |
| Contract | `uv run --offline --no-project --with jsonschema==4.25.1 python scripts/validate_tool_contract.py` | 8 isolated input/output schemas and 144+ synthetic assertions passed |

Node wrappers, wheel/sdist builds, client interoperability, and live-instance version matrices were not independently checked in this round.

### Known limitations

- The host did not yet use the official MCP Python SDK. Limited JSON-RPC method tests did not establish full protocol compliance or every client's compatibility.
- The HTTP connector lacked complete resolved-address validation, numeric-address pinning, actual peer IP/port checks, and target credential binding. HTTPS used a default TLS context without a live TLS/SNI matrix. Remote/production use still required independent safety-spec acceptance.
- Upstream reads had byte limits/socket timeouts, but complete absolute deadlines, decompression budgets, and in-flight cancellation still required separate acceptance.
- Boot 2.7/3.x/4.x and MVC/WebFlux evidence came from synthetic fixtures, without a real Java/Boot/authentication matrix. Source-type/factory correlations still required explicit SourceCatalog facts.
- No explicit build backend, dependency lock, or verified distribution artifacts existed at this stage. This version did not claim every SPEC product goal.
- The [red-team audit](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/security-redteam-2026-10-17.md) and machine inventory describe an earlier baseline, not complete auditing of new modules.

The source-freeze cleanup did not change public inputSchema/outputSchema, runtime dependencies, target allowlists, or target configuration.
