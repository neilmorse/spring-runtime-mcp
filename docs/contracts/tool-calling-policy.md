# 工具调用策略与当前错误契约

公开契约为版本 2，协议目标为 MCP 2026-07-28，宿主也支持 SDK legacy 模式。八个 Tool 定义位于 [tools-contract.json](../../src/spring_runtime_mcp/schemas/tools-contract.json)，由 tools/list 发布；包级 contractVersion/protocolVersion 不作为 Tool 字段发送。

## 发现、参数与工具选择

八工具按 name 的 ASCII 字母序固定发布，inputSchema/outputSchema 使用 JSON Schema 2020-12，引用在各自 `$defs` 内闭合。四项风险注解为 readOnlyHint=true、destructiveHint=false、idempotentHint=true、openWorldHint=false；实际权限由确定性守卫执行。

Schema 的 default 由服务端参数规范化显式应用。工具参数 JSON 最多 16 KiB；非法字段、类型、选择器或超限返回 INVALID_ARGUMENT，不读取目标。pattern 是区分大小写的有界 glob，支持 `*`、`?`，最多 128 字符；其余按字面匹配，多个筛选条件按 AND，packagePrefix 按包段边界匹配。

| 诊断入口 | 工具与当前调用行为 |
| --- | --- |
| 慢启动 | springboot_analyze_startup：读取 GET startup，按耗时降序及稳定身份排序；保留父链和单位缺口 |
| 迁移异常 | springboot_check_migrations：engine=auto 时分别读取 Flyway/Liquibase；按异常状态优先及引擎报告顺序排序 |
| 源码与运行态比较 | springboot_detect_drift：只比较显式预期维度，额外运行对象的判定需要完整预期与运行覆盖 |
| 健康异常 | springboot_diagnose_health：默认隐藏健康子节点和详情，componentPath 为本地树查询，探针只访问固定健康组 |
| Bean 或条件异常 | springboot_inspect_beans：至少给名称、类型或包筛选；根据分析需要读取 beans/conditions，缺条件仍保留可用 Bean 证据 |
| 配置来源 | springboot_inspect_config：至少给 prefix/propertyKeyPattern，includeValues=false；只投影操作者登记范围 |
| OpenAPI | springboot_search_openapi：schemaName 与操作查询互斥，httpMethod 不可单独查询；固定 GET `/actuator/openapi`，同文档引用默认两阶、最多八阶 |
| 路由注册 | springboot_verify_mappings：至少给路径、方法或 Controller 筛选；只读 mappings，不调用业务 URL |

精确选择器、枚举、深度与输出字段应读取当前工具对应 Schema，不从示例推导新参数。

## 结果、分页与证据

工具先在完整可见事实中建立依赖关系和反向索引，再筛选、计数、稳定排序及分页。maxResults 默认/上限为 50。记录数、字节、深度或分析预算达到上限时保留 truncated、truncationReasons、coverage 和 nextAction；完整匹配总数不可确认时 totalMatched 为 null。

续页重发原工具、目标和同一规范化查询参数，只增加 cursor。快照为脱敏共享编码记录，游标记录 offset，正常续页只处理当前页；默认 60 秒绝对 TTL、32 MiB 总预算，续页不延长期限。策略戳变化后复验整份快照，发现不安全内容则移除相关句柄。

nextAction.kind 指示 page/refine/remediate/done 等下一步；page 使用 nextCursor。filterSuggestions 仅含该工具允许的安全参数，客户端合并后重新验证。CURSOR_EXPIRED 时重新发起不含 cursor 的查询，不能把新结果当成原快照续页。

- Bean 别名、父链、同名遮蔽、嵌套条件和传递阻塞分析遵循[归一化架构](../architecture/cross-version-normalization.md)。源码目录未覆盖不等于 Bean 不存在。
- 健康组件不可读或状态缺失时，保留可用组件和 gaps；影响过滤计数时 totalMatched 为 null。
- mappings 的非 DispatcherServlet 覆盖或未知函数 predicate 保留 partial/unknown，不能把空结果确认为未注册。
- 迁移缺失字段使用 null/UNKNOWN；pending、MISSING_FAILED 和耗时依报告证据表达。Liquibase 版本预期不替代 changeSet 身份。
- drift 的预期数组缺省表示不比较，显式空数组表示预期为空；Bean/路由/迁移版本预期合计最多 100 个实体。sourceRevision/sourceModifiedAt 为调用者声明，证据不足时保持 candidate/unknown。

## 配置读取

env/configprops 默认关闭。操作者使用 CLI 登记属性、前缀或 profiles 权限；工具查询与策略取交集。连接器只读取固定 `/actuator/env` 和 `/actuator/configprops`，本地过滤不会减少上游响应大小，也不提供 `/env/{property}` 等动态路径。

includeValues 默认 false；显式允许值时仍执行登记范围、字段投影和双层脱敏。值、输入值及 origin 共享敏感上下文，秘密内容统一遮蔽或省略。activeProfiles 使用实际报告，不从属性字符串猜测；来源不可安全表示时为 null/unknown。安全细节见[安全架构](../architecture/security-and-sanitization.md)。

## 错误与本地配方

outputSchema 验证 structuredContent 中的领域信封。DiagnosticError 的 code、endpointId、httpStatus、retryable、message、remediation 由本地固定逻辑产生；配方包含 recipeId、action、configKeys、steps、requiresApproval、retryAfterMs，不回显原异常或上游指令。

| 当前观察 | 实际代码与处理 |
| --- | --- |
| 参数不符合契约 | INVALID_ARGUMENT；refineQuery，不联网 |
| 未登记目标/未启用能力 | TARGET_NOT_REGISTERED / CAPABILITY_DISABLED |
| 401/403 | ENDPOINT_UNAUTHORIZED，保留 HTTP 状态；reviewAuthorization |
| 3xx | REDIRECT_BLOCKED，不跟随重定向；reviewAuthorization |
| 普通端点 404 | ENDPOINT_NOT_EXPOSED；reviewExposure |
| startup 404 | STARTUP_DATA_UNAVAILABLE；configureStartup，但单凭状态不能确认采集器缺失 |
| 其他拒绝状态（含 405） | ENDPOINT_UNAVAILABLE；startup 5xx 提供 configureStartup，其他使用一般端点建议 |
| 不支持媒体/编码、响应不完整 | UNEXPECTED_CONTENT_TYPE / UNSUPPORTED_CONTENT_ENCODING / INCOMPLETE_RESPONSE |
| 超时/连接失败 | TARGET_TIMEOUT / TARGET_CONNECTION_REFUSED / TARGET_CONNECTION_FAILED |
| 输出或缓存不安全、预算超限 | UNSAFE_OUTPUT / SANITIZATION_FAILED / RESPONSE_TOO_LARGE 等固定码，停止该分支 |
| 游标失效/查询变化 | CURSOR_EXPIRED / CURSOR_QUERY_MISMATCH；重建查询或恢复原参数 |

`failed()` 的实际状态：INVALID_ARGUMENT 为 invalid，ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED 为 denied，其余失败为 unavailable；data 和 totalMatched 为 null，coverage.state=unavailable，errors 至少一项。ok/partial 的有效诊断 isError=false，包括健康 DOWN、迁移失败及有证据的漂移。

实现中的 retryable 固定 false、retryAfterMs 为 null；INVALID_ARGUMENT 配方 requiresApproval=false，其他错误配方为 true。执行者仍应核对已有同范围授权，配方标志本身不会撤销或扩大授权。目标配置、暴露、凭据权限和重启遵循项目权限规则。

## 帧与调用预算

结果同时含 structuredContent 和唯一 TextContent，text 为同一脱敏对象的紧凑 JSON；完整结果使用 resultType=complete。完整 JSON-RPC 工具响应连同 request id、SDK 元数据及两份内容最多 16,384 UTF-8 字节，宿主与实际发送出口复核。静态 tools/list 的 Schema 不按该工具回包上限裁剪。

服务端强制单工具 15 秒总时限及每目标两个读取槽。建议 Agent 每轮最多 4 次调用、累计结果最多 64 KiB，达到后总结并收窄；这一跨调用策略由调用者遵守，不是宿主会话计数守卫。授权、网络、安全或证据阻塞时停止相应分支，完成其余可独立诊断。

## 离线契约检查

```bash
uv run --no-sync python scripts/validate_tool_contract.py
```

在锁定开发环境中运行，使用合成内存数据验证排序、风险注解、独立 Schema、局部引用和正反例；不连接 Spring Boot。完整验证分级见[发布流程](../launch/README.md)。
