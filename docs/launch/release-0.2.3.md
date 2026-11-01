# 0.2.3 Alpha — 2026-11-01

本版修复 source catalog 对 Spring Context ID 的错误校验。发布已获操作者授权，当前记录为发布准备状态；正式发布、公开安装与 Registry 的结果完成后补齐。

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

正式发布后使用公开 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.3 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.3 --base-url http://127.0.0.1:18081
```

第二条命令是 STDIO 宿主；目标先按[配置指南](../target-app-setup.md)准备。源码目录与凭据仅通过既有 --source-catalog / --token-env 接入，配置诊断默认关闭。

## 发布批次

待完成：干净提交的完整本地/远端门禁、wheel/sdist 隔离安装、正式发布、公开 PyPI 全新安装、GitHub Release、精确版本 MCP Registry 提交与回读。
