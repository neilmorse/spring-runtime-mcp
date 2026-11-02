# 0.2.2 Alpha — 2026-10-31

本次补丁改善真实用户验收中发现的诊断修复提示。
[PyPI 0.2.2](https://pypi.org/project/spring-runtime-mcp/0.2.2/) 与
[GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.2) 已公开；
标签指向 `d4388d39b2ec57160836c602bf97f4875f7f6fe3`，包含修复提交 `4dcbe49`。
旧版本标签与产物保持不变。

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

使用公开 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.2 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.2 --base-url http://127.0.0.1:18081
```

目标先按[配置指南](../../docs/target-app-setup.md)准备。第二条命令是持续等待客户端的 STDIO 宿主；Bearer 目标参见[客户端配置指南](../../docs/client-configuration.md)中的 --token-env 与 env_vars 示例。配置诊断保持默认关闭。

## 发布批次

- 干净候选的完整本地门禁退出 0，1118 passed / 44.27 秒；静态检查、契约、联网漏洞审计、wheel/sdist 净室安装通过。
- [远端候选验证](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41199234783) 与
  [正式发布流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41199583597) 已通过，覆盖 Python 3.11–3.14。
- 本地完整门禁、远端候选、正式发布与公开 PyPI 的 wheel/sdist SHA256 一致。
- 本地首次检查因可编辑安装元数据仍为旧版本而失败，重装项目后完整重跑通过；远端两次镜像下载失败仅重跑对应作业后通过，没有更改测试或绕过门禁。
- PyPI 环境保留 neilmorse 审批与禁止管理员绕过；精确标签列表仅增加 v0.2.2，保留 v0.2.0、v0.2.1。
- 公开 PyPI 仓库外全新 Python 3.12.15 环境无缓存、无锁约束安装通过，实际 SDK 为 2.3.0；两协议模式、原始 JSON-RPC、八工具回环 HTTP、Schema/注解、脱敏/16 KiB 预算及七 replay 均通过，并独立检查新参数与 startup 配方。
- 公开安装首次解析未找到刚发布版本；相同命令重试后通过，保留首轮日志，没有更改包或使用本地源码替代。
- [Registry 发布工作流](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41217447137) 使用固定版本和源提交、校验摘要的官方 publisher 与短时 GitHub OIDC，已成功发布并独立回读 `io.github.neilmorse/spring-runtime-mcp` 0.2.2；未将个人访问令牌交给 Registry。
- [Registry 公开条目](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp) 的包标识与版本已匹配；临时安装环境已清理。

| 文件 | SHA256 |
| --- | --- |
| spring_runtime_mcp-0.2.2-py3-none-any.whl | `277e8b7c53526d8f458696ee4e4433b026671cfa15d8a417668bbdc84e59e2b1` |
| spring_runtime_mcp-0.2.2.tar.gz | `2d0a0a64e96d225ed7d95ababcf8591713aedeeccc7d0327f2505eb65601975b` |
