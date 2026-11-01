# 小众生产项目 HertzBeat：功能、稳定性与可用性验收

日期：2026-10-23。目标：在一个规模适中、真实生产使用但相对小众的项目上重复本地隔离验收，
补足大型金融/数据平台之外的 Spring Boot + JPA/Flyway + H2 + Sureness 组合。只访问自行
启动的回环目标，不连接任何生产实例，不执行监控任务、告警或业务写请求。

复现资产见 [examples/niche-project-matrix](../../examples/niche-project-matrix/README.md)
和 [check_niche_project_runtime.py](../../scripts/check_niche_project_runtime.py)。

## 固定项目与构建

| 项目 | 固定 tag / revision | 总 / 主 Java 文件 | 原生 Boot | 构建 | 运行时 |
| --- | --- | ---: | --- | --- | --- |
| Apache HertzBeat | v1.7.3 / `67ad4b04ef1b06b62f0e5030a26d0ca069294fa3` | 1387 / 975 | 3.4.2 | Maven / Java 17 | 原生 manager + 内嵌 H2 文件 |

只构建 `hertzbeat-manager` 及其 reactor 依赖；跳过上游测试、Checkstyle、Spotless、
文档和发布装配。上游测试、前端 UI 和发布包未验证。

## 隔离与启动

- 外部配置通过 `niche.properties` 传入，未命名为 `application.properties`，保留原生
  `application.yml` 的 H2/Flyway/`prod` profile 默认值。
- H2 文件位于临时副本 `.niche-diagnostics/data/`，只监听回环随机端口；无 MySQL、
  PostgreSQL、Kafka、外部模型或真实监控目标。
- 测试启动器保留 HertzBeat 原生 `Manager`，注入 2048 步启动缓冲和一个纯 Servlet
  `DiagnosticSecurity`。过滤器只匹配 `/actuator/**`：GET/HEAD、匿名 401、普通 Bearer
  403、管理员放行；不引入 Spring Security。
- HertzBeat 的 Sureness 会拦截合成 Bearer；临时 classpath 前置一份 `sureness.yml`，
  仅追加 `/actuator/**===*` 放行。业务 `/api/**` 的 Sureness 规则未改；这是测试配置，
  不是生产安全建议。
- Spring AI MCP server 保持原生启用。首次尝试关闭 `spring.ai.mcp.server.enabled` 时，
  容器仍创建 `webMvcSseServerTransportProvider`，因缺少依赖 Bean 启动失败；该属性与
  自定义初始化存在耦合，本轮保留启用且不调用外部模型。

## 观察

- **Flyway/H2**：原生 Flyway 端点返回 5 条 APPLIED，配置诊断默认关闭，健康 db 组件
  可读。没有数据库暂停/恢复场景；H2 为内嵌数据库，可用性只覆盖目标停止/重启。
- **启动树**：2048 步缓冲下仍为 partial，保留 `STARTUP_NODE_LIMIT`、
  `STARTUP_DEPTH_LIMIT`、`STARTUP_ORPHAN_STEP` 等缺口；没有把 partial 说成完整时间线。
- **Bean 图**：875 个 Bean、1167 条依赖，安全投影后 873 个可见 Bean；87 页穷尽；
  `totalMatched=null`，保留 `ASSOCIATION_LIMIT`、`GRAPH_LIMIT_REACHED` 等预算缺口。
- **路由**：`/api/monitors` 在原生 mappings 中可正向匹配；业务 API 的 Sureness
  鉴权没有被测试绕过。

## 快速验收摘要

65 秒快速运行全部断言通过：415 次调用；启动 12.579 秒 / 同宿主重启 14.797 秒；
管理端 401/403、两种 SDK 协议、非法参数、Flyway、路由、健康、启动、配置默认关闭、
OpenAPI 负向、目标停止/重启和游标过期均通过；最大完整回包 15,072 字节，
中位/p95 延迟 438.666 / 1260.290 ms。结果为 `accepted=true`、`failureCodes=[]`。

## 正式 300 秒运行

脱敏聚合报告见
[results/hertzbeat-final-300s.json](../../examples/niche-project-matrix/results/hertzbeat-final-300s.json)
（SHA256 `656977d040dc0e5de4f8264ed921933b71ad3b1fbac0d1afe1537224a63da560`）。

| 指标 | 正式 300 秒结果 |
| --- | --- |
| 验收 | `accepted=true`，`failureCodes=[]`，退出 0 |
| 调用 | **1594 次**真实 MCP 调用 |
| 状态 | ok 375 / partial 1210 / denied 2 / invalid 2 / unavailable 5 |
| 预期错误 | 匿名/普通 Bearer 401/403、非法参数、OpenAPI 固定入口 404、配置默认关闭、游标绑定/过期、目标停止；无计划外错误码 |
| 库存 | 1 个 Context、875 个 Bean、1167 条依赖；安全投影后 **873 个可见 Bean**，**87 页穷尽**，无重复页、快照稳定；`totalMatched=null`，保留 `ASSOCIATION_LIMIT`、`BEAN_GRAPH_INCOMPLETE`、`GRAPH_LIMIT_REACHED`、`REDACTED_IDENTIFIERS` 等 partial 缺口 |
| 原生域 | 路由 `/api/monitors` ok/complete；db 健康 ok/complete；Flyway **5 条 APPLIED**；启动树 partial，保留 `STARTUP_NODE_LIMIT`、`STARTUP_DEPTH_LIMIT`、`STARTUP_ORPHAN_STEP`、`STARTUP_TIMELINE_INCOMPLETE`；漂移 partial，保留 Bean 索引/源事实缺口 |
| 延迟 | 中位数 547.253 ms；p95 1136.386 ms；最大 1849.020 ms |
| 完整回包 | 最大 **15,072 字节**，低于 16,384 字节硬上限；outputSchema、独立安全门和完整帧预算均通过 |
| 启动 | 首次 13.653 秒；同一宿主重启 14.395 秒；启动缓冲 2048 步 |
| 宿主资源 | MCP 宿主 RSS 83,680 → 101,912 KiB；FD 7 → 7；并发后仍存活；全部 MCP 子进程退出 |
| 清理 | 目标进程停止、MCP 子进程全部退出；H2 文件保留在临时副本，不进入源码或结果 |

partial 1210 次主要来自 Bean 图预算、启动/条件证据和分页/回包预算；这不是组件详情完整
或业务监控正常的结论。H2 为内嵌数据库，本轮没有数据库暂停场景；可用性覆盖目标停止/
重启和健康读取。

## 验证

| 检查 | 结果 |
| --- | --- |
| 快速验收 | 415 次调用，`accepted=true`，`failureCodes=[]` |
| 正式 300 秒 | 1594 次调用，`accepted=true`，`failureCodes=[]` |
| 契约/静态检查 | 本轮未改生产 Python 代码；新增 harness 已通过 Ruff；当前 925 项 pytest、mypy 53、Ruff 115、契约通过 |
| pre-release 门禁 | 6/6 阶段通过：925 passed；工作区有 81 处未提交/未跟踪验收材料，按 `--allow-dirty` 记录为警告，不是代码失败 |
| 结果清理 | 目标进程、MCP 子进程退出；结果 JSON 无凭据/令牌/密码键；无 Docker 容器 |

## 限制

- 只验证 HertzBeat v1.7.3 / Java 17 / Boot 3.4.2 / H2 的一个固定提交，不是 MySQL/
  PostgreSQL 生产部署、集群、HA、长期运行或真实监控流量验收。
- 管理 Bearer 过滤器和 Sureness 放行规则是测试注入，不是上游推荐配置；Spring AI MCP
  server 保留启用但未调用外部模型。
- 启动树和 Bean 图均有显式 partial 缺口；300 秒并发只说明本机短时稳定性，
  RSS/延迟不是生产容量基准。
- 未验证 UI、上游测试、告警投递和发布包。