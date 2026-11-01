# 0.2.5 Alpha — 2026-11-01

本版为发布候选，尚未公开发布。完整本地/远端门禁、产物摘要与公开安装验收待完成；
下方源补丁证据不替代本发布批次结果。旧版本标签和产物保留。

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

## 安装（发布后）

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.5 --version
```

首次接入见[首次查询指南](../first-query.md)。目标采集、暴露与重启仍须维护者授权。

## 发布批次

待完整门禁和发布后验收；保留 PyPI 精确标签授权、neilmorse 审批与禁止管理员绕过。
