# 当前响应归一化与关系分析

归一化处理经过固定 HTTP 门禁的 Actuator/OpenAPI JSON。实际端点和安全边界见[安全架构](security-and-sanitization.md)；字段以 [Schema](../../src/spring_runtime_mcp/schemas/tools-contract.json) 为准。

## 输入与版本证据

ResponseGateReader 接受普通 JSON 及 Actuator v2/v3 媒体类型，构造带 target、snapshot、observation、observedAt 和 endpoint 身份的 ParsedObservation。适配器依据报告结构读取上下文和领域数据；精确 Boot 版本没有可用证据时为 null。在线链路按工具需要读取固定端点，不执行自动能力握手、版本探测或多路径回退。

| 领域 | 当前归一化行为 |
| --- | --- |
| beans | 解析 contexts/beans、类型、scope、aliases 和 dependencies，建立 Context 与 Bean 身份及可见依赖图 |
| conditions | 读取 positiveMatches/negativeMatches，识别有界已知条件消息并归一化 outcome；未知语法保留缺口 |
| mappings | 提取 MVC dispatcher、WebFlux 注解及可识别函数式路由中的路径、方法、handler、Context 和栈 |
| health | 遍历 components/details 等可见组件，区分聚合状态、详情隐藏、不可读状态及树深度限制 |
| flyway/liquibase | 分别读取报告库存及上下文/迁移 Bean 身份，投影版本、changeSet、checksum、顺序和状态 |
| startup | 解析 timeline/events 的事件身份、父节点和持续时间，筛选慢步骤并输出祖先链 |
| env/configprops | 在登记策略内归一化来源、绑定与有效值；配置默认关闭且值默认隐藏 |
| openapi | 识别支持的 OpenAPI 文档结构，投影操作或 Schema 并有界解析同文档引用 |

Boot 2.7/3.x/4.x 相关形状与 MVC/WebFlux 有合成测试和部分隔离样本；精确版本及客户端组合须单独验收。结构可识别不等于完整兼容矩阵通过。

## Bean 图与 Context 可见性

Bean 身份包含 target、Context、canonicalName 和 beanKind。每个 Context 建立 canonicalName/alias 双向索引，同名冲突保持未解析。依赖先在当前 Context 查找，再沿 parentId 逐层查找；子容器同名 Bean 遮蔽祖先，父容器不会反向到子容器解析依赖。

完整可见图及反向索引在过滤和分页前构造，依赖/被依赖方向均可多跳遍历。环、缺失父节点、未暴露依赖、歧义别名和访问预算进入 gaps；达到深度或节点上限时保留可用事实并标记不完整。

Source catalog 仅提供操作者核实的类型继承和生产者事实；运行 Bean 与目录生产者按 Context、名称/别名、类型及 source key 等证据关联。未扫描类型不能用空继承列表表示已扫描，未提供目录不能推断 Bean 不存在。目录格式与限制见[接入指南](../source-catalog.md)。

## 条件与阻塞链

AnyNestedCondition、AllNestedConditions、NoneNestedConditions 以 ANY/ALL/NONE 递归三值结果处理。已报告 outcome、识别出的条件语法、搜索范围及源码生产者关联共同限制归因；冲突、截断和未知实现保持 unknown。

ConditionalOnBean 支持现有可识别类型及严格匹配的单一具名缺失消息。单一 names 选择器的 `did not find any beans named <name>` 仅在后缀与选择器完全一致时识别；复合要求、名称不符和无法唯一解析时不生成确定链。MissingBean 按其相反条件方向处理。

有证据的阻塞路径可沿 `REQUIRED_BEAN_MISSING → SOURCE_FACTORY_NOT_CREATED → PROPERTY_NOT_FOUND/PROPERTY_VALUE_MISMATCH` 传递。跨层关联必须有唯一目录生产者和精确 conditionSources；局部条件已知时，外层仍可能因其他证据缺口保持 partial。运行代理类型与源码声明类型分别保留，不能用虚构类型或工厂关系补齐缺口。

## 路由、健康、迁移与启动

MVC/WebFlux 的注册事实来自 mappings，不调用业务 URL。函数式 predicate 仅解析已支持的正向组合及媒体约束；OR/NOT/未知语法保留缺口。非 DispatcherServlet（如 Jersey）可能覆盖查询路径时，空 dispatcher 结果使用 NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED 和未知总数。

健康总状态与可见子组件分别保留。不可读组件、缺失状态或详情/深度受限时返回 partial；影响筛选计数的缺口令 totalMatched 为 null。固定健康探针的 503 是可解析证据，不代表连接成功即健康。

迁移排序使用引擎报告的安装顺序及稳定身份，缺失字段保持 null/UNKNOWN。Flyway 预期版本比较使用安装顺序中最新的成功且有版本记录；Liquibase 不提供等价标准版本语义，版本预期无法支持时明确报告。未报告的 pending、耗时或失败不能补造，MARK_RAN 只表达引擎报告状态。

启动时间线保留单位、事件、父链和截断证据。父节点缺失、非树关系、深度或节点预算受限时标记 partial；重叠事件耗时不求和为 JVM 总启动时间。采集由目标应用在 run 前配置 BufferingApplicationStartup，指南见[目标配置](../target-app-setup.md)。

## OpenAPI 引用

在线读取固定 `/actuator/openapi`；文档内支持的版本/方言按现有解析器处理。同文档 JSON Pointer 处理 `~0`/`~1` 转义，引用展开默认两阶、最多八阶；共享引用独立投影，使用有界访问与输出预算。

直接和二阶引用均保留可追溯事实。循环、未解析引用、远程引用、方言或层级不可确定时记录 gaps；远程 `$ref` 从不联网读取。PathItem 的非冲突相邻字段可以保留；字段冲突或操作不可读影响完整计数时 totalMatched 为 null。

Schema 中名为 description 的业务属性与原始自由文本说明分别处理；投影保留允许的结构字段，同时始终执行脱敏和输出安全门。

## 漂移与证据分级

漂移只比较调用者明确提供的维度。数组缺省表示不比较，显式空数组表示预期为空；只有 expectedScopeComplete=true 且运行证据完整时才能判断额外运行对象。Bean 图可传播影响，sourceRevision/sourceModifiedAt 是调用者声明。

版本、时间、Context、实例或启动证据不充分时保持 candidate/unknown；不将文件较新直接写成“进程未重启”。配方和错误只由本地安全模板生成，HTTP 状态本身不能确定采集、配置或业务根因。
