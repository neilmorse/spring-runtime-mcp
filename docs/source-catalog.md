# Bean 源码目录接入与证据边界

Context ID 使用运行报告中的精确文本身份；`shop-product` 等连字符名称可以登记。

先按[首次接入指南](first-query.md)完成基础查询；source catalog 是按需增强，不是首次接入前提。

`--source-catalog` 接受操作者整理的 JSON 事实，不扫描、执行或下载源码。
可使用仓库内的[受限静态事实生成器](source-facts-generation.md)处理显式登记的 Java 文件，或从[演示目录](../examples/spring-boot-demo/source-catalog.json)按已核实源码整理最小子集。生成器只处理有限 AST 子集，不是完整 Spring 扫描器；生成结果仍须操作者审核。
目录由 [CLI](../src/spring_runtime_mcp/cli.py) 在启动时加载，使用[现有加载器](../src/spring_runtime_mcp/adapters/source_catalog.py)校验；不属于工具调用参数。

```bash
uv run --no-sync python -m spring_runtime_mcp.cli \
  --base-url http://127.0.0.1:18081 --target-id local \
  --token-env SHOP_ACTUATOR_TOKEN --source-catalog /abs/path/source-catalog.json
```

凭据由已登记环境变量提供，不写入目录。目录 `targetId` 必须与 `--target-id` 一致；应用端仍需独立配置获权的 beans/conditions 读取。

## 真实字段与关联

顶层仅有 `targetId`、可选 `sourceRevision`、`types`、`producers`。文件最多 262,144 字节，types 与 producers 合计最多 1,000 条。
每个 type 必须包含 `name`、`directSupertypes`。每个 producer 必须包含以下全部字段：

| 字段 | 登记依据 |
| --- | --- |
| `contextId` | beans/conditions 实际报告的 Context ID，逐字匹配；`shop-product` 与 `shop_product` 不等价。允许 1–256 字符文本，拒绝 C0（U+0000–U+001F）与 DEL（U+007F），不按 Java 类型名校验。 |
| `beanName`、`aliases` | 源码中可核实的 Bean 名称与别名；不能从类名猜测未核实的注册名称。 |
| `declaredType`、`implementationType` | 源码声明类型与已知实现；实现未知用 null。运行代理类型不等同于源码实现类型。 |
| `configurationClass`、`factoryMethod` | 实际配置类/工厂方法；非工厂生产者的 factoryMethod 为 null。 |
| `conditionSources` | 与 conditions 中 source key 精确对应的数组；不从 Bean 名称拼接。嵌套类的二进制类型名可能含 `$`，条件 source key 可能使用 `.`，须分别核实。 |
| `sourceFile`、`sourceLine` | 相对获权源码快照的文件路径与正整数行号；禁止绝对路径、上级路径、反斜杠及 C0 控制字符。 |

除 contextId 外的符号字段仍使用现有有界 Java 符号校验。目录不能添加 `complete`、依赖边或自定义条件消息等字段。
`sourceRevision` 是操作者声明，不证明运行实例来自该版本；文件/行号也不会由服务器再次读取验证，应在仓库外保留源码摘要与目录覆盖说明。

只登记已核实的直接父类型。没有扫描某类型时应省略该 type，不能用 `directSupertypes: []` 代替“不知道”。
没有全局扫描完整性字段意味着不能借目录宣称整个应用完整；目录未覆盖的类型、生产者和条件须继续保留 unknown/partial。

## 判断接入是否有价值

在同一实例上重复同一查询，对照可见事实与缺口，而非只数 partial：

- 对已存在 Bean，只有 Context、名称/别名与实际类型均满足现有匹配规则时，才新增 `producer`，证据级别为 `correlated`。CGLIB 代理类型与源码类型不一致时可能仍为 null；不要虚构代理类型的源码事实来强行关联。
- 对未创建 Bean，目录负责将源码预期的生产者关联到 conditions 的配置类/方法。条件报告才是条件是否匹配的运行证据；目录本身不证明未创建原因。
- 属性条件的已知负向消息可给出 `PROPERTY_NOT_FOUND` / `PROPERTY_VALUE_MISMATCH`。未识别的语法保持 unknown；其它条件或图证据不完整时，局部原因可见而整体仍为 partial。
- 没有目录、条件权限不足、source key/Context 错配时，不应把空 items 写成“Bean 不存在”。`totalMatched: null` 表示不能确认完整匹配数。

单一具名 `ConditionalOnBean` 的负向消息只有在后缀名称与唯一 names 选择器一致时才解析；精确 conditionSources 与唯一目录生产者可将其关联到上游属性条件。未加载目录、Context/source 错配、多个要求无法归因或条件不可读时，继续返回 unknown/partial。已知类型选择器及传递条件使用同一证据链；未知语法保持证据缺口。

Bean 名称解析与目录中的 Java 类型/source 校验分别处理；条件消息支持的有界连字符名称，不代表所有名称都满足目录符号字段校验。运行代理与源码类型的全部组合、任意上游消息及完整 Boot 版本矩阵尚未验证。

图深度/关联上限、运行响应引用了未暴露 Bean、敏感标识脱敏、未扫描的类型关系不会因目录加载而消失。
详见[调用策略](contracts/tool-calling-policy.md)与[跨版本归一化](architecture/cross-version-normalization.md)。
