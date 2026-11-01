# 0.2.7 Alpha — 2026-11-01

[PyPI](https://pypi.org/project/spring-runtime-mcp/0.2.7/)、[GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.7) 与 MCP Registry 已公开，Registry 精确名称/版本已独立回读。
标签 `v0.2.7` 指向 `4a7a7c74b869d3aa13f64bd5b4786c7d08085fa2`。本次只整理文档和发行包，诊断逻辑、八工具 Schema、运行依赖、安全策略与预算保持。

## 变化

- 当前实现集中导航，移出历史设计与阶段过程；AGENTS.md 保留 29 行核心规则。
- 中英文 README 用实际问题介绍八项功能，客户端模板单独维护。
- 人类资料库仅保留决策、最终报告、独有机器摘要和发布记录，重复材料通过 Git 回查。
- wheel/sdist 明确排除 `.human/`，工具 Schema、py.typed 和 replay 资源完整；安装说明统一为 0.2.7。

## 发行证据与边界

- 本地完整门禁六项全部通过：1172 passed / 45.86 秒，mypy、Ruff、契约、联网依赖审计及 wheel/sdist 各自净室验收。
- [候选 CI](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41307043125) 与 [正式标签流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41307310153) 全部通过，包含 Python 3.11–3.14 和完整发行门禁；正式产物核对后完成既有环境审批。
- [公开安装验收](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41312391163)在 GitHub 全新 Linux / Python 3.12.3 环境无缓存、无锁约束安装通过，实际 SDK 2.3.0；通过两种 SDK 模式、原始管道、八工具自建回环 HTTP 和七个 replay 场景。
- 首次公开安装因 files.pythonhosted.org 依赖下载超时失败；随后在 GitHub 全新环境使用隔离 pip、同一官方索引完整通过；本机慢速重试停止，未使用本地包或替代索引。
- 本地、候选 CI、正式标签、GitHub assets 与公开 PyPI 的 wheel/sdist 摘要一致。
- [Registry 流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41311140339) 使用固定源提交、校验摘要的 publisher 和 GitHub OIDC 成功；公开 API 回读名称 `io.github.neilmorse/spring-runtime-mcp`、PyPI 包及 0.2.7 一致。
- 本次未启动或连接真实 Spring Boot；不扩大完整 Boot/Java/客户端、Windows/macOS、生产集群或 TLS/SNI 兼容性结论。旧标签和产物保持。

| 产物 | SHA256 |
| --- | --- |
| spring_runtime_mcp-0.2.7-py3-none-any.whl | `472bf92de8beb58876ab2b16a089079738f577d9bce95c8beae4ac933883ed42` |
| spring_runtime_mcp-0.2.7.tar.gz | `9621b5d4cbb2f3022de6be21d2250fc2b242dd10c82197152dc6d5a967c8db1a` |
