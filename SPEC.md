# Spring Boot 运行时诊断 MCP：当前产品规格

本规格描述仓库当前实现的产品范围。公开输入、输出、默认值和约束以 [tools-contract.json](src/spring_runtime_mcp/schemas/tools-contract.json) 为准；协作权限由 [AGENTS.md](AGENTS.md) 维护。文档入口为 [docs/README.md](docs/README.md)。

## 产品与接入

产品为 Python 3.11+ 独立 CLI，通过官方 MCP Python SDK 的 STDIO 宿主提供八个工具。CLI 启动时登记一个回环 origin 与 target，支持可选 Bearer 环境变量绑定、本地 Source catalog 和显式启用的配置诊断。安装与第一次查询见[首次接入](docs/first-query.md)。

目标地址只允许解析到 127.0.0.0/8 或 ::1；origin 仅含 http(s) scheme、host 和 port。实际连接使用数字地址并检查 peer，HTTPS 使用默认 TLS 验证。请求固定 GET、禁重定向、禁环境代理；工具参数只参与本地查询，不提供 URL、路径或请求头透传。

当前端点表固定在 `/actuator/` 下，OpenAPI 固定读取 `/actuator/openapi`。Basic、自定义管理基路径、自动能力探测、端点回退和远程目标不在当前支持范围。

## 八个工具

| 工具 | 当前能力与证据边界 |
| --- | --- |
| springboot_analyze_startup | 读取启动事件、耗时及父链，筛选并排序；缺失单位、父节点或深度证据保留缺口，重叠步骤不相加为总启动时间 |
| springboot_check_migrations | 归一化 Flyway/Liquibase 库存、状态、版本/身份及 checksum；可比较显式预期集合；pending、版本或耗时未报告时保持未知 |
| springboot_detect_drift | 比较调用者提供的 Bean、路由、迁移版本及 Profile 预期，结合依赖图和可用启动证据给出影响及证据分级 |
| springboot_diagnose_health | 读取整体健康、可见组件和固定 liveness/readiness；详情隐藏或状态缺失时返回 partial/unknown |
| springboot_inspect_beans | Context、别名、正反向及多跳依赖；结合 conditions 和登记源码事实形成有证据的阻塞链 |
| springboot_inspect_config | 默认关闭；启用后按登记属性/前缀投影来源、绑定与有效值，值默认隐藏且始终脱敏 |
| springboot_search_openapi | 操作或 Schema 查询；同文档引用、共享引用、循环和深度处理；不请求远程引用 |
| springboot_verify_mappings | MVC/WebFlux 已报告路由的路径、方法、handler 与 Context；无法读取或非 DispatcherServlet 覆盖时保留不完整状态 |

工具列表按名称字母序固定发布，四项风险注解显式保留。工具发现不读取目标。工具选择、筛选组合及下一步规则见[调用策略](docs/contracts/tool-calling-policy.md)。

## 结果与安全不变量

- 查询先建立完整可见事实和关联，再筛选、稳定排序及分页。maxResults 默认和上限均为 50。
- 领域信封包含 source、data、totalMatched、truncated、coverage、nextAction 和 errors 等 Schema 字段；未知总数使用 null，证据不足使用 partial/unknown。
- 每个工具回包同时提供 structuredContent 和同内容的紧凑 JSON 文本副本；完整 JSON-RPC 工具响应最多 16,384 UTF-8 字节。
- 单次工具总时限 15 秒，每目标两个共享读取槽；排队计入时限。上游响应体最多 8 MiB，响应头最多 32 KiB。
- 只缓存脱敏快照；默认绝对 TTL 60 秒、总预算 32 MiB。续页保持原查询与原快照，进程重启丢失快照。
- 所有外部证据经 SanitizerPipeline 和独立输出安全门；禁止输出原始凭据、异常栈、OpenAPI 自由描述、完整 env/configprops 值树及远端指令。
- 禁止目标写请求、heapdump、原始 logfile、任意业务请求及鉴权/TLS/脱敏/预算绕过。startup 始终 GET。

实现细节见[系统概览](docs/architecture/system-overview.md)、[安全架构](docs/architecture/security-and-sanitization.md)及[归一化架构](docs/architecture/cross-version-normalization.md)。

## 配置与源码事实

CLI 读取 `SPRING_RUNTIME_BASE_URL`、`SPRING_RUNTIME_TARGET_ID`、`SPRING_RUNTIME_TIMEOUT`、`SPRING_RUNTIME_SOURCE_CATALOG` 作为相应参数默认值。Bearer 仅从 `--token-env` 指定的变量读取；令牌值不放入工具参数或配置文件。

配置诊断由 `--config-prefix`、`--config-property`、`--config-profiles` 显式登记，`--config-allow-values` 允许登记范围内经脱敏的值输出。网络读取仍使用固定 `/actuator/env`、`/actuator/configprops`，筛选在本地执行，不能声称减少了上游返回范围。

Source catalog 是操作者登记的 JSON 事实，最多 256 KiB，types/producers 合计最多 1,000 条；CLI 不扫描或执行源码。关联依据及覆盖缺口见[接入指南](docs/source-catalog.md)。

## 验证与兼容范围

默认测试使用合成多版本 fixtures、测试自建回环 HTTP/TLS 服务和官方 SDK 协议检查。离线重放复用处理器；它是一条一次性命令，不是常驻 MCP 服务。

归一化代码处理 Boot 2.7/3.x/4.x 相关结构及 MVC/WebFlux 报告。结构识别、合成测试和固定项目隔离样本分别提供有限证据；完整 Boot/Java/客户端矩阵、Windows/macOS 和生产集群兼容性尚未验证。JAX-RS 业务路由、任意条件消息、运行代理与源码类型的所有组合也不保证完整可见。

真实实例集成必须单独授权，与默认离线检查分开。标准检查、构建及发布门禁见[发布流程](docs/launch/README.md)。wheel 分发工具 Schema、py.typed 和 replay 资源；人类历史库留在 Git，不进入 wheel/sdist。
