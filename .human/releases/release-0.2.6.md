# 0.2.6 Alpha — 2026-11-01

[PyPI 0.2.6](https://pypi.org/project/spring-runtime-mcp/0.2.6/) 与 [GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.6) 已公开；MCP Registry 已独立回读确认。
标签指向 `60a4bea4434413fd140ef9bddf7d5bf4133d7b68`，包含 P4 修复提交 `989f985f0b69ad8f18a0849891f2555f8238125f`。
下列源补丁证据与本发布批次验收分开，旧版本标签及产物保留。

## 行为变化与兼容性

- 仅扩展条件适配器：单一 `names` 选择器的负向消息 `did not find any beans named <name>`，后缀名称必须与唯一选择器完全一致。
- 该解析接通既有的 `REQUIRED_BEAN_MISSING → SOURCE_FACTORY_NOT_CREATED → PROPERTY_*` 证据链。类型条件与传递分析已有实现，不作为新增图能力宣称。
- 保留 ALL/CURRENT/PARENTS、MissingBean 的相反方向、reported outcome 冲突及 Condition 实现类型检查。多个要求、复合选择器、名称不符、截断和未知语法继续保守处理。
- Bean 名称支持有界连字符子集；Java 类型/source 校验与目录符号限制未放宽，不能据此宣称任意名称均可关联源码。
- CGLIB producer 关联保持，不能通过删除代理后缀补造类型事实。公开 Schema、错误码、运行依赖、网络/鉴权/TLS、脱敏、预算及图算法均未修改。

## 源补丁证据与范围

P4 源码候选的独立验收为 1172 passed / 46.40 秒，mypy、Ruff/格式及 diff 检查通过。新增 29 个合成用例；实施时 RED 8 failed / 15 passed，最终相关 GREEN 75 passed。
持久报告目录 `spring-runtime-mcp-p4-report-2026-11-01` 包含 33 个文件及 SHA-256 离线核验脚本，相关源码哈希与候选一致。

真实组合仅 Boot 3.5.16 / Java 21 / MVC / JWT / PostgreSQL 16.15 / SDK 2.3.0 的当前 TDD 开发快照隔离副本。
同实例基线无路径，候选产生“具名 Bean 缺失 → 唯一源码工厂未创建 → 属性不匹配”路径；整体仍 partial，保留原有证据缺口。
属性满足时 Bean 存在且无缺失链；无目录、source/Context 错配或 conditions 不可读时保持 unknown、无虚假路径。
10 次真实 STDIO 工具调用检查 Schema、文本副本和规范帧预算，最大 3768 UTF-8 字节；不是原始字节抓包。

连字符名称、MissingBean 具名负向、搜索范围变体主要为离线合成验证，不代表真实矩阵全部通过。
临时资源已清理，原 TDD 状态、文件及既有实例保持；未覆盖完整 Boot/客户端矩阵或代理类型关联。
源补丁验收不等于公开发行包验收；公开 0.2.5 包保持原样。

## 安装

以下命令面向该版本的公开发行包；发布状态以本记录的发布批次为准：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.6 --version
```

首次接入见[首次查询指南](../../docs/first-query.md)，源码目录见[接入指南](../../docs/source-catalog.md)。
目标暴露、配置和重启仍须维护者授权。

## 发布批次

- 干净候选的本地完整门禁退出 0：1172 passed / 45.46 秒，mypy、Ruff、八工具契约和联网漏洞审计通过。
- [远端候选完整验证](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41300445346) 与 [正式标签流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41300742943) 全部通过，覆盖 Python 3.11–3.14。
- wheel/sdist 各自通过净室安装、两种 SDK 模式、八工具自建回环 HTTP 和七 replay；本地、候选 CI、正式发布和公开 PyPI 摘要一致。
- PyPI 仅新增精确 v0.2.6 标签，仍需 neilmorse 审批且禁止管理员绕过；正式产物核对一致后完成所需审批。
- 公开包在仓库外全新 Linux / Python 3.12.15 环境无 uv 缓存、无锁约束、无替代索引环境覆盖安装通过，实际 SDK 2.3.0。通过两模式、原始 JSON-RPC、八工具 HTTP、Schema/注解、脱敏/16 KiB 预算及七 replay。
- 安装后的包以合成证据验证具名缺失解析与名称不一致拒绝，并验证别名 → 工厂 → 属性失败路径及缺目录保守对照；继承的函数类过滤、凭据提示和 opaque Context catalog 检查也通过。
- 公开索引初期命名解析暂不可见，隔离解析重试后就绪；真实无缓存安装遇到依赖下载网络重试，最终完整通过，没有使用本地包或源码替代。
- [Registry 工作流](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41301592797) 使用固定源提交、校验摘要的官方 publisher 和 GitHub OIDC 发布成功；[公开 API](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp) 独立确认名称、PyPI 包标识和 0.2.6。
- 首次接入指南的安装固定版本与 CLI 预期输出同步至 0.2.6。仅更新安装版本，本批次没有重跑 Codex 真实会话或扩大客户端兼容声明。
- 本发布批次未启动或连接 TDD 真实实例，真实 Spring 结论仍以上述 P4 源补丁证据范围为准。

| 文件 | SHA256 |
| --- | --- |
| spring_runtime_mcp-0.2.6-py3-none-any.whl | `efaa0dc6f559e2e2ef722bbb39a248c882245c1b700ea9b7b4927df644ba50a3` |
| spring_runtime_mcp-0.2.6.tar.gz | `d3b63a0e26f175297d80f10058bfb742e314e22ad8657cbd64f33a5f7d699c20` |
