# 当前实现约定

本文用于修改现有模块时确认真实接口和传递关系。新增代码规则与核心保护区见 [AGENTS.md](../../AGENTS.md)。

## 接口与数据

Python 使用 snake_case 与 PascalCase，公共 JSON 使用 camelCase。八工具处理器均由 `@tool_handler` 包装，接收 `arguments: Mapping[str, Any]` 与 `services: Services`，异步返回领域信封。

适配器输入输出各自定义，不能统一改造成假定签名：

| 适配器入口 | 输入与返回 |
| --- | --- |
| `normalize_beans` | ParsedObservation 与 budget → BeanGraph |
| `normalize_conditions` | ParsedObservation 与 budget → ConditionReport |
| `normalize_config` | env、configprops、ConfigQuery、SanitizerPipeline，可选 policy → profiles/items/gaps |
| `normalize_health` | body 和组件、详情、健康过滤及深度参数 → overall/items/gaps |
| `normalize_mappings` | body 和路由、方法、控制器及 Context 参数 → items/gaps |
| `normalize_migrations` | flyway、liquibase、MigrationQuery → items/gaps/状态 |
| `normalize_openapi` | body、OpenApiQuery → version/candidate/items/gaps/blocked |
| `normalize_startup` | body 和名称、耗时及深度参数 → 六项 tuple，由工具层解包 |
| `load_source_catalog` | 已解析 Mapping、target_id 与 budget → SourceCatalog；文件读取由 CLI 完成 |

Fact 的 known/unknown/notReported/redacted 表示不同证据状态；known + null 可表示根 Context 没有父节点。None、空集合和布尔返回值的含义以调用点为准。新增公共字段的缺失状态遵循 Schema。

## 错误与缺口

- NormalizationError 继承 ValueError，AnalysisLimit 继承 NormalizationError。工具边界先处理领域异常，再转换指定解析错误、超时和意外错误。
- 适配器可返回 gaps，由构造领域信封的工具层调用 `partial()`。过滤结果为零与证据不可见分别表达。
- `failed()` 将 INVALID_ARGUMENT 映射为 invalid，将 ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED 映射为 denied，其余映射为 unavailable；共同返回 `data=null`、`totalMatched=null`、不可用 coverage 及 errors 数组。
- ResponseGateReader 将传输错误转换为固定 EndpointReadError；TypeError/AssertionError 重抛。协议及工具边界的 catch-all 产生固定安全错误，连接器清理后重抛路径保留取消和失败语义。
- CLI 配置错误写 stderr 并退出 2；KeyboardInterrupt 退出 130。原异常文本、堆栈和凭据不出站。

错误码和配方实现见 [diagnostics.py](../../src/spring_runtime_mcp/diagnostics.py)，调用者语义见[调用策略](../contracts/tool-calling-policy.md)。

## 分页与预算

通用 `tools.support.finalize` 先脱敏、再分页，按含结构与文本两份内容的 JSON-RPC 帧计量。只有 RESPONSE_TOO_LARGE 触发条目数收缩，其他安全错误继续传播。Bean 工具独立分页，还可裁剪关联数组或条件分析，并记录 RESPONSE_BUDGET 等缺口。

SnapshotStore 保存共享的不可变编码记录及游标 offset；续页只解码和投影当前页，按实际 consumed 推进。游标绑定工具和规范化查询，策略戳变化触发安全复核；TTL 从快照创建时计算，访问及续页不延长期限。

| 限制 | 当前值与实现位置 |
| --- | --- |
| 单工具总时限 | 15 秒；`tools/support.py`、宿主回调 |
| 每目标并发读取 | 2；`services.py` |
| 单次 Services 读取等待 | 最多 5 秒及剩余调用时限 |
| socket 建连预算 | 所有候选地址共享 2 秒，并受读取时限约束 |
| HTTP 响应头 | 32 KiB 累计预算 |
| HTTP 响应体 | 8 MiB；gzip 压缩前后分别限制 |
| 有界 JSON 深度/节点 | 64 / 100,000 |
| AnalysisBudget 默认 visits/depth | 20,000 / 16 |
| CallBudget 总 visits | 20,000 |
| maxResults 默认/上限 | 50 / 50 |
| 完整工具响应帧 | 16,384 UTF-8 字节 |
| STDIO 输入帧 | 64 KiB |
| Source catalog 文件 | 256 KiB |
| 快照 TTL/存储预算 | 60 秒 / 32 MiB |

`CALL_BUDGET` 使用 ContextVar；宿主建立 scope，工具包装器复用或创建 scope，finally 复位。图访问、上游读取与输出字节预算是不同限制。

## 装配与 I/O

环境变量读取集中在生产 `cli.py`；维护脚本和测试各自管理执行环境。HTTP 使用 `http.client` 并经工作线程执行；在线协议宿主使用官方 SDK。`transport/stdio.py` 的控制台隔离辅助供离线 replay 使用。

未登记 SourceCatalog 时，Services 使用带 SOURCE_CATALOG_UNPROVIDED 的空事实目录。未登记配置读取策略时，env/configprops 能力关闭。健康端点的 503 可作为健康证据，其他端点的 503 按不可用处理。
