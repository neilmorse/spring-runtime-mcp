# 0.2.4 Alpha — 2026-11-01

本版改善首次接入体验。
[PyPI 0.2.4](https://pypi.org/project/spring-runtime-mcp/0.2.4/) 与
[GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.4) 已公开。
标签指向 `4e9e571aac001fc6fa9f95026688b54ae767202c`，包含 P2 修复提交 `de14a41b59ca5c0ac26fe520e33e4931216f562e`。旧版本标签和产物保留。

## 变化与兼容性

- [首次查询指南](../first-query.md)串联公开包安装、最小目标登记、Codex 独立配置、Bearer 环境变量转发、八工具发现与可核对的路由查询；源码开发与按需 source catalog 分开说明。
- 缺失或空 Bearer 变量的 CLI 错误使用固定安全文案，提示检查父客户端环境与转发（Codex env_vars），不回显变量名/令牌；退出码 2、stderr 提示与 stdout 空保持。
- 分层排错说明区分登记、协议、目标鉴权和有效证据；可编辑安装元数据错配明确使用 --reinstall-package 刷新，已在临时副本独立复现。
- 公开工具 Schema、错误码含义、运行依赖、目标/IP/端点边界、HTTP 只读、TLS、脱敏和预算保持；Bean/条件算法未改。

## 已有验证与范围

P2 补丁独立验收为 1134 passed / 46.64 秒，mypy、Ruff/格式通过；候选 wheel 的 113 个包文件与源码逐字节一致。
留存的公开 0.2.3 与源码候选验收证明 Linux / Python 3.12.15 / SDK 2.3.0 / Codex CLI 0.164.0 能发现八工具，并完成参数错误、修正和真实路由查询；目标为隔离 TDD Boot 3.5.16 / Java 21 / MVC / JWT，原工作区及既有客户端配置保留。
这些是本轮源补丁与有限真实样本的证据，不能代替本发布批次验收；未验证 Windows/macOS、其它客户端或完整兼容矩阵。

## 安装

使用公开 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.4 --version
```

首次接入按[首次查询指南](../first-query.md)操作。配置诊断保持默认关闭，目标暴露与重启仍需维护者授权。

## 发布批次

- 干净候选的完整本地门禁退出 0：1134 passed / 47.32 秒；mypy、Ruff、八工具契约与联网漏洞审计通过。
- [远端候选验证](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41273731709) 与
  [正式发布流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41273949601) 已通过，覆盖 Python 3.11–3.14。
- wheel/sdist 各自完成净室安装、两种 SDK 模式、八工具自建回环 HTTP 与七 replay；本地、远端候选、正式发布及公开 PyPI 的文件摘要一致。
- PyPI 保留 neilmorse 审批和禁止管理员绕过，仅新增精确 v0.2.4 标签授权。
- 公开 PyPI 仓库外全新 Python 3.12.15 环境无缓存、无锁约束安装通过，实际 SDK 2.3.0；两种模式、原始 JSON-RPC、八工具 HTTP、Schema/注解、脱敏/16 KiB 预算及七 replay 通过。安装后的 CLI 另行验证缺失变量退出 2、stdout 空、父环境/env_vars 提示以及不回显变量名/堆栈。
- 首次公开命名解析未找到刚发布版本，保留日志；索引就绪、独立命名解析成功后，实际全新安装通过，没有使用本地文件或源码替代。
- [Registry 工作流](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41274337209) 以固定版本/源提交、校验摘要的官方 publisher 及短时 GitHub OIDC 发布成功；[公开 API](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp) 已独立确认 io.github.neilmorse/spring-runtime-mcp 0.2.4 的包标识与版本。

| 文件 | SHA256 |
| --- | --- |
| spring_runtime_mcp-0.2.4-py3-none-any.whl | `526628eeefac8c3767cf28d6c735c0c77d0b427de0d015fba6842907f5a23927` |
| spring_runtime_mcp-0.2.4.tar.gz | `4b87a6f55346240af8739151c1bbf33bc07f9bb3bbdfaa22c7971d780f711226` |
