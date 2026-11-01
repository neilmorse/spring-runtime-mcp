# 0.2.5 Alpha — 2026-11-01

[PyPI 0.2.5](https://pypi.org/project/spring-runtime-mcp/0.2.5/) 与
[GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.5) 已公开，MCP Registry 已独立回读确认。
标签指向 `f3f99310967b50dbee847ef82228f87ac8beba27`，包含 P3 修复提交 `dc5883b334d2983e4d573a34300d2a88dcb653b7`，并保留 m8ven 分支提交 `9b0af723c7542a82b2c4ad453331fda8daca15fb` 的合并历史。
旧版本标签和产物保留；源补丁证据与本发布批次验收分开记录。

## 变化与兼容性

- WebFlux RouterFunction 的结构化 `details.handlerFunction.className` 保留到现有 `controllerClass`，支持现有 `controllerClassPattern` 过滤，修复类信息丢失和过滤漏匹配。
- 结构化 method 元数据继续优先；函数实现类可能为生成的 lambda 类，不据此推断 Java 业务方法或 descriptor。
- 新增六项 handler 元数据回归和三项 startup 边界回归。OR、NOT、自定义 predicate 保持 `MAPPING_PREDICATE_UNPARSED`；空查询不能证明路由不存在。startup 500 节点上限和 partial 继续保留。
- 合并 `codex/m8ven-verification` 的 README 发布者认证徽章，不将第三方徽章描述为安全或完整兼容矩阵认证。
- 公开工具 Schema、错误码含义、运行依赖、目标/IP/端点边界、HTTP 只读、TLS、脱敏和预算保持；没有扩展 Gateway 代理路由读取。

## 源补丁的实际证据

P3 原临时目录丢失后，于 2026-11-01 重新执行并持久保存补验，明确区分重新执行与恢复旧文件。
源码候选的全量离线套件为 1143 passed / 45.59 秒，mypy、Ruff/格式通过；基线 RED 2 failed / 4 passed，候选定向 GREEN 9 passed。

真实范围仅 Boot 3.5.16 / Spring 6.2.19 / Java 21：当前 TDD shop-product 开发源码隔离副本的 MVC/JWT/PostgreSQL startup，及独立 WebFlux/本地角色 Bearer 的注解与正向 AND/媒体条件函数路由。
startup 在 run 前设置原生 BufferingApplicationStartup，连续 GET 保留 575 个事件，单位/跨度/可见父子关系/分页通过；超过分析上限返回 partial。
WebFlux 缺失/错误凭据 401、权限不足 403、合法凭据 200；同实例基线/候选复现并修复函数类过滤，业务 handler 调用数为零。
19 次官方 SDK 工具调用通过 Schema、文本副本一致性和规范帧预算检查，最大 4420 UTF-8 字节；该数字为解码后重建帧，非原始字节抓包。

持久证据位于维护者仓库外目录 `spring-runtime-mcp-p3-report-2026-11-01`；30 个文件有 SHA-256 清单与离线核验脚本，源补丁哈希独立复核一致。
临时进程、数据库、源码与活动配置清理完成，TDD 原文件/状态保持。证据不包含原始目标响应、凭据或框架日志。
这不是公开 0.2.5 分发包验收；未验证 Boot 2.7/4.x、其他 3.x/Java、Windows/macOS、WebFlux startup、TLS/SNI 或完整 Gateway 代理路由。

## 安装

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.5 --version
```

首次接入见[首次查询指南](../first-query.md)。目标采集、暴露与重启仍须维护者授权。

## 发布批次

- 干净候选的完整本地门禁退出 0：1143 passed / 46.30 秒；mypy、Ruff、八工具契约和联网漏洞审计通过。
- [远端候选完整验证](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41288931660) 与 [正式发布流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41289146303) 全部通过，覆盖 Python 3.11–3.14。
- wheel/sdist 各自完成隔离安装、两种 SDK 模式、八工具自建回环 HTTP 及七 replay。本地、候选 CI、正式流水线和公开 PyPI 摘要一致。
- PyPI 仍需 neilmorse 审批且禁止管理员绕过，仅新增精确 v0.2.5 标签授权。正式产物核对一致后完成所需审批。
- 公开 PyPI 在仓库外全新 Linux / Python 3.12.15 环境无 uv 缓存、无锁约束安装通过，实际 SDK 2.3.0。通过两模式、原始 JSON-RPC、八工具 HTTP、Schema/注解、脱敏/16 KiB 预算及七 replay。
- 安装后的公开包以合成证据确认结构化函数类保留及类过滤成功，方法名/descriptor 继续未知；继承的缺失凭据安全提示与 opaque Context catalog 检查也通过。
- 首次实际公开命名安装未解析到新版本，失败日志保留；后续隔离命名解析就绪后，真正的公开无缓存安装通过。下载依赖期间有网络重试，没有用本地文件或源码替代公开包。
- [Registry 工作流](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41289714894) 使用固定源提交、校验摘要的官方 publisher 与短时 GitHub OIDC 发布成功；[公开 API](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp) 独立确认包名和 0.2.5 版本。
- M8ven 徽章分支已合入 master，公开 README 包含原始徽章；本发布记录不宣称 M8ven 平台认证状态已另行确认。
- 本发布批次未启动或连接 TDD 真实实例；真实 Spring 证据仍以上述 P3 源码补验范围为准。

| 文件 | SHA256 |
| --- | --- |
| spring_runtime_mcp-0.2.5-py3-none-any.whl | `2de53868d8d9e461124d2c90b43429567aa3f14611db5d5f27b4d17246c2bc29` |
| spring_runtime_mcp-0.2.5.tar.gz | `638eb26d0075cf76c93b741871a85106fabfebb909e05c08ddfc40a50d0c0497` |
