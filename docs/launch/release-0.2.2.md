# 0.2.2 Alpha — 2026-10-31

本次补丁改善真实用户验收中发现的诊断修复提示。发布已获操作者明确授权；当前为发布准备记录，标签、正式流水线、公开安装结果与产物摘要将在完成后补充，不将准备状态当作已发布。

## 变化与兼容性

- INVALID_ARGUMENT 引导检查实际 inputSchema、字段名、类型与 maxResults 的 1–50 范围；修正参数无需审批，不回显提交的输入。
- startup GET 的 5xx 保留 ENDPOINT_UNAVAILABLE 与实际 HTTP 状态，建议核对暴露、Boot 版本和启动采集；明确状态码不确定根因，配置及重启仍需授权。
- 中英文 README 补充 Codex Bearer 环境变量转发和准确的路由参数示例。
- 八工具 inputSchema/outputSchema、运行依赖、目标/IP/端点白名单、鉴权、只读、TLS、脱敏与 16 KiB 预算保持。旧版本标签和产物保留。

## 已有验证与边界

修复提交 4dcbe49 的 18 项新增回归及全量 1118 项离线测试、mypy、Ruff、八工具契约校验通过。
另经授权使用 TDD 当前开发副本、临时 PostgreSQL、Boot 3.5.16 / Java 21 / MVC / JWT，完成源码版针对性真实回归；Codex CLI 0.164.0 实际完成参数错误、修正后的 Bean 与路由查询，以及 startup 500 提示读取。
三次实际 STDIO 回包最大 2677 字节；临时资源已清理，原开发文件保留。
这些是修复前后的源码验收证据，不能代替本发布批次的产物与公开安装验收；不代表完整平台、Boot/Java/客户端、WebFlux、OpenAPI 或生产网络矩阵。

## 安装

正式发布后使用公开 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.2 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.2 --base-url http://127.0.0.1:18081
```

目标先按[配置指南](../target-app-setup.md)准备。第二条命令是持续等待客户端的 STDIO 宿主；Bearer 目标参见主 README 的 --token-env 与 env_vars 示例。配置诊断保持默认关闭。

## 发布批次

待完成：干净候选提交的完整本地门禁、远端发布门禁、PyPI 环境精确标签授权与既有人工审批、公开 PyPI 安装、GitHub Release、固定源提交的 MCP Registry 发布与独立回读。
