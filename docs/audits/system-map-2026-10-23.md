# 当前系统地图 — 2026-10-23

范围：`src/spring_runtime_mcp/` 当前工作树，基线 HEAD `49ffdb9` 加未提交修改。只做静态检查，未运行测试、构建或连接目标。旧 [2026-10-18 架构审计](project-state-and-architecture-audit-2026-10-18.md) 保留历史意义，不作为当前入口说明。

## 1. 统计口径

生产包共有 53 个 Python 文件。依赖采用 AST 的 Import / ImportFrom，解析相对导入，包含函数内导入；每个依赖方对同一文件只计一次。不包含第三方包、运行时对象调用、动态导入或测试依赖。箭头 `A → B` 表示 A 导入 B，不代表数据传输方向。

源码指纹 SHA-256：`ddd4a5c7f0d63931e0455ac1454ff1dd4b3c03784a132909626bf374f48aa4a3`。

指纹计算按包内相对路径字典序排列全部 `.py`，依次拼接 `相对路径 UTF-8 + NUL + 文件字节 + NUL` 后取 SHA-256；用于辨认本次静态基线，不绑定旧覆盖率报告。

## 2. 模块依赖图（按层归并）

| 依赖方 | → 被依赖模块 / 层 |
| --- | --- |
| `adapters` | `analyzers`, `contracts`, `models`, `policy`, `transport` |
| `analyzers` | `contracts`, `models` |
| `cli.py` | `__init__.py`, `adapters`, `models`, `policy`, `server.py`, `services.py`, `transport` |
| `contracts` | `models` |
| `diagnostics.py` | `models`, `policy`, `transport` |
| `policy` | `models`, `transport` |
| `replay.py` | `adapters`, `contracts`, `diagnostics.py`, `models`, `policy`, `services.py`, `snapshots.py`, `tools`, `transport` |
| `server.py` | `__init__.py`, `contracts`, `diagnostics.py`, `models`, `policy`, `services.py`, `snapshots.py`, `tools`, `transport` |
| `services.py` | `models`, `policy`, `snapshots.py` |
| `snapshots.py` | `models`, `policy` |
| `tools` | `adapters`, `analyzers`, `contracts`, `diagnostics.py`, `models`, `policy`, `services.py`, `snapshots.py`, `transport` |
| `transport` | `models`, `policy` |

这是实际导入图，不是理想分层。policy 与 transport 的归并图存在双向边，但不能仅据此断言具体文件循环导入。模型处于共用底层，工具层负责将适配器、分析器和安全出口连接起来。

## 3. 入口清单

| 入口 | 定位 | 可见行为 |
| --- | --- | --- |
| 安装命令 spring-runtime-mcp / 模块启动 | [cli.py](../../src/spring_runtime_mcp/cli.py) / main | CLI 与环境变量装配、配置错误 stderr、启动 STDIO |
| MCP 生命周期 / 协议流 | [server.py](../../src/spring_runtime_mcp/server.py) / run_stdio | 官方 SDK 管理协议；有界 stdin 与工具响应出口 |
| MCP tools/list、tools/call | 同文件 / build_server 的两个回调 | 固定工具描述符、参数/结果校验、调用总预算 |
| 工具注册分发 | [registry.py](../../src/spring_runtime_mcp/tools/registry.py) / call_tool | 八个固定 Handler |
| 本地集成装配 | server.py / build_services、build_server | 注入 Services，不主动建立目标连接 |
| 固定场景重放 | [replay.py](../../src/spring_runtime_mcp/replay.py) / main | 包内 JSON 事实经相同工具处理后一次退出 |

八工具与入口文件：

| 注册名 | Handler 文件 |
| --- | --- |
| springboot_analyze_startup | [analyze_startup.py](../../src/spring_runtime_mcp/tools/analyze_startup.py) |
| springboot_check_migrations | [check_migrations.py](../../src/spring_runtime_mcp/tools/check_migrations.py) |
| springboot_detect_drift | [detect_drift.py](../../src/spring_runtime_mcp/tools/detect_drift.py) |
| springboot_diagnose_health | [diagnose_health.py](../../src/spring_runtime_mcp/tools/diagnose_health.py) |
| springboot_inspect_beans | [inspect_beans.py](../../src/spring_runtime_mcp/tools/inspect_beans.py) |
| springboot_inspect_config | [inspect_config.py](../../src/spring_runtime_mcp/tools/inspect_config.py) |
| springboot_search_openapi | [search_openapi.py](../../src/spring_runtime_mcp/tools/search_openapi.py) |
| springboot_verify_mappings | [verify_mappings.py](../../src/spring_runtime_mcp/tools/verify_mappings.py) |

包未提供供外部请求的 HTTP 服务路由；这里的 HTTP 是向已登记 Actuator/OpenAPI 发起读取。开发检查脚本不属于 MCP 工具入口。

## 4. 事实核心与风险排序

以下按共用安全/协议边界及影响范围优先排序，辅以直接依赖数与修改频次，不是由覆盖率自动计算的缺陷排名。提交次数来自全部 15 次 Git 提交，不含未提交改动。行/分支数值引用 [历史覆盖率表](coverage-risk-zoning-2026-10-23.md)，本次未重新测量，不能与当前源码指纹视为同一次采集。

| 顺序 | 文件 | 生产直接依赖方 | 提交次数 | 历史行 / 分支 % | 风险依据 |
| --- | --- | --- | --- | --- | --- |
| 1 | [transport/actuator_http.py](../../src/spring_runtime_mcp/transport/actuator_http.py) | 1 | 3 | 85.1 / 66.1 | 所有在线读取共用，直接引用数低不表示影响小 |
| 2 | [server.py](../../src/spring_runtime_mcp/server.py) | 1 | 5 | 86.1 / 57.1 | 协议边界且提交次数最多 |
| 3 | [contracts/definitions.py](../../src/spring_runtime_mcp/contracts/definitions.py) | 16 | 2 | 81.8 / 77.0 | 共用参数与工具契约 |
| 4 | [models/common.py](../../src/spring_runtime_mcp/models/common.py) | 38 | 2 | 95.5 / 75.0 | 被引用最多，承载错误与预算模型 |
| 5 | [services.py](../../src/spring_runtime_mcp/services.py) | 13 | 1 | 96.2 / 50.0 | 共用读取并发与时限 |
| 6 | [policy/sanitization.py](../../src/spring_runtime_mcp/policy/sanitization.py) | 8 | 3 | 93.6 / 90.8 | 强制脱敏边界 |
| 7 | [tools/support.py](../../src/spring_runtime_mcp/tools/support.py) | 9 | 3 | 92.2 / 71.4 | 共用分页、结果和时限包装 |
| 8 | [snapshots.py](../../src/spring_runtime_mcp/snapshots.py) | 5 | 2 | 89.8 / 76.6 | 跨页证据与策略复核 |

高引用、频繁修改、低覆盖没有集中在同一文件。`transport/stdio.py` 的历史 28.6% 行覆盖、0% 分支覆盖也不能单独证明它最危险；子进程采集范围尚未核实。

## 5. 考古遗迹检查

| 检查 | 观察 | 限制 |
| --- | --- | --- |
| 注释掉的大段代码 | src 中未发现连续至少 5 行的纯注释块 | 只作候选筛查，不覆盖字符串中的代码或短注释块 |
| TODO/FIXME/HACK/XXX | src、tests、scripts 的 Python 文件中未发现行首注释标记 | 不代表没有未完成行为 |
| 无引用公开定义 | 在上述 Python 文件的 Name、Attribute、ImportFrom 名称扫描中，未发现 src 顶层公开函数/类的零引用候选 | 同名会产生误匹配；不是完整可达性或导出审计 |
| 冗余重导出候选 | tools/support 的 __all__ 含 SnapshotStore；本轮未找到仓内通过该路径使用它的代码 | SnapshotStore 本体被使用；没有外部使用证据，不能据此删除重导出 |
| 文档遗留 | 旧宿主图、统一适配器签名、唯一 catch-all、错误的 Services 伪代码 | 已在当前惯例与接手说明中修正；旧审计明确标为历史快照 |

## 6. 核心数据流

| 顺序 | 层 / 符号 | 数据与边界 |
| --- | --- | --- |
| 1 | CLI → build_services | 可信本地参数、环境变量、可选 SourceCatalog → Services；默认配置诊断关闭 |
| 2 | SDK → build_server 回调 → registry | JSON-RPC 参数 → Schema 校验 → Handler；共享调用时限 |
| 3 | Handler → Services.read | cursor 命中时走内存；采集时核对目标，每目标最多两个读取槽 |
| 4 | ResponseGateReader → ActuatorHttpTransport | 逻辑 endpoint → 固定 GET → 已批准回环地址；TLS、peer、状态码、媒体类型、响应体预算检查 |
| 5 | bounded_json → ParsedObservation | 原始字节 → 有界 JSON 与身份/时间/端点元数据；尚未作为公开结果输出 |
| 6 | Adapter / Analyzer | 规范化、建图或比较；缺口沿 gaps/Fact 传递；配置等路径使用专项投影和脱敏 |
| 7 | SanitizerPipeline → 分页 / SnapshotStore | 脱敏结果 → 页与有界内存快照；续页复核查询绑定、到期和适用的策略变化 |
| 8 | 输出 Schema / serialize_response / SDK 写流 | 校验结果契约与安全投影；structuredContent 加兼容文本；完整工具帧最多 16,384 字节 |
| 9 | SDK stdout | 向 MCP 客户端返回 JSON-RPC |

没有业务数据库落库；快照保存在进程内，重启后消失。网络外发为对登记目标的读取。离线 replay 从固定包内资源产生观测后复用 Handler，控制台隔离在 transport/stdio.py，不经过在线 HTTP 连接器。

本地图描述现状，不作为阶段 1a 的人工行为确认，也不授权新增特征测试或迁移实现。
