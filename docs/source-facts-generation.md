# 显式登记 Java 静态事实

`scripts/generate_source_facts.py` 是仓库内的离线维护脚本，生成现有 CLI 可加载的 Source catalog 和 `springboot_detect_drift` 可接收的参数。它不增加 MCP 工具、端点或 Python 运行依赖，MCP 进程仍不扫描工作区。

## 执行与产物

需要完整 JDK（含 `java`、`javac`），以及按[验证流程](launch/README.md)同步的锁定 Python 环境。仅通过重复的 `--source` 登记相对项目根的 `.java` 文件，不递归扫描、不展开 glob。`contextId` 必须来自操作者核对过的运行报告，脚本不推测它。

```bash
uv run --no-sync python scripts/generate_source_facts.py \
  --project-root /absolute/project \
  --source src/main/java/example/Service.java \
  --source src/main/java/example/Configuration.java \
  --context-id application --target-id local \
  --output-dir /tmp/project-source-facts-new
```

输出目录必须不存在，包含：

- `source-catalog.json`：经现有加载器校验的类型和生产者。实现类型未知时为 null；不猜测工厂实现或运行代理类型。
- `drift-arguments.json`：存在已识别 Bean 或路由时才生成，经现有漂移参数校验。未识别到某维度时省略该维度；两者都未识别时不生成此文件，不能将空数组充当完整空预期。
- `source-facts-report.json`：始终为 partial，记录固定缺口、登记文件的 SHA-256 及运行身份未采集状态。报告不写入 catalog，也不是工具信封。

漂移 Bean 预期只使用已识别名称与指定 Context；声明返回接口不等同于运行对象类型，因此不生成类型相等约束。`expectedScopeComplete` 始终为 false，防止把登记范围外的运行 Bean 或路由判为额外对象。源码声明是调用者的比较预期，不保证条件 Bean 一定创建，也不证明路由已经注册。应先审核生成结果，再把参数传给 MCP 工具。

## 支持的静态子集

脚本在最小环境中编译仓库自带的 [JDK helper](../scripts/java/SourceFacts.java)，使用 `JavacTask.parse()` 解析登记文件的临时字节快照。它不分析符号、不编译目标源码、不运行目标 main/静态初始化器/注解处理器，也不读取目标 classpath、POM 或网络。不能以解析成功代替 Java 编译通过。

当前处理顶层普通 class/interface、可明确解析的显式父类型、标准 `@Configuration` 中的标准 `@Bean`，以及标准 Controller 中受支持的字面量映射。名称解析限于已登记声明、明确且无歧义的 import、有限 java.lang 类型及支持的全限定名。`@Bean` 名称/别名须是字面量；缺省名称依据标准 Bean 方法名。

直接父类型只描述源码显式的 extends/implements；没有显式声明可记录空数组。任一父类型无法确定时省略整个 type 并记录缺口，不能用空数组替代未知。通配 import、泛型、嵌套/record/enum、动态名称、自定义元注解、重载与名称冲突、无法排除的遮蔽及复杂映射会被跳过或留下缺口。声明不在已支持子集内，不表示运行对象不存在。

路由仅处理支持的正向字面路径和显式方法；额外条件、未知注解、继承或同方法多个映射不生成确定路由。静态摘要不包含源码正文、注释、方法体字面值或自由文本。

## 条件来源登记

默认 `conditionSources=[]`，报告记录 `CONDITION_SOURCES_UNBOUND`。脚本不会从 Bean 名拼出 conditions source key。需要条件链关联时，操作者可用 `--condition-sources relative/bindings.json` 显式登记 JSON 映射：

```json
{
  "example.StripeConfiguration#stripeClient": ["StripeConfiguration#stripeClient"]
}
```

左侧是生成器识别出的配置类与工厂方法，右侧必须来自已核实的目标 conditions 报告。未匹配的左侧键会失败，避免拼写错误被忽略；它仍是操作者声明，生成器不联网核实。示例的登记文件见 [source-condition-bindings.json](../examples/injected-faults/source-condition-bindings.json)。关联边界见 [Source catalog](source-catalog.md)。

## 限额与失败

最多登记 256 个文件，单文件 256 KiB、合计 2 MiB；helper 最多输出 1,000 个事实，catalog 仍受现有 256 KiB/1,000 条限制，漂移预期仍受现有 100 个实体限制。超限应收窄登记，不静默分页或截断成完整集合。

文件通过目录描述符和 `O_NOFOLLOW` 读取，拒绝符号链接、越界路径、非常规文件及读取期间变化；该安全读取实现依赖支持这些接口的平台。各文件单独采样，不构成原子仓库快照。生成的字符串执行现有 SanitizerPipeline 字符串规则，再经独立输出门检查；不能安全输出时失败，不修改标识来伪造关联。

失败退出 2，仅向 stderr 输出固定分类，不回显编译诊断、源码或异常栈；成功退出 0。先验证再一次性移动临时产物目录，不覆盖已有结果。构建与运行产物的区别见[本地构建证据](build-evidence.md)。
