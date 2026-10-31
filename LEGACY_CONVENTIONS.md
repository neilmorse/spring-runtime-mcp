# 现状惯例记录

核对日期：2026-10-23。范围：`src/spring_runtime_mcp/` 当前工作树，包含未提交修改。

本文只记录观察到的实现，不规定未来设计，也不确认这些行为都应保持。代码定位使用文件与符号名；测试覆盖率是历史测量，见 [系统地图](docs/audits/system-map-2026-10-23.md) 和 [覆盖率记录](docs/audits/coverage-risk-zoning-2026-10-23.md)。本次文档修订没有运行测试或连接目标。

## 1. 命名与实际接口

Python 函数和变量主要使用 snake_case，类使用 PascalCase，公共 JSON 字段使用 camelCase。内部辅助函数通常以下划线开头，但也有 `glob_matches`、`validate_arguments`、`parse_rfc3339` 等公开辅助函数；不能据此声称项目不使用 `validate_*`、`parse_*` 或布尔返回值。

八个工具函数均由 `@tool_handler` 包装，接收 `arguments: Mapping[str, Any]` 与 `services: Services`，异步返回结果信封。注册名为 `springboot_` 加工具名，固定按字母序列在 [registry.py](src/spring_runtime_mcp/tools/registry.py) 中。

适配器的参数、返回类型并不统一：

| 文件 / 函数 | 实际输入 | 实际返回 |
| --- | --- | --- |
| [beans.py](src/spring_runtime_mcp/adapters/beans.py) / `normalize_beans` | ParsedObservation；关键字 budget | BeanGraph |
| [conditions.py](src/spring_runtime_mcp/adapters/conditions.py) / `normalize_conditions` | ParsedObservation；关键字 budget | ConditionReport |
| [config.py](src/spring_runtime_mcp/adapters/config.py) / `normalize_config` | env、configprops、ConfigQuery、SanitizerPipeline；可选 policy | profiles、items、gaps 的 tuple |
| [health.py](src/spring_runtime_mcp/adapters/health.py) / `normalize_health` | body；component_path、include_details、include_healthy、max_depth | overall、items、gaps 的 tuple |
| [mappings.py](src/spring_runtime_mcp/adapters/mappings.py) / `normalize_mappings` | body；路径、方法、控制器和 context 过滤参数 | items、gaps 的 tuple |
| [migrations.py](src/spring_runtime_mcp/adapters/migrations.py) / `normalize_migrations` | flyway、liquibase、MigrationQuery | items、gaps、状态字符串的 tuple |
| [openapi.py](src/spring_runtime_mcp/adapters/openapi.py) / `normalize_openapi` | body、OpenApiQuery | version、candidate、items、gaps、blocked 的 tuple |
| [startup.py](src/spring_runtime_mcp/adapters/startup.py) / `normalize_startup` | body；名称、耗时和深度过滤参数 | 六项 tuple，调用方解包 |
| [source_catalog.py](src/spring_runtime_mcp/adapters/source_catalog.py) / `load_source_catalog` | 已解析 Mapping；target_id、budget | SourceCatalog；此函数不读取文件 |

`adapters/drift.py` 提供漂移分析辅助函数，不是上述八个 `normalize_*` 入口之一。适配器并非都调用 `partial()`；不少适配器返回 gaps，由工具层合并进信封。

## 2. 错误处理的实际路径

| 位置 | 捕获 / 抛出行为 | 外部表现 |
| --- | --- | --- |
| [models/common.py](src/spring_runtime_mcp/models/common.py) | NormalizationError 继承 ValueError；AnalysisLimit 继承 NormalizationError | 异常携带诊断码；捕获顺序影响结果 |
| [tools/diagnose_health.py](src/spring_runtime_mcp/tools/diagnose_health.py) 等八个 Handler | 先捕获 NormalizationError，再捕获 TimeoutError、指定解析异常、最后 Exception | 分别形成原诊断码、TARGET_TIMEOUT、MALFORMED_EVIDENCE、INTERNAL_ERROR 信封 |
| [transport/response_gate.py](src/spring_runtime_mcp/transport/response_gate.py) / `read` | 超时、NormalizationError、OSError 和其他 Exception 转换为 EndpointReadError；TypeError/AssertionError 重抛 | 保留端点及适用的 HTTP 状态，不包含原异常文本 |
| [transport/actuator_http.py](src/spring_runtime_mcp/transport/actuator_http.py) / `request` | 超时或取消时 abort，短暂等待工作线程后重抛；TLS 异常转换 | 不把取消当成功；清理等待使用 `contextlib.suppress` |
| 同文件 / `_open` 的 socket 工厂 | OSError 关闭 socket，可尝试下一条已检查的地址；BaseException 关闭 socket后重抛 | 宽泛捕获用于清理，不是网络异常归一化 |
| [server.py](src/spring_runtime_mcp/server.py) / `_call_tool`、`_result` | 各有 Exception 兜底 | 固定 INTERNAL_ERROR；未知工具由 `_call_tool` 抛 MCPError |
| [replay.py](src/spring_runtime_mcp/replay.py) / `main` | 有两处 Exception 兜底 | 固定失败结果或安全序列化回退 |
| [cli.py](src/spring_runtime_mcp/cli.py) / `main` | ConfigurationError 写 stderr 并退出 2；KeyboardInterrupt 退出 130 | 配置错误不会启动诊断会话 |

本次 AST 计数在 12 个生产文件中找到 14 个 `except Exception` / `except BaseException` 处理器；该计数不包含 `contextlib.suppress`。因此不存在“唯一 catch-all 在 HTTP 连接器”的现状。

辅助函数还会用 None、False、空集合表达解析失败、判断不通过或没有条目。例如 `server._valid_envelope` 验证失败返回 False，OpenAPI 引用解析失败可返回 None。不能把这些返回值一概解释为成功或证据不存在。

### 失败信封

[diagnostics.py](src/spring_runtime_mcp/diagnostics.py) 的 `failed()` 先用 `safe_code()` 规范诊断码，再生成：

| code | status |
| --- | --- |
| INVALID_ARGUMENT | invalid |
| ENDPOINT_UNAUTHORIZED、TARGET_NOT_REGISTERED | denied |
| 其他码，包括 TARGET_TIMEOUT、MALFORMED_EVIDENCE、INTERNAL_ERROR | unavailable |

共同字段为 `data=None`、`totalMatched=None`、`coverage.state="unavailable"`、`nextAction.kind="remediate"`。错误信息在 `errors` 数组中，不是单个 `error` 字段。`partial()` 与 `failed()` 是不同路径；部分证据不必然导致整个调用失败。

## 3. 外部依赖与 IO

| 依赖 / 入口 | 实际调用方式 |
| --- | --- |
| MCP SDK | `server.build_server` 创建 lowlevel Server；`server.run_stdio` 使用 SDK stdio_server；注册工具列表与调用回调 |
| jsonschema | Draft202012Validator 校验工具参数与输出；server 配有 RFC3339 格式检查 |
| 标准库 HTTP | http.client 同步连接，经 `asyncio.to_thread` 执行；不使用 requests/httpx 作为诊断连接器 |
| 目标选择 | CLI 装配一个 origin 与 target；工具参数不提供 URL 或请求头透传 |
| 地址与连接 | 当前仅允许回环地址；解析结果先全组检查，再按数字地址连接并检查 peer；HTTPS 使用默认验证上下文 |
| 请求方法 | ResponseGateReader 固定 GET；连接器只接受 GET/HEAD，拒绝重定向跟随；不读取环境代理配置 |
| 身份认证 | `--token-env` 指定环境变量名称，由 CLI 读取 Bearer 值，再传给连接器和 SanitizerPipeline；没有默认读取 `SPRING_RUNTIME_BEARER_TOKEN` 的路径 |
| 本地源码事实 | CLI 有界读取普通文件，解析 JSON 后交给 `load_source_catalog`；不会读取 catalog 中指向的源码 |
| 离线重放 | replay 使用包内固定资源，经 replay_files 安全读取后复用 Handler |

环境变量读取集中在生产代码的 `cli.py`：base URL、target、timeout、source catalog 的默认值，以及 `--token-env` 指定的变量。这个范围不包括仓库维护脚本或测试。

当前没有通用 HTTP 自动重试或 OpenAPI 多候选端点回退；socket 工厂在多个已批准地址间处理连接失败的行为与应用级重试不同。

`transport/stdio.py` 提供 `quiet_console` / `seal_console`，由 replay 使用；它不是在线 SDK 宿主。

## 4. 隐式约定

| 条件 | 实际语义 / 分支 |
| --- | --- |
| Fact 的 known / unknown / notReported / redacted | 区分已知、不可判断、未报告和被脱敏；known + None 可表示根 Context 没有父节点 |
| None、空集合、空字符串 | 语义依字段和调用位置确定；例如 STDIO 空字符串表示读取结束，不能宣称代码完全不使用空字符串 |
| `query.cursor` 有值 | 工具优先读取 SnapshotStore，续页不重新采集目标；参数摘要用于绑定原查询 |
| `config_policy is None` | 默认不开放 env/configprops；显式配置范围后才能进入配置诊断 |
| 未提供 SourceCatalog | `build_services` 创建带 SOURCE_CATALOG_UNPROVIDED 的空事实目录；Bean 工具将其视为事实来源限制，不等价于运行时 Bean 不存在 |
| HTTP 503 | 只有 health 系列端点可继续解析为健康证据；其他端点按不可用处理 |
| Health 缺少根 status | overall 可为 None；遍历节点使用 UNKNOWN 并记录 HEALTH_STATUS_UNOBSERVED，不等价于所有畸形输入都抛异常 |
| Health 只有聚合状态而无可见详情 | 可记录 HEALTH_DETAILS_NOT_VISIBLE；显式空 components 与未报告 components 有区别 |
| Health body 不是 dict | adapter 抛 ValueError；经过工具层时转换为 MALFORMED_EVIDENCE |
| Health 详情或深度受限 | Handler 标记 partial/truncated；在相关缺口下 totalMatched 为 None |
| OpenAPI 本地引用 | 在文档内解析并处理循环、深度与投影；不请求远程引用 |
| 脱敏 | SanitizerPipeline 使用字段投影、敏感键/值检查与已知秘密变体；标记为 `[REDACTED_BY_MCP]`；序列化还经过 output_guard |

### 分页与存储

通用 `tools.support.finalize` 先脱敏，再按 maxResults 切页，使用完整 JSON-RPC 双副本序列化计量；仅对 RESPONSE_TOO_LARGE 减半条目数，其他 NormalizationError 向上传播。剩余条目通过内存快照续页；零条目结果也可正常返回，不能写成“至少返回一项”。

Bean 工具有独立 `_page`：除条目数外还裁剪 aliases/dependencies/dependents；单项仍超限时可移除关联或条件分析，记录 RESPONSE_BUDGET，最后才返回失败。该响应字节预算与分析节点访问预算不是同一限制。

SnapshotStore 使用 OrderedDict；分页快照共享已编码的 header/items，游标记录 offset，`advance` 按本页实际 consumed 推进。默认 TTL 为 60 秒，内存预算为 32 MiB，续页不延长原始期限；重启丢失快照。脱敏策略标记变化时重新检查整个缓存快照，检查失败会移除相关游标；不是简单比较版本后抛固定版本不匹配错误。

server 的 `_result` 再检查完整帧；`_BoundedWriteStream.send` 在 SDK 实际序列化出口复核大小，超限替换为 RESPONSE_TOO_LARGE 信封。server 不执行条目二分分页。

### 预算与并发

`CALL_BUDGET` 是 ContextVar。宿主回调建立共享 deadline，`tool_handler` 复用已有 scope 或创建新 scope，并在 finally 中复位。Services 每目标两个读取槽，排队也计入时限；这是并发读取上限，不是“所有工具串行执行”。

| 参数 / 限制 | 当前值 | 来源 |
| --- | --- | --- |
| 工具总时限 | 15 秒 | tools/support.py |
| Services 单次读取等待上限 | 5 秒，并受剩余总时限约束 | services.py |
| ResponseGateReader 默认 timeout | 5 秒；构造参数允许大于 0 且不超过 60 | transport/response_gate.py |
| 上游响应体上限 | 8 MiB | transport/response_gate.py |
| 有界 JSON 默认深度 / 节点数 | 64 / 100,000 | transport/bounded_json.py 函数参数，不是 MAX_JSON_* 常量 |
| AnalysisBudget 默认 visits / depth | 20,000 / 16 | models/common.py；深度由调用方遍历逻辑使用 |
| CallBudget 总访问次数上限 | 20,000 | models/common.py |
| maxResults 默认值 / 上限 | 50 / 50 | contracts/definitions.py |
| 完整工具响应帧上限 | 16,384 UTF-8 字节 | transport/responses.py；含 structuredContent 与文本副本 |
| STDIO 输入帧上限 | 64 KiB | server.py |
| SourceCatalog 文件上限 | 256 KiB | cli.py |

## 5. 记录边界

当前系统的模块图、入口和完整数据流集中在 [系统地图](docs/audits/system-map-2026-10-23.md)。本记录不推导测试是否充分，不把历史覆盖率或静态可达性当成行为已验收；也不包含迁移建议、重构规则或已批准的行为清单。
