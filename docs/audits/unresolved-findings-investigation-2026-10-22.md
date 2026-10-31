# 遗留问题原因调查 — 2026-10-22

状态更新：下文保留修复前的调查快照。后续[闭环修复](remaining-findings-remediation-2026-10-22.md)
已处理 R1–R5，并完成带本地 springdoc 补丁的 JHipster 独立管理端口验收；原失败记录不变。

本轮研究“为什么尚未修复”，不修改诊断生产算法、公开工具 Schema 或第三方依赖。
保留前轮所有补丁与失败记录；新增离线探针、无网络 Java 最小实验和已授权临时 JHipster 实例的定向实验。

## 结论与上轮范围遗漏

遗留问题分成两类：**本项目五项实现缺口**，以及 **JHipster/springdoc 独立管理端口组合的启动故障**。
五项缺口全部在当前工作树复现。它们没有被技术或授权条件阻塞；上轮主动把补丁范围收窄到
新出现的两个 OpenAPI 缺陷，未完成已知审查清单的闭环。不能把“本轮范围之外”解释为无法修复。

JHipster 上轮使用同端口配置获得可用诊断，但没有修复原独立端口的依赖初始化行为。
本轮进一步确认：**启动生命周期和文档地址是两个需要分别解决的问题**。

## 五项当前缺口

复现脚本：[probe_unresolved_review_findings.py](../../scripts/probe_unresolved_review_findings.py)。
全部输入为合成 JSON，结果保存为[有界事实摘要](unresolved-review-probe-2026-10-22.json)。
脚本退出 **1** 表示仍有缺陷复现，不能计作测试通过。

| 编号 | 实际复现 | 代码根因 | 修复方向 |
| --- | --- | --- | --- |
| R1：PathItem 相邻操作丢失 | 引用对象声明 GET，当前 PathItem 另声明 POST；只返回 GET，仍是 ok | `adapters/openapi.py:365` 将整个当前对象替换为引用目标，忽略相邻字段；通用包装解析器也用于 PathItem | 专门处理 PathItem 的非冲突字段；相同字段冲突保持 partial，不能猜覆盖顺序；不要把这一规则套到 Parameter/Response Reference Object |
| R2：非法启动时间被当成完整比较 | startup 的 startTime 是不可解析字符串，drift 返回 ok / complete / totalMatched=0 | `tools/detect_drift.py:91` 只检查 str；`:99` 将解析失败折叠成 False；`:275` 仅为 None 标缺口 | 让时间解析返回有效时间或 unknown；缺失、非法、无时区都进入已有 STARTUP_TIMING_UNOBSERVED，不能把不可比较当成“未发现漂移” |
| R3：RFC3339 判断过宽且漏接合法值 | 基本日期、周日期、秒级时区偏移被输入/输出接受；小写 z、合法闰秒被拒绝 | `contracts/definitions.py:216` 与 `server.py:55` 都用 datetime.fromisoformat 代替 RFC3339 语法；startup adapter 也另有同类解析函数 | 统一受限时间解析，先验证 RFC3339 形状，再校验日历/偏移；明确小写 t/z、闰秒和比较规则；保留独立测试 oracle，不能把实现复制进测试 |
| R4：嵌套 Schema 丢失根方言 | 文档默认未知，Root 显式选择已支持方言；其普通 child 却被标为 unsupported / partial | `adapters/openapi.py:139` 每次递归只回退到文档默认，没有携带当前 Schema resource 的有效方言 | 在线内子 Schema 递归传递有效方言；跨引用时结合目标所在 resource 判断，不能盲目继承调用方；缓存不能混淆方言作用域 |
| R5：不可读路径仍报告确定零 | PathItem 指向缺失本地对象；status=partial、gaps 非空，但 totalMatched=0 | 归一化器跳过无法读取路径；`tools/search_openapi.py:45` 无条件使用 len(items)，未携带枚举完整性 | 区分“操作未能枚举”和“已找到操作的 Schema 展开不完整”；前者 totalMatched=null，后者仍可保留已证明的操作计数 |

R1 的修复不能简单合并所有对象：OpenAPI 对同一 PathItem 字段同时存在于本地和引用目标的
情况明确未定义覆盖行为。见 [OpenAPI Path Item](https://spec.openapis.org/oas/v3.1.1.html#path-item-object)。
R4 需要遵守 Schema resource 根的方言覆盖作用域，见
[OpenAPI 方言规则](https://spec.openapis.org/oas/v3.1.1.html#specifying-schema-dialects)和
[JSON Schema Core 8.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-8.1.1)。
R3 的语法依据是 [RFC3339 5.6](https://www.rfc-editor.org/rfc/rfc3339.txt)。

这五项均可在现有输出契约下修复，无需新增运行依赖、开放任意 URL 或弱化安全校验。
建议先处理 R2/R3/R5 的“缺证据却给确定结论”，再处理 R1/R4 的引用语义和方言作用域。

## 为什么现有测试没有拦住

- PathItem 回归只覆盖“只有引用”的路径，没有引用旁的独立操作。
- 启动时间回归覆盖 analyze_startup 的非法事件时间和 drift 的端点缺失，没有覆盖 drift 收到非法 timeline.startTime。
- 独立 conformance 时间 checker 有更严格的语法；常规 fixture 是规范时间，没有针对运行时 checker 做基本日期/周日期/偏移秒等差异输入。
- 方言覆盖测试的 Root 是标量，没有 Root 的内联子 Schema。
- 未读路径虽然有 partial 标记，但尚无“partial 不能同时表示已证明零操作”的计数断言。

因此，前轮 837 passed 证明已有断言通过，不能证明这五个分支正确。
这些是当前测试输入缺口和未闭环事项；本轮探针保留为显式失败，未修改默认 pytest 来制造绿灯。

## JHipster：启动失败的因果链

固定来源仍是 JHipster commit `6b000b5d23a36c45e01472471b84a44fa2464044`，原生 Boot **4.1.1**、
Spring Framework **7.0.9**、JHipster framework **9.4.0**、springdoc **3.1.1**、Java **21**。

1. 原生配置开启 show-actuator，独立管理端口使 springdoc 的后处理器 3 生效。
2. 该静态工厂方法直接依赖 List<GroupedOpenApi>，容器必须在 BeanFactory 后处理阶段创建分组实例。
3. 创建分组需要 JHipster 分组配置类；它只有带 JHipsterProperties 参数的构造器。
4. 此时用于正常构造器发现的 BeanPostProcessor 尚未进入通常的注册阶段，实例化最终走到无参构造路径，产生 NoSuchMethodException。

依据是已安装字节码、原始有界错误因果类型、
[同版本 springdoc 工厂方法](https://github.com/springdoc/springdoc-openapi/blob/v3.1.1/springdoc-openapi-starter-common/src/main/java/org/springdoc/core/configuration/SpringDocConfiguration.java#L535)
和 [Spring 对 BeanFactoryPostProcessor 过早实例化的说明](https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html)。
“后处理器直接索取 Bean 实例”这一因果判断现已得到下面两个实验支持。

### 无网络的最小生命周期实验

[EarlyGroupedBeanProbe.java](../../examples/project-matrix/EarlyGroupedBeanProbe.java)
只启动 AnnotationConfigApplicationContext，不开端口、不读取目标、不使用凭据；
复用缓存的 Spring/springdoc 类。合成配置类只有依赖构造器，返回一个 GroupedOpenApi。

| 对照 | 结果 |
| --- | --- |
| 普通配置正常创建分组 | 成功，1 个分组 |
| BFPP 工厂直接索取 List<GroupedOpenApi> | 失败；UnsatisfiedDependencyException → BeanCreationException → BeanInstantiationException → NoSuchMethodException |
| BFPP 仅通过 getBeanNamesForType(..., allowEagerInit=false) 检查定义 | 成功，1 个分组 |

[三次实验摘要](../../examples/project-matrix/early-grouped-bean-verification.json)
只保存退出码、成功标记和异常类名。这证明按定义探测的方向可行，**尚未等价于完整第三方库补丁已通过验收**。
完整补丁需要同时调整工厂方法和处理器对分组的依赖，并覆盖无分组、显式分组、属性分组及不同管理端口模式。
仅把列表改成 lazy/provider、随后仍在同一 BFPP 阶段索取实例，不能解决过早创建本身。

### 真实独立端口对照：启动后还会遇到文档路径问题

使用 [probe_jhipster_separate_port.py](../../scripts/probe_jhipster_separate_port.py)，
仅在一次性外部配置追加 show-actuator=false，并将 dev 组限定为 api-docs，避免上游样例秘密配置。
保留原生 API-docs、独立随机回环管理端口、内存 H2、JWT 管理员规则和前轮命名空间补丁。
没有替换 jar、业务实现、POM 或诊断端点白名单。

实际结果见[六次定向读取摘要](../../examples/project-matrix/jhipster-separate-port-investigation.json)：

- 应用成功启动，未出现原异常；管理员可找到 userService。
- multipleOpenApiActuatorResource 和 openAPIDefaultGroupedOpenAPI 两个 Bean 均实际存在，排除了“简单关闭全部 OpenAPI”这一解释。
- 固定 GET /actuator/openapi 返回 HTTP 404 / ENDPOINT_NOT_EXPOSED。
- 两种路由过滤未返回记录；这不能证明其他管理路由不存在，也不作为分组路径可访问的证据。

springdoc 的[分组管理端口资源源码](https://github.com/springdoc/springdoc-openapi/blob/v3.1.1/springdoc-openapi-starter-webmvc-api/src/main/java/org/springdoc/webmvc/api/MultipleOpenApiActuatorResource.java#L84)
将 JSON 映射在 /{group}；当前连接器只登记 /actuator/openapi。
结合实际分组资源 Bean 和根路径 404，可以判断固定根路径与分组文档之间仍有集成缺口。
本轮没有请求任何分组/自定义 HTTP 地址，因此**不宣称分组文档已经真实验收通过**。

这解释了上轮为什么同端口方案可以通过，却不能算原配置修复：它同时避开了过早实例化触发条件，
并通过受信配置提供了连接器可读取的固定文档地址。要完成原配置，需要分别解决：
第三方 BFPP 仅检查定义，以及提供保持 JWT 管理员保护的固定文档入口/受信候选登记。
不能只修启动后便宣布 OpenAPI 全链路恢复，也不能开放任意地址透传。

## 本轮检查和边界

- 定向 pytest：**64 passed，1.36 秒**（综合、交付审计和 OpenAPI 投影回归）；没有重复全量测试。
- mypy：52 个源码文件通过；Ruff check 和 format：100 个文件通过。
- 离线遗留探针：退出 1，五项 reproduced=true，按失败保留。
- 三个无网络 Java 对照：两个成功、一个预期失败；真实 JHipster 对照成功启动，但固定 OpenAPI 入口仍失败。
- 所有工具结果均经过契约、安全门和完整 16,384 字节响应检查；真实进程在 finally 停止；无原始响应、目标日志、异常栈或 JWT 持久化。

本轮没有实施上述修复、提交、发布、新增运行依赖或改变连接器的登记范围。
