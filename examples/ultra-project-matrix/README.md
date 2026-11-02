# 超大型生产系统矩阵：Apache Fineract（opt-in）

本目录只用于用户明确授权的临时副本验收，不属于默认 pytest，也不连接任何生产实例。
目标是补上现有矩阵没有覆盖的金融核心系统、Java 17 / Boot 3.1.7、Gradle 多模块与
真实 PostgreSQL 运行路径；不把一次固定提交的通过写成完整版本矩阵。

| 项目 | 固定 tag | 总 / 主 Java 文件 | 原生 Boot | 构建 | 运行时 |
| --- | --- | ---: | --- | --- | --- |
| Apache Fineract | 1.9.0（`5d96e8cc32ff63f97d5ac15e19c6fafee0c31357`） | 4565 / 4087 | 3.1.7 | Gradle 8.5 / Java 17 | 临时 PostgreSQL 16，回环 HTTP |

文件数按整个仓库 `*.java` 与 `**/src/main/java/**/*.java` 统计；实际加载 Bean 数以
验收摘要为准。Fineract 是真实金融机构使用的核心账务平台，但本轮只启动一次性本地副本，
不部署、不连接既有业务数据、不执行任何业务写请求。

## 拉取与构建

源码缓存位于 `~/.cache/spring-runtime-mcp/ultra-matrix-20261023/fineract`。
浅克隆固定 tag 后，用 Java 17 编译 provider；跳过上游测试、文档和 Swagger 生成。

```bash
git clone --depth 1 --branch 1.9.0 https://github.com/apache/fineract.git fineract
cd fineract
git apply /abs/path/to/spring-runtime-mcp/examples/ultra-project-matrix/fineract-build-workaround.patch
JAVA_HOME=/usr/lib/jvm/java-17-openjdk \
GRADLE_OPTS='-Dorg.gradle.jvmargs=-Xmx1536m -Dorg.gradle.parallel=false' \
./gradlew --no-daemon --console=plain :fineract-provider:classes \
  -x test -x cucumber -x resolve -x check -x spotlessCheck
```

[patch](fineract-build-workaround.patch) 只做两件事：给 `pluginManagement` 增加公共
镜像回退，以及追加 `dumpRuntimeClasspath` 任务；不修改 Boot/BOM、provider 依赖或
运行时 classpath。

Fineract 的文档插件依赖 `com.burgstaller:okhttp-digest:1.10`，该制品位于已停用的
JCenter，Gradle 插件门户返回缺失。临时副本在 `settings.gradle` 的 `pluginManagement`
中增加公共镜像 `https://maven.aliyun.com/repository/public` 作为回退；这是构建来源调整，
不改变 Fineract 的 Boot/BOM、provider 依赖或运行时 classpath。镜像可用性与供应链风险
属于本轮限制，不应把该构建命令当成长期可复现的官方构建。

编译完成后生成运行 classpath：

```bash
./gradlew --no-daemon :fineract-provider:dumpRuntimeClasspath
# 结果：fineract-provider/classpath-runtime.txt
```

`dumpRuntimeClasspath` 任务由本轮临时追加，不写入上游源码控制。

## 启动与隔离

`FineractDiagnosticsLauncher.java` 只做三件事：反射调用 Fineract 原生
`ServerApplication.configureApplication` 保留原生配置，注入
`BufferingApplicationStartup(2048)`，并注册管理专用 `DiagnosticSecurity`。
`DiagnosticSecurity` 复用大型矩阵模板，只匹配 `/actuator/**`，强制 GET/HEAD、
匿名 401、非管理员 403、管理员 `ROLE_DIAGNOSTICS`；不替换 `/api/**` 原生 Basic Auth。

运行配置通过外部 properties 提供：根 context path、HTTP、同端口 Actuator、只读端点、
`env/configprops` 永不显示值、关闭 JMS/Kafka/外部事件/批处理/遥测。数据库使用
`postgres:16-alpine` 一次性容器，仅发布到 `127.0.0.1` 随机端口；初始化脚本创建
`fineract_tenants`、`fineract_default` 和专用 `fineract` 用户。密码由脚本随机生成，
只经环境变量传给应用，不写入 properties、命令参数或摘要。

```bash
uv run --no-sync python scripts/check_ultra_project_runtime.py \
  --project ~/.cache/spring-runtime-mcp/ultra-matrix-20261023/fineract \
  --output ~/.cache/spring-runtime-mcp/ultra-matrix-20261023/fineract-result.json \
  --soak-seconds 300
```

脚本会自行创建/删除命名数据库容器和目标进程，结束后不留下本轮容器、网络或 MCP 子进程。

## 当前断言与容量边界

- Fineract 的 Jersey `/api/*` 路由不在 dispatcher 映射中；相关查询应保留 partial、totalMatched=null 和 NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED。可见 `/actuator/health` 注册事实与业务路由缺口分别断言。
- 启动快照受归一化节点/深度预算约束；本启动器使用 2048 步缓冲。更大缓冲可能触发 NORMALIZATION_LIMIT，不能靠放宽产品预算掩盖容量边界。
- 数据库暂停时检查有界不可用结果、Bean 读取及恢复；这不是生产告警、耐久性或 HA 验证。
- 分页检查完整可见快照及无重复项，totalMatched 和 coverage 依证据完整性表达，不能将可见条目数当作原生完整总数。

[保存的聚合](results/fineract-final-300s.json)只对应其固定提交、配置和运行窗口，不代表本次执行或当前版本的容量基准。

## 验收内容

- 八工具按名称字母序发现、四项风险注解、两种官方 SDK 协议、非法参数拒绝。
- 管理端匿名 401、普通 Bearer 403、管理员正向读取；非 GET/HEAD 在过滤器层拒绝。
- 可见 Bean 全链分页、稳定快照、无重复页、`CURSOR_QUERY_MISMATCH` 和 60 秒
  `CURSOR_EXPIRED`。
- 原生 Bean/条件、路由、健康（含 db 组件）、启动树、Liquibase/不可读迁移、
  OpenAPI 不可读负向、配置默认关闭与登记前缀、跨域漂移。
- 四路并发约 300 秒；目标停止时返回 `TARGET_CONNECTION_REFUSED`，同一 MCP 宿主在目标
  重启后恢复。
- 可用性故障：暂停 PostgreSQL 后健康不得保持 UP，Bean 读取仍应可用；恢复后健康回到 UP。
- 每个结果检查 outputSchema、独立安全门和包含文本副本、服务端元信息及最长 request id
  的完整 16,384 字节预算。

## 限制

- 只验证 Fineract 1.9.0 / Java 17 / Boot 3.1.7 / PostgreSQL 16 的一个固定提交，不是
  全版本矩阵，也不是生产集群、HA、长期运行或真实业务流量验收。
- 当前连接器固定读取 `/actuator/openapi`；Fineract 的 springdoc 入口不是该路径，因此
  OpenAPI 只做不可读负向断言，不代表正向兼容。`/actuator/liquibase` 是否暴露
  以实际摘要为准；不可读时只验证错误码。
- Fineract 的 JAX-RS 业务路由不在 Actuator mappings 中；本轮只验证工具会保守返回
  partial/gap，不验证具体业务路由的正向匹配。`/api/v1/offices` 探针的 `observed=false`
  必须与 `NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED` 一起阅读。
- 管理专用 Bearer 过滤器和启动缓冲是测试启动器注入，不是上游原生安全配置；默认生产
  部署仍须由维护者按原生安全链授权，不能把本测试配置当作产品推荐。
- 数据库暂停只验证短时恢复，不验证 PostgreSQL 持久性、复制、故障切换或长期连接泄漏。
- 300 秒并发只说明本机有限窗口内的稳定性；RSS/延迟不是生产容量基准。
- Gradle 插件镜像回退只解决已停用 JCenter 制品，不证明上游构建在干净环境中无需修改。