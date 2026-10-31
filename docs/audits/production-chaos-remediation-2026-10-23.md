# 生产故障矩阵问题：调研、修复与复验

日期：2026-10-23。用户明确要求调研并修复上一轮的 PC-01、PC-02、LS-01，沿用缓存公开项目的隔离实例、数据库和重启授权。保留此前未提交代码和历史失败；没有变更八工具公开 Schema、Python 运行依赖、目标白名单、方法守卫、绝对 TTL 或最终回包预算。

## 调研与行为变化

### PC-01：健康详情的指令文本通道

根因有三层：健康详情被转换为 name/value 描述符后丢失说明字段上下文；脱敏器只传播凭据敏感名称；独立出口只检查字典键 instructions 等，没有识别描述符中的同名字符串。进一步回归还发现 error 中不含空格的普通单词可被误当成异常类名。

修复在字段上下文而不是指令 canary 字面上实施：对 instructions、description、comments、stackTrace、message、error、exception、system、role 等名称做大小写、NFKC、分隔符归一化；关联 value、inputs、bindingValue、effectiveValue 和 origin 受同一 taint 约束。名称本身无法安全投影时，关联值也必须移除，覆盖百分号/反斜杠编码和非法标签。独立出口拒绝尚未脱敏的等价记录，不能依赖生产者必然调用脱敏器。

健康错误只保留全限定 Java 类名形态的 errorType；不能识别则为 null，异常消息不会以普通标量恢复。数据库类型、数值健康指标和合法异常类名仍保留。OpenAPI 中同名业务 Schema 属性保持 Schema 对象语义，不把 properties.instructions/description/role 当作运行态指令描述符。

位置：[描述符脱敏](../../src/spring_runtime_mcp/policy/sanitization.py)、[独立出口](../../src/spring_runtime_mcp/policy/output_guard.py)、[健康错误类型](../../src/spring_runtime_mcp/adapters/health.py)。

### LS-01：本地随机游标被后续安全门拒绝

原先 SnapshotStore.put 只检查随机句柄唯一性；编码内容识别可能把其解码结果判为高危，直到最终出口才拒绝。修复统一普通缓存和分页句柄的生成：登记前使用当前 SanitizerPipeline 与独立出口检查候选，拒绝碰撞及不安全候选，最多尝试 16 次。

连续拒绝时返回既有 UNSAFE_OUTPUT，不放行候选、不无限循环，也不写入无法交付的缓存条目或为新句柄提前淘汰有效缓存。凭据变体识别、随机源和最终出口守卫保留。确定性回归覆盖“拒绝首个候选后成功”“碰撞后成功”“持续拒绝/碰撞有界退出”“已登记 opaque 凭据也不能成为句柄”。

位置：[SnapshotStore](../../src/spring_runtime_mcp/snapshots.py)。

### PC-02：较大快照连续分页无法在期限内完成

原始 Bean _page 每次复制整个剩余结果；缩小回包时还重复复制，再对整个未发送尾部脱敏、编码并创建另一份缓存。通用 finalize 也有相同结构。1255 个可见 Bean 在本机两次分别读到 390/370 个便超过原始 60 秒期限。过期守卫工作正确，修复没有延长 TTL。

现在首次只缓存一份安全快照：元数据与每条记录编码为独立不可变字节；游标只保存共享快照和偏移。每次只解码/复制请求上限内的记录，16 KiB 预算进一步裁剪后按实际已发送数量推进偏移。完整依赖图、过滤、计数、排序仍发生在分页之前，Bean/条件/OpenAPI 算法未改。当前页仍脱敏并通过独立出口检查，没有把“曾检查过”当作免检权。

缓存按快照唯一存储计费，并计入记录和每句柄的保守元数据费用，继续受 32 MiB/LRU 限制。引用计数覆盖最后句柄被淘汰、旧句柄重放及过期清理。每条续页继承同一观察的绝对期限。

为了保留凭据更新后的安全性，缓存只记不含明文凭据的策略戳。替换 SanitizerPipeline 或同一实例的凭据变体发生变化时，必须复验整份快照，包括尚未请求及已发送的记录；一旦发现新敏感值，删除该快照的全部句柄。回归同时验证普通缓存与共享缓存的隔离、绑定、容量和清理。

位置：[共享缓存](../../src/spring_runtime_mcp/snapshots.py)、[Bean 分页](../../src/spring_runtime_mcp/tools/inspect_beans.py)、[通用分页](../../src/spring_runtime_mcp/tools/support.py)。

## 失败回归与离线证据

新增 [test_production_chaos_repairs.py](../../tests/unit/test_production_chaos_repairs.py)。首轮选取的 16 项回归在修复前全部失败，涵盖字段透传、错误类型误识别、不安全句柄登记和整尾分页工作。之后补齐持续拒绝/碰撞、共享存储、不可变页、原始 TTL、查询绑定、凭据刷新删除整快照、完整可见遍历及编码标签变体，共 28 项新增回归；没有删除或弱化现有安全测试。

[PC-01/PC-02 探针](production-chaos-remediation-probe-2026-10-23.json)：最终回包中指令 canary 不再出现、登记密码仍移除；合成分页的脱敏输入记录数从 1255/20/1235/20/1215 变为 1255/20/20，只有一次源读取；冻结时钟超过原始 60 秒仍返回 CURSOR_EXPIRED。

[LS-01 探针](large-project-cursor-remediation-2026-10-23.json)：固定不安全候选在登记前被拒绝，16 次有界退出，缓存未写入。随机抽样只是安全门行为的辅助记录，不当作工具失败率或统计保证，也没有为得到特定计数而重抽样。

两个探针增加 --expect-repaired 模式，以修复后应满足的条件决定退出码；默认仍保留历史缺陷复现语义。旧报告和原失败 JSON 不覆盖。

## 真实项目复验

使用 [固定源码与外部配置](../../examples/production-chaos/projects.json) 和既有编译产物，不下载新项目、不替换上游 Boot/BOM。ThingsBoard 仍使用临时可选 Actuator 与独立 PostgreSQL；DolphinScheduler 仍是开发 Standalone，不改称生产集群。所有报告仅保留聚合元数据，不保存原始目标响应、异常消息、堆栈或真实令牌。

最终源码下三项共 **425 次真实 MCP 调用全部满足预期断言**；修复过程较早的一轮也通过，独立归档，不与最终调用数相加或覆盖旧失败。

| 项目 | 调用数 | 首次连续可见分页 | 所有调用中位数 / p95 ms | 最大完整回包字节 |
| --- | ---: | --- | --- | ---: |
| shenyu | 118 | 692 / 69 页，穷尽 | 58.458 / 537.052 | 14916 |
| thingsboard | 176 | 1255 / 125 页，穷尽 | 57.604 / 732.708 | 16260 |
| dolphinscheduler | 131 | 820 / 82 页，穷尽 | 55.694 / 514.038 | 13672 |

ThingsBoard 两条旧链分别 390/370 个后过期；最终首次链穷尽全部 1255 个可见 Bean，125 次分页 SDK 调用耗时累计 9745.012 ms。这个累计数不含调用间验证和其他调度开销，不是整个遍历墙钟或生产性能基准。三项基线实际仍为 699/1280/826 个 Bean，注入后为 1699/2280/1826，包含原先声明的额外运维组件。

完整安全摘要：[ShenYu](../../examples/production-chaos/results/shenyu-remediation.json)、[ThingsBoard](../../examples/production-chaos/results/thingsboard-remediation.json)、[DolphinScheduler](../../examples/production-chaos/results/dolphinscheduler-remediation.json)；[聚合及源码/报告哈希](production-chaos-remediation-2026-10-23.json)。

三项都继续执行：匿名 401/低权限 403、原生连接池耗尽/释放、三类自编启动失败及失败期间 MCP unavailable、额外 1000 个实际 Bean 的末端查询、坏响应逐项拒绝后恢复、上下文异常/引用/时间的 partial、取消后同宿主恢复。ThingsBoard 的真实 PostgreSQL 暂停后 DOWN、恢复后 UP；三项 redirect/remote-ref 陷阱计数均为零。独立 canary 断言检查了原生额外健康组件及 HTTP 503 合成健康，均未透传指令。

上述通过包含对预期故障错误码和恢复的验证，不意味着没有错误响应。原生未暴露/不可读取入口仍按本轮实际 200 错误 JSON、401 或 404 处理，不声称新增原生 OpenAPI 正向兼容性。所有原生来源不足和图预算缺口继续 partial，totalMatched 仍可能为 null。

## 验证与限制

- 最终全量：`uv run --no-sync python -m pytest -q`，**909 passed，32.11 秒**。
- 类型：`uv run --no-sync python -m mypy src/spring_runtime_mcp`，53 个源文件通过。
- Ruff check / format：109 个 Python 文件通过。
- 契约：8 组独立工具 Schema、144+ 合成断言通过。
- 两个独立探针以 `--expect-repaired` 验证修复条件，历史输出保持不动。
- 文档链接、完整报告哈希、16 KiB 回包预算、零陷阱读取及自有容器/网络清理另行核查。

没有打包或资源布局修改，因此本轮未重新构建本项目 wheel；没有提交、推送、发布或部署。共享缓存策略戳的最终刷新与编码标签加固有独立回归，真实矩阵最终选取使用同一最终源码。所有自有容器、网络、MCP 子进程已停止，源码缓存保留；未处理其他用户容器。

这次关闭的是已确定的三个问题及其回归场景。结构化标识符仍是目标可选择的数据，不能据此承诺任何语义的提示注入都已消除，也不证明下游 Agent 的其他工具权限安全。绝对 60 秒 TTL 和 32 MiB 上限仍可能限制更大或更慢环境，应收窄查询或明确建立新快照，不能拼接新旧观察。未验证生产分布式集群、真实业务流量、长期泄漏、UI、远程 TLS 或完整 Spring Boot 版本矩阵。
