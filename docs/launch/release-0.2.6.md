# 0.2.6 Alpha — 2026-11-01

本版处于发布准备阶段；完整门禁、产物比对和公开安装验证待完成。
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

首次接入见[首次查询指南](../first-query.md)，源码目录见[接入指南](../source-catalog.md)。
目标暴露、配置和重启仍须维护者授权。

## 发布批次

待本地/远端完整门禁与公开安装验收。保留精确 PyPI 标签授权、neilmorse 审批及禁止管理员绕过。
