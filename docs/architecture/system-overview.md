# 系统概览

Spring Runtime MCP 是 Python 3.11+ 的独立 STDIO 服务，为编码 Agent 提供登记 Spring Boot 回环实例的只读运行证据。安装入口为 `spring-runtime-mcp`；版本源为 [__init__.py](../../src/spring_runtime_mcp/__init__.py)，依赖及构建配置见 [pyproject.toml](../../pyproject.toml)，精确开发环境由 [uv.lock](../../uv.lock) 固定。

## 模块与入口

| 模块 | 当前职责 |
| --- | --- |
| `cli.py` | 参数、环境变量、Bearer 和可选源码目录加载，装配服务并启动 STDIO |
| `server.py` | 官方 MCP SDK lowlevel Server，工具发现、参数/结果验证、共享调用时限与有界协议出口 |
| `services.py` | 登记目标、读取器、脱敏、源码事实、快照及每目标读取槽协调 |
| `transport/` | 固定端点 HTTP、响应门禁、有界 JSON、帧序列化和离线资源读取 |
| `policy/` | 配置读取范围、字段投影、脱敏及独立输出安全门 |
| `models/` | Fact、查询、观测、图模型及分析/调用预算 |
| `adapters/` | 将 Actuator/OpenAPI 结构归一化为领域事实和证据缺口 |
| `analyzers/` | Bean 图遍历、条件链和漂移影响等确定性分析 |
| `tools/` | 八个处理器、固定注册、信封合成及分页 |
| `contracts/`、`schemas/` | 参数规范化和随包分发的八工具 Schema |
| `snapshots.py` | 有界脱敏快照、查询绑定游标与续页 |
| `replay.py`、`replay_data/` | 使用相同处理器执行一次性离线场景 |

模块按上述职责协作；这不是强制的单向导入图。模型为共享基础，工具层将读取、归一化、分析和安全出口连接起来。

[CLI](../../src/spring_runtime_mcp/cli.py) 的 `main` 调用 [server](../../src/spring_runtime_mcp/server.py) 的 `build_services` 和 `run_stdio`。`build_services` 装配单个 origin/target，工具读取时才建立连接。`build_server(services)` 注册 `tools/list`、`tools/call` 回调，支持测试或本地集成注入 Services。

## 在线数据流

1. CLI 校验 origin、目标、超时、可选配置策略及 Bearer 变量名称；源码目录经有界读取和 JSON 校验加载。
2. SDK 接收请求；宿主验证参数并建立共享 15 秒调用时限，固定注册表分发到工具。
3. 首次查询经 Services 取得目标读取槽，ResponseGateReader 校验能力，标准库连接器向固定路径发 GET。
4. 有界响应通过状态、媒体类型与 JSON 检查，成为带目标、快照、观测时间和端点身份的 ParsedObservation。
5. 适配器和分析器建立完整可见事实及关联，工具层将 gaps 汇入 coverage/status，过滤、计数、稳定排序。
6. SanitizerPipeline 处理输出，分页层按记录数及完整响应字节预算选择本页；需要续页时保存脱敏快照。
7. 宿主验证输出 Schema，独立安全门及 SDK 实际序列化出口复核完整 JSON-RPC 帧，返回结构与兼容文本副本。

## 状态与资源

首次查询采集运行证据；带 cursor 的查询沿用原参数及快照，期间不重新读取目标。SnapshotStore 默认 60 秒绝对 TTL、32 MiB 总预算，使用 LRU 淘汰；进程重启后快照丢失。策略戳变化时复核整份缓存事实，失败则删除该快照的相关句柄。

Services 每目标最多两个并发读取，等待槽位也计入调用时限。单次服务读取等待最多 5 秒并受剩余时限约束；CLI 的 reader timeout 默认 5 秒、允许大于 0 且不超过 60 秒。DNS 系统调用和工作线程的清理限制见[安全架构](security-and-sanitization.md)。

## 工具与证据

固定注册八工具，按名称排序，具体选择器和结果以 [Schema](../../src/spring_runtime_mcp/schemas/tools-contract.json) 及[调用策略](../contracts/tool-calling-policy.md)为准。Fact 区分 known、unknown、notReported、redacted；证据缺失沿 gaps 传至工具层，必要时返回 partial 和未知总数。

可用性和支持范围见[产品规格](../../SPEC.md)。默认验证使用合成 fixtures 和测试自建回环服务；真实目标验收需独立授权。开发检查及发行包验证见[发布流程](../launch/README.md)。
