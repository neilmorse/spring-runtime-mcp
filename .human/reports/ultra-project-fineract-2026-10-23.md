# 超大型生产系统 Fineract：功能、稳定性与可用性验收

日期：2026-10-23。目标：按用户要求自行拉取超大型真实生产项目，在本地隔离副本模拟线上
运行环境，完成八工具功能、稳定性和可用性测试。只访问自行启动的回环目标和一次性数据库，
不连接任何生产实例，不执行业务写请求、迁移或 repair。复现资产见
[examples/ultra-project-matrix](../../examples/ultra-project-matrix/README.md) 和
[check_ultra_project_runtime.py](../../scripts/check_ultra_project_runtime.py)。

## 固定项目与构建

| 项目 | 固定 tag / revision | 总 / 主 Java 文件 | 原生 Boot | 构建 | 运行时 |
| --- | --- | ---: | --- | --- | --- |
| Apache Fineract | 1.9.0 / `5d96e8cc32ff63f97d5ac15e19c6fafee0c31357` | 4565 / 4087 | 3.1.7 | Gradle 8.5 / Java 17 | 一次性 PostgreSQL 16，回环 HTTP |

Fineract 是真实金融机构使用的核心账务平台。本轮浅克隆固定 tag，只启动 provider 的一次性
本地实例；未部署、未接触生产集群或既有业务数据。上游测试、文档、UI 和完整发布包未验证。

构建遇到已停用 JCenter 的文档插件传递依赖 `com.burgstaller:okhttp-digest:1.10`。
临时副本通过 [fineract-build-workaround.patch](../../examples/ultra-project-matrix/fineract-build-workaround.patch)
在 `settings.gradle` 的 `pluginManagement` 中增加公共镜像
`https://maven.aliyun.com/repository/public` 作为回退，并追加 `dumpRuntimeClasspath`；
Fineract 的 Boot/BOM、provider 运行依赖和 classpath 未改。镜像可用性与供应链风险属于
本轮限制，不能把该构建命令当成长期可复现的官方构建。

## 隔离与启动

- 外部配置通过 `ultra.properties` 以命令行参数传给原生
  `ServerApplication.configureApplication`；不再把文件命名为 `application.properties`，
  避免遮蔽 classpath 中 Fineract 的原生默认配置。
- 启动器反射保留原生配置，注入 `BufferingApplicationStartup(2048)` 和管理专用
  `DiagnosticSecurity`。过滤器只匹配 `/actuator/**`，强制 GET/HEAD、匿名 401、
  非管理员 403、管理员 `ROLE_DIAGNOSTICS`；不替换 `/api/**` 原生 Basic Auth。
- PostgreSQL 使用一次性容器，仅发布到 `127.0.0.1` 随机端口；初始化脚本创建
  `fineract_tenants`、`fineract_default` 和专用用户。密码由脚本随机生成，只经环境变量
  传递，不写入 properties、命令参数或摘要。
- `env/configprops` 永不显示值；JMS/Kafka/外部事件/批处理/遥测/外部客户端关闭；
  数据库连接池连接超时 3 秒。全部目标结束由脚本清理。

## 本轮发现与闭环

### F1：JAX-RS 业务路由被写成“不存在”（已修复）

Fineract 的业务 REST 由 Jersey `ServletContainer` 注册在 `/api/*`。Actuator
`/actuator/mappings` 的 `dispatcherServlets` 只有 17 条 Spring MVC/Actuator 路由，
`servlets` 明确列出 Jersey 与 dispatcherServlet，但旧适配器完全忽略 `servlets`。

修复前 `springboot_verify_mappings` 对 `/api/v1/offices` 返回 `ok/complete` 和空结果，
等价于把证据源不覆盖写成路由不存在。修复后：

- 当查询路径可能由非 DispatcherServlet 容器覆盖时，返回 `partial`、
  `totalMatched=null` 和 `NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED`。
- `/actuator/health` 等可见 DispatcherServlet 路由仍正常正向匹配。
- 新增 4 个离线回归，覆盖 Jersey 覆盖、正向路由、无 servlets 的正常完整零结果。

业务 JAX-RS 路由本身仍不可由当前 Actuator 数据正向枚举；本轮只验证工具会保守降级，
不把 `observed=false` 当作业务路由不存在，也不宣称 JAX-RS 正向兼容。

### F2：8192 步启动快照超出归一化预算（容量限制，保留）

8192 步 `BufferingApplicationStartup` 的原生启动 JSON 约 1.74 MB，当前归一化预算返回
`NORMALIZATION_LIMIT`（HTTP 200，安全失败）。本轮把测试启动缓冲降到 2048 步以取得
正向启动证据；8192 步结果保留为已知容量边界。没有提高产品解析/遍历预算，也没有把
`NORMALIZATION_LIMIT` 说成启动无瓶颈。

### F3：数据库暂停后的可用性

暂停 PostgreSQL 后，健康端点超出 5 秒读取预算，MCP 返回
`unavailable / TARGET_TIMEOUT`；Bean 读取仍可用；恢复数据库后健康回到 UP。结论是
有界降级和恢复，而不是健康详情完整、告警及时或生产 HA 通过。

## 快速验收摘要

65 秒快速运行（`--soak-seconds 65`）在 F1 修复后全部断言通过：

- 486 次真实 MCP 调用；目标初始化 2544 个 Bean、5626 条依赖，安全投影后 2524 个可见
  Bean；252 页穷尽，无重复页、快照稳定，`totalMatched=null` 与 partial 缺口保留。
- 管理端匿名 401、普通 Bearer 403、管理员正向读取；非法参数 `INVALID_ARGUMENT`。
- 两种官方 SDK 协议；目标停止时 `TARGET_CONNECTION_REFUSED`，同一宿主重启后恢复。
- 60 秒游标过期和查询绑定错误；配置默认关闭；OpenAPI/Liquibase 固定入口不可读负向。
- 数据库暂停/恢复；Bean 读取在数据库不可用时仍可用；JAX-RS 业务路由探针返回
  `partial` + `NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED`。
- 最大完整回包 15,170 字节，低于 16,384 字节硬上限；结果均通过 outputSchema、
  独立安全门和完整帧预算。

## 正式 300 秒运行

正式运行命令：

```bash
uv run --no-sync python scripts/check_ultra_project_runtime.py \
  --project ~/.cache/spring-runtime-mcp/ultra-matrix-20261023/fineract \
  --output ~/.cache/spring-runtime-mcp/ultra-matrix-20261023/fineract-final-300s.json \
  --soak-seconds 300
```

首次 300 秒尝试在 soak 中途被外部中断，未生成报告；本节使用随后完整重跑的结果，
不把中断计作通过或失败。脱敏聚合报告见
[results/fineract-final-300s.json](../../examples/ultra-project-matrix/results/fineract-final-300s.json)
（SHA256 `363e00e7c1c061fe3196e9f17334d8af7c8235ba21c9aa70e33302846f2207ed`）。

| 指标 | 正式 300 秒结果 |
| --- | --- |
| 验收 | `accepted=true`，`failureCodes=[]`，退出 0 |
| 调用 | **1202 次**真实 MCP 调用 |
| 状态 | ok 235 / partial 956 / denied 2 / invalid 2 / unavailable 7 |
| 预期错误 | 匿名/非管理员 401/403、非法参数、固定 OpenAPI/Liquibase 入口 404、配置能力默认关闭、游标绑定/过期、目标停止、数据库暂停超时；无计划外错误码 |
| 库存 | 1 个 Context、2544 个 Bean、5626 条依赖；安全投影后 **2524 个可见 Bean**，**252 页穷尽**，无重复页、快照稳定；`totalMatched=null`，保留 `ASSOCIATION_LIMIT`、`BEAN_GRAPH_INCOMPLETE`、`GRAPH_LIMIT_REACHED`、`REDACTED_IDENTIFIERS` 等 partial 缺口 |
| 延迟 | 中位数 743.034 ms；p95 2583.734 ms；最大 5011.524 ms（数据库暂停超时调用） |
| 完整回包 | 最大 **15,170 字节**，低于 16,384 字节硬上限；outputSchema、独立安全门和完整帧预算均通过 |
| 启动 | 首次 78.779 秒；同一宿主重启 47.604 秒；启动缓冲 2048 步 |
| 宿主资源 | MCP 宿主 RSS 91,324 → 104,268 KiB；FD 7 → 7；并发后仍存活；全部 MCP 子进程退出 |
| 数据库可用性 | 暂停前 UP → 暂停后 `unavailable / TARGET_TIMEOUT`（未保持 UP）→ 恢复后 UP，1 次恢复尝试；暂停期间 Bean 读取仍可用 |
| JAX-RS 探针 | `/api/v1/offices` 返回 `partial` + `NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED`，`observed=false`，不作为业务路由不存在的证据 |
| 清理 | 目标进程停止、数据库容器删除、MCP 子进程全部退出 |

这不是“所有组件详情完整”的结果：partial 956 次主要来自 Bean 图预算、启动/条件证据缺口和
需要分页的大结果；失败的错误码均为有界安全降级或预期负向。300 秒窗口只说明本机短时稳定性，
不是生产容量、长期泄漏或高可用基准。

## 验证

| 检查 | 结果 |
| --- | --- |
| 完整 pytest | **913 passed，32.06 秒**（新增 4 个 mappings 回归） |
| 首轮完整 pytest | 912 passed / 1 failed：`test_stdio_host_process_accepts_a_matching_fact_catalog` 在 300 秒重负载后失败；该测试单独重跑 0.80 秒通过，第二次全量 913 passed。测试未修改，保留为进程时序波动，不声称零抖动 |
| mypy | 53 个源文件通过（strict） |
| Ruff | `check` 通过，`format --check` 111 个 Python 文件通过 |
| 契约 | 8 组独立工具 Schema、144+ 合成断言通过 |
| 结果清理 | 目标进程停止、数据库容器删除、MCP 子进程全部退出；结果 JSON 无凭据/令牌/密码键 |

## 限制

- 只验证 Fineract 1.9.0 / Java 17 / Boot 3.1.7 / PostgreSQL 16 的一个固定提交，不是
  全版本矩阵、生产集群、HA、长期运行或真实业务流量验收。
- JAX-RS 业务路由仍不可正向枚举；只验证保守 partial/gap。OpenAPI 和 Liquibase 固定
  入口不可读，只做负向断言。
- 管理专用 Bearer 过滤器和启动缓冲是测试启动器注入，不是上游原生安全配置。
- 数据库暂停只验证短时恢复，不验证持久性、复制、故障切换或长期连接泄漏。
- 300 秒并发只说明本机有限窗口内的稳定性；RSS/延迟不是生产容量基准。
- Gradle 插件镜像回退只解决已停用 JCenter 制品，不证明上游构建在干净环境中无需修改。