# 0.2.4 Alpha — 2026-11-01

本版改善首次接入体验。发布已获操作者授权，当前为准备记录；正式流水线、公开包验收及 Registry 状态完成后补齐。

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

正式发布后使用公开 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.4 --version
```

首次接入按[首次查询指南](../first-query.md)操作。配置诊断保持默认关闭，目标暴露与重启仍需维护者授权。

## 发布批次

待完成：干净提交的完整本地/远端门禁、wheel/sdist 隔离安装、正式发布、公开 PyPI 全新安装与缺失凭据提示检查、GitHub Release、MCP Registry 发布及独立回读。
