# 0.2.3 Alpha — 2026-11-01

本版修复 source catalog 对 Spring Context ID 的错误校验。
[PyPI 0.2.3](https://pypi.org/project/spring-runtime-mcp/0.2.3/) 与
[GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.3) 已公开。
标签指向 `3f752dc46f8f5b9344bdfbde15597b95f3dd6670`，包含修复提交 `8997e6d9e118f1e10e2b03b8b0abf1b9b98165ad`。旧版本标签和产物保留。

## 变化与兼容性

- source catalog 的 contextId 不再按 Java 类型名校验；shop-product、application:management 等有界身份可以加载，保留原值并精确关联。
- Context ID 长度限制为 1–256，拒绝 C0 与 DEL；其余 Java 符号字段仍严格校验。shop-product 与 shop_product 不视为同一身份。
- 新增[源码目录接入说明](../source-catalog.md)，解释事实登记、条件 source key、未扫描范围以及 partial/unknown。
- 八工具公开 Schema、运行依赖、目标/IP/端点白名单、鉴权、只读、TLS、脱敏和预算保持。CGLIB 代理关联及具名 ConditionalOnBean 传递链的真实覆盖限制仍保留；没有修改条件分析算法。

## 已有验证与限制

16 项新增离线回归及全量 1134 项测试通过；本次独立验收复跑为 1134 passed / 45.76 秒，mypy、Ruff 与格式检查通过。
另经授权对 TDD 当前开发副本的 Boot 3.5.16 / Java 21 / MVC / JWT 隔离实例进行正反对照：目录新增准确工厂关联，属性负向场景可见 PROPERTY_VALUE_MISMATCH，条件能力缺失时仍 unknown；真实 STDIO legacy 接通目录。
这些是源码和有限真实样本证据，不能代替本发布批次验收，不代表完整条件语法、代理/传递链、Boot/客户端/平台矩阵。原开发工作区保留，临时运行资源已清理。

## 安装

使用公开 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.3 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.3 --base-url http://127.0.0.1:18081
```

第二条命令是 STDIO 宿主；目标先按[配置指南](../target-app-setup.md)准备。源码目录与凭据仅通过既有 --source-catalog / --token-env 接入，配置诊断默认关闭。

## 发布批次

- 干净候选的完整本地门禁退出 0：1134 passed / 48.95 秒；mypy、Ruff、八工具契约和联网漏洞审计通过。
- [远端候选验证](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41267958909) 与
  [正式发布流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41268217530) 均通过，覆盖 Python 3.11–3.14。
- wheel/sdist 均完成隔离安装、SDK 两模式、八工具自建回环 HTTP 与七 replay；本地、远端候选、正式发布和公开 PyPI 的文件摘要一致。
- PyPI 保留 neilmorse 审批和禁止管理员绕过，仅增加精确 v0.2.3 标签授权。
- 公开 PyPI 仓库外全新 Python 3.12.15 环境无缓存、无锁约束安装通过，实际 SDK 2.3.0；两模式、原始 JSON-RPC、八工具 HTTP、Schema/注解、脱敏/16 KiB 预算及七 replay 均通过。安装后的 CLI 目录加载器另行接受 shop-product Context ID，确认修复已进入公开包。
- 发布初期安装索引尚未列出新版本，前三次解析失败；索引出现且独立解析成功后，相同命名安装通过。保留失败日志，没有用本地 wheel 或源码替代公开安装。
- [Registry 工作流](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41268759615) 使用固定版本/源提交、校验摘要的官方 publisher 与短时 GitHub OIDC，发布成功；[公开 API](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp) 已独立确认 io.github.neilmorse/spring-runtime-mcp 0.2.3 的包标识与版本。

| 文件 | SHA256 |
| --- | --- |
| spring_runtime_mcp-0.2.3-py3-none-any.whl | `af80539a4beb436cb271a21acec2a75b79f24136bf831e10b8519a3b9e21cb58` |
| spring_runtime_mcp-0.2.3.tar.gz | `78b7c63d9a598f747ca72d3d31a423e56fea4d67d946efad406fab62e4427c48` |
