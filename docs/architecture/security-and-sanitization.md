# 当前安全架构与脱敏边界

本项目只读诊断登记的回环 Spring Boot 实例。网络边界由 [actuator_http.py](../../src/spring_runtime_mcp/transport/actuator_http.py) 实现，能力门禁由 [response_gate.py](../../src/spring_runtime_mcp/transport/response_gate.py) 实现，工具参数与输出由 [Schema](../../src/spring_runtime_mcp/schemas/tools-contract.json) 约束。

## 目标、连接与凭据

CLI 登记单个 origin/target。origin 允许 http/https、host 和 port，拒绝凭据、路径、query、fragment、控制字符及非规范危险地址。每次连接解析 DNS 后先验证全组地址均为回环，再使用数字 IP 建连并核对实际 peer；IPv4 映射等地址按现有校验处理，不能绕过回环限制。

连接器使用标准库 `http.client`，通过工作线程执行阻塞 I/O；不读取环境代理，不跟随重定向。HTTPS 使用默认验证上下文，保持证书验证和原 host 的 TLS 名称验证。Basic、任意 headers、远程地址与自定义基路径不提供入口。

`--token-env` 只登记环境变量名称；生产代码仅在 CLI 读取值，随后绑定该连接器和 SanitizerPipeline 的已知秘密集合。请求只向已登记 origin 的固定端点发送该 Bearer。凭据不进入日志、错误信息、工具定义或原始响应缓存。

## 固定端点与只读门禁

ResponseGateReader 先验证登记目标和启用能力，再固定调用 GET、`follow_redirects=False`。连接器独立强制 GET；其他方法及跟随重定向请求均拒绝。

| 逻辑端点 | 固定路径 |
| --- | --- |
| beans、conditions、mappings | `/actuator/beans`、`/actuator/conditions`、`/actuator/mappings` |
| health | `/actuator/health` |
| health-liveness、health-readiness | `/actuator/health/liveness`、`/actuator/health/readiness` |
| flyway、liquibase、startup | `/actuator/flyway`、`/actuator/liquibase`、`/actuator/startup` |
| openapi | `/actuator/openapi` |
| env、configprops | `/actuator/env`、`/actuator/configprops`；默认关闭 |

路径来自连接器内固定表，不拼接工具参数。禁止 heapdump、原始 logfile、目标写方法与业务端点调用；startup POST 会排空缓冲区，始终禁止。404、鉴权失败和重定向不触发其他路径或匿名重试。

## 响应、时限与取消

- HTTP 状态及 Content-Type 在正文读取前检查；重定向、401/403 和不支持的媒体类型直接拒绝。健康系列 503 允许读取为健康证据。
- 接受 `application/json` 和 Actuator v2/v3 JSON 媒体类型；Accept 固定为 `application/json`。响应表示来自媒体类型，不据此推断精确 Boot 版本。
- 响应头累计最多 32 KiB；正文最多 8 MiB。支持无编码、identity 和单层 gzip，压缩前后分别限额；其它编码拒绝。
- Content-Length 未收满、畸形 gzip、重复 JSON 键、非有限数字及有界 JSON 深度/节点超限均显式失败，不回显原响应。
- 多地址连接尝试共享 2 秒建连预算。Reader 默认 5 秒，Services 读取等待最多 5 秒并受工具 15 秒总时限约束；等待每目标两个读取槽也计时。
- 超时或取消时中止连接，短暂等待工作线程清理后重抛。系统 DNS 调用不能强制终止，不宣称所有底层线程在工具超时瞬间停止。

## 配置读取与两层脱敏

env/configprops 需要操作者显式登记读取策略。网络仍读取固定完整端点，在上游预算内本地投影；登记范围限制可见字段，不限制应用实际生成的响应大小。查询与登记属性/前缀取交集，profiles 读取单独登记。

[SanitizerPipeline](../../src/spring_runtime_mcp/policy/sanitization.py) 负责字段白名单、敏感键和值、描述符上下文传播、连接串、origin、已知秘密及编码/嵌入值处理；敏感值使用 `[REDACTED_BY_MCP]` 或省略。配置值默认隐藏；显式 includeValues 也只能输出登记范围内允许的脱敏值。输入值、绑定值及 origin 的关联敏感性一起传播。

原始 env/configprops 树、健康异常文本、条件消息和 OpenAPI descriptions 不出站。健康只保留批准的结构化字段，origin 只保留可安全表示的来源标识及位置；证据不可用使用 null、Fact 状态或 gaps。redactions 使用安全输出字段/索引，不包含原始秘密键或秘密摘要。

独立 [output_guard](../../src/spring_runtime_mcp/policy/output_guard.py) 检查序列化与缓存出口。快照仅存脱敏数据，策略戳不保存明文凭据；策略变化后复验整个快照，失败则删除相关游标。该机制降低已识别格式的泄露和指令透传风险，不构成任意语义提示注入免疫。

## 协议出口与失败处理

STDIO stdout 只承载 JSON-RPC，安全日志与 CLI 错误写 stderr。宿主验证工具输入、输出与 RFC3339 时间；非法参数不联网。安全错误转换为固定本地消息，禁止异常 repr、堆栈、远端建议或原始响应出站。

每个工具结果包含 structuredContent 与同内容的文本副本；完整 JSON-RPC 响应最多 16,384 UTF-8 字节。工具分页、宿主结果构造与 SDK 实际发送层分别执行预算检查；安全检查失败不会降级为原文输出。静态 tools/list 不受工具结果 16 KiB 上限裁剪。

默认测试与合成安全回归见 [tests/security](../../tests/security/README.md)，检查命令见[发布流程](../launch/README.md)。自建回环 TLS 测试与固定项目样本不代表完整真实 TLS/SNI、平台或客户端矩阵通过。
