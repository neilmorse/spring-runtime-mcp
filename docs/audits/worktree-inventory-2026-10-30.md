# 工作区交付清单 — 2026-10-30

范围：master 提交 `49ffdb9` 之上的当前工作区快照；清单记录文件状态，不代表逐个文件已经审查通过。此文件自身在快照生成后创建。保留用户已有改动，不自动暂存、提交或删除。

生成时：35 项已跟踪变更、143 个未跟踪文件。门禁修复和相应新测试也计入此快照。

快照生成后新增 `tests/unit/test_health_incomplete_counts.py`、`tests/unit/test_http_rejection_read_budget.py`、`tests/unit/test_http_connect_deadline.py`，并修改 Health 工具及 HTTP 连接器/响应门处理证据缺口和读取边界；本清单不自动跟踪后续变更。

交付审核时需核对生产代码与测试成对纳入；验收原始失败、修复及结果摘要应保持关联。仅凭此路径清单不能证明文件内容不存在敏感信息；缓存、运行数据库、临时凭据和构建产物不应混入提交。

用途与关联核对：

| 范围 | 用途与交付关系 |
| --- | --- |
| `src/` | 当前生产实现。未跟踪的 `mapping_predicates.py` 被 `adapters/mappings.py` 导入；`timestamps.py` 被 server、contracts、startup 和 drift 导入，必须与相关改动一起纳入。 |
| `tests/` | 现有修复的离线回归及本轮门禁测试，应与所验证的实现一起审查。 |
| `scripts/` | 项目矩阵、故障探针、净室验收及预发布检查；与对应 `examples/` 和 `docs/audits/` 一起决定交付范围。 |
| `docs/` | 历史审计、修复记录、脱敏结果摘要及交接文档；旧失败和后续复验应成对保留。 |
| `examples/` | 多个固定项目的启动材料、配置、补丁及验收聚合；按子目录核对可复现性和内容边界。`examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.stdout.log` 是待审查的日志文件，需单独确认内容及是否纳入。 |
| 根目录及配置 | 产品说明、规则、许可证与依赖锁定；`ai_audit.py` 的暂存重命名和目标文件后续修改需要一起审查。 |

该 Nacos 日志有 49 行；对 traceback、私钥头、Bearer 和密码赋值的有限模式筛查未命中，不能据此证明日志内容完全安全或决定纳入范围。

## 已跟踪变更

- ` M` `.agent/PLANS.md`
- ` M` `.gitignore`
- ` M` `AGENTS.md`
- ` M` `CHANGELOG.md`
- ` M` `HANDOVER.md`
- ` M` `README.md`
- ` M` `README.zh-CN.md`
- ` M` `SPEC.md`
- ` M` `docs/architecture/cross-version-normalization.md`
- ` M` `docs/audits/delivery-audit-remediation-2026-10-22.md`
- ` M` `docs/audits/project-state-and-architecture-audit-2026-10-18.md`
- ` M` `docs/contracts/tool-calling-policy.md`
- ` M` `pyproject.toml`
- `RM` `scripts/ai_audit.py`（原路径 `ai_audit.py`）
- ` M` `scripts/check_stdio_install.py`
- ` M` `src/spring_runtime_mcp/adapters/health.py`
- ` M` `src/spring_runtime_mcp/adapters/mappings.py`
- ` M` `src/spring_runtime_mcp/adapters/openapi.py`
- ` M` `src/spring_runtime_mcp/adapters/startup.py`
- ` M` `src/spring_runtime_mcp/cli.py`
- ` M` `src/spring_runtime_mcp/contracts/definitions.py`
- ` M` `src/spring_runtime_mcp/policy/output_guard.py`
- ` M` `src/spring_runtime_mcp/policy/sanitization.py`
- ` M` `src/spring_runtime_mcp/replay.py`
- ` M` `src/spring_runtime_mcp/server.py`
- ` M` `src/spring_runtime_mcp/snapshots.py`
- ` M` `src/spring_runtime_mcp/tools/detect_drift.py`
- ` M` `src/spring_runtime_mcp/tools/inspect_beans.py`
- ` M` `src/spring_runtime_mcp/tools/registry.py`
- ` M` `src/spring_runtime_mcp/tools/search_openapi.py`
- ` M` `src/spring_runtime_mcp/tools/support.py`
- ` M` `tests/integration/test_cli_config_wiring.py`
- ` M` `tests/integration/test_stdio_host_process.py`
- ` M` `tests/security/redteam-audit.test.ts`
- ` M` `uv.lock`

## 未跟踪文件

### src

- `src/spring_runtime_mcp/adapters/mapping_predicates.py`
- `src/spring_runtime_mcp/models/timestamps.py`

### tests

- `tests/unit/test_cli_startup_contract.py`
- `tests/unit/test_diagnose_health_characterization.py`
- `tests/unit/test_handler_registration.py`
- `tests/unit/test_health_characterization.py`
- `tests/unit/test_mappings_servlet_coverage.py`
- `tests/unit/test_openapi_projection_safety.py`
- `tests/unit/test_pre_release_check.py`
- `tests/unit/test_production_chaos_repairs.py`
- `tests/unit/test_remaining_findings.py`
- `tests/unit/test_webflux_predicates.py`

### scripts

- `scripts/check_guide_runtime.py`
- `scripts/check_large_project_runtime.py`
- `scripts/check_nacos_soak.py`
- `scripts/check_niche_project_runtime.py`
- `scripts/check_production_chaos.py`
- `scripts/check_project_runtime.py`
- `scripts/check_ultra_project_runtime.py`
- `scripts/check_xxl_job_runtime.py`
- `scripts/pre_release_check.py`
- `scripts/prepare_springdoc_patch.py`
- `scripts/probe_jhipster_separate_port.py`
- `scripts/probe_large_project_stability.py`
- `scripts/probe_openapi_matrix_findings.py`
- `scripts/probe_production_chaos_findings.py`
- `scripts/probe_unresolved_review_findings.py`
- `scripts/production_fault_proxy.py`

### docs

- `docs/RISK_ITEMS_HANDOFF.md`
- `docs/ai-collaboration-workflow.md`
- `docs/audits/coverage-risk-zoning-2026-10-23.md`
- `docs/audits/final-delivery-audit-2026-10-23.md`
- `docs/audits/large-project-cursor-probe-2026-10-22.json`
- `docs/audits/large-project-cursor-remediation-2026-10-23.json`
- `docs/audits/large-project-stability-2026-10-22.json`
- `docs/audits/large-project-stability-2026-10-22.md`
- `docs/audits/mcp-release-gate-2026-10-23.md`
- `docs/audits/nacos-four-hour-2026-10-23.md`
- `docs/audits/niche-project-hertzbeat-2026-10-23.md`
- `docs/audits/openapi-project-matrix-remediation-2026-10-22.md`
- `docs/audits/openapi-projection-remediation-2026-10-22.json`
- `docs/audits/production-chaos-2026-10-23.json`
- `docs/audits/production-chaos-2026-10-23.md`
- `docs/audits/production-chaos-findings-2026-10-23.json`
- `docs/audits/production-chaos-remediation-2026-10-23.json`
- `docs/audits/production-chaos-remediation-2026-10-23.md`
- `docs/audits/production-chaos-remediation-probe-2026-10-23.json`
- `docs/audits/remaining-findings-remediation-2026-10-22.md`
- `docs/audits/system-map-2026-10-23.md`
- `docs/audits/ultra-project-fineract-2026-10-23.md`
- `docs/audits/unresolved-findings-investigation-2026-10-22.md`
- `docs/audits/unresolved-review-probe-2026-10-22.json`
- `docs/audits/unresolved-review-remediation-2026-10-22.json`
- `docs/audits/webflux-predicate-investigation-2026-10-22.md`
- `docs/audits/webflux-predicate-remediation-2026-10-22.md`
- `docs/audits/xxl-job-2026-10-23.md`

### examples

- `examples/large-project-matrix/LargeProjectLauncher.java`
- `examples/large-project-matrix/LegacyServletSecurity.java.template`
- `examples/large-project-matrix/README.md`
- `examples/large-project-matrix/ReactiveSecurity.java.template`
- `examples/large-project-matrix/ServletSecurity.java.template`
- `examples/large-project-matrix/common.properties`
- `examples/large-project-matrix/dataflow.properties`
- `examples/large-project-matrix/flowable.properties`
- `examples/large-project-matrix/projects.json`
- `examples/large-project-matrix/spring-boot-admin.properties`
- `examples/nacos-soak-matrix/DiagnosticManagementSecurity.java`
- `examples/nacos-soak-matrix/META-INF/spring/org.springframework.boot.actuate.autoconfigure.web.ManagementContextConfiguration.imports`
- `examples/nacos-soak-matrix/NacosDiagnosticsLauncher.java`
- `examples/nacos-soak-matrix/README.md`
- `examples/nacos-soak-matrix/common.properties`
- `examples/nacos-soak-matrix/nacos.properties`
- `examples/nacos-soak-matrix/projects.json`
- `examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23-build.json`
- `examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.json`
- `examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.jsonl`
- `examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.stdout.log`
- `examples/niche-project-matrix/DiagnosticSecurity.java`
- `examples/niche-project-matrix/README.md`
- `examples/niche-project-matrix/common.properties`
- `examples/niche-project-matrix/hertzbeat.properties`
- `examples/niche-project-matrix/projects.json`
- `examples/niche-project-matrix/results/hertzbeat-final-300s.json`
- `examples/production-chaos/ChaosConfiguration.java`
- `examples/production-chaos/DiagnosticSecurity.java`
- `examples/production-chaos/ProductionLauncher.java`
- `examples/production-chaos/README.md`
- `examples/production-chaos/ShenyuManagement.java`
- `examples/production-chaos/common.properties`
- `examples/production-chaos/dolphinscheduler.properties`
- `examples/production-chaos/projects.json`
- `examples/production-chaos/results/dolphinscheduler-remediation.json`
- `examples/production-chaos/results/dolphinscheduler.json`
- `examples/production-chaos/results/shenyu-remediation.json`
- `examples/production-chaos/results/shenyu.json`
- `examples/production-chaos/results/thingsboard-remediation.json`
- `examples/production-chaos/results/thingsboard.json`
- `examples/production-chaos/shenyu.properties`
- `examples/production-chaos/thingsboard-actuator.patch`
- `examples/production-chaos/thingsboard.properties`
- `examples/project-matrix/EarlyGroupedBeanProbe.java`
- `examples/project-matrix/ProjectDiagnosticsLauncher.java`
- `examples/project-matrix/README.md`
- `examples/project-matrix/SpringdocPatchedProbe.java`
- `examples/project-matrix/early-grouped-bean-verification.json`
- `examples/project-matrix/jhipster-actuator-namespace.patch`
- `examples/project-matrix/jhipster-core.properties`
- `examples/project-matrix/jhipster-fixed.properties`
- `examples/project-matrix/jhipster-same-port-verification.json`
- `examples/project-matrix/jhipster-same-port.properties`
- `examples/project-matrix/jhipster-separate-port-investigation.json`
- `examples/project-matrix/jhipster-separate-port-remediation-verification.json`
- `examples/project-matrix/jhipster.properties`
- `examples/project-matrix/logback-diagnostics.xml`
- `examples/project-matrix/petclinic-rest-final-remediation-verification.json`
- `examples/project-matrix/petclinic-rest-initial-verification.json`
- `examples/project-matrix/petclinic-rest-remediation-verification.json`
- `examples/project-matrix/petclinic-rest.properties`
- `examples/project-matrix/petclinic.properties`
- `examples/project-matrix/projects.json`
- `examples/project-matrix/springdoc-3.1.1-diagnostics.patch`
- `examples/project-matrix/springdoc-compile-pom.xml`
- `examples/project-matrix/springdoc-patched-probe-verification.json`
- `examples/project-matrix/verification.json`
- `examples/ultra-project-matrix/FineractDiagnosticsLauncher.java`
- `examples/ultra-project-matrix/README.md`
- `examples/ultra-project-matrix/common.properties`
- `examples/ultra-project-matrix/fineract-build-workaround.patch`
- `examples/ultra-project-matrix/fineract.properties`
- `examples/ultra-project-matrix/projects.json`
- `examples/ultra-project-matrix/results/fineract-final-300s.json`
- `examples/upstream-guides/GuideDiagnosticsLauncher.java`
- `examples/upstream-guides/README.md`
- `examples/upstream-guides/diagnostics-pom.template.xml`
- `examples/upstream-guides/verification.json`
- `examples/upstream-guides/webflux-remediation-verification.json`
- `examples/xxl-job-matrix/DiagnosticSecurity.java`
- `examples/xxl-job-matrix/README.md`
- `examples/xxl-job-matrix/common.properties`
- `examples/xxl-job-matrix/projects.json`
- `examples/xxl-job-matrix/results/xxl-job-final-300s.json`
- `examples/xxl-job-matrix/xxl-job.properties`

### other

- `LEGACY_CONVENTIONS.md`
