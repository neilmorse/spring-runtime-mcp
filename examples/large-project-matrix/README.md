# 大型公开项目原生运行矩阵（opt-in）

只在用户明确授权的临时副本运行，不属于默认 pytest，不连接已有业务实例。
固定提交见 [projects.json](projects.json)，本轮证据见
[审计报告](../../docs/audits/large-project-stability-2026-10-22.md)。

| 项目 | 固定 tag | 主 Java 文件 | 原生 Boot | 运行配置 |
| --- | --- | ---: | --- | --- |
| Flowable | flowable-7.2.0 | 5525 | 3.5.4 | REST WAR，原生流程/CMMN/DMN/IDM 引擎，临时 H2 |
| Spring Cloud Data Flow | v2.11.5 | 1110 | 2.7.18 | 任务平台、原生 Flyway、临时 H2，关闭 streams/schedules |
| Spring Boot Admin | 4.1.3 | 242 | 4.1.1 | secure profile、WebFlux、独立管理端口，关闭 client/discovery |

文件数按整个固定仓库的 `**/src/main/java/**/*.java` 统计；不等同于加载的 Bean 数。
Admin 用于增加 Reactive 技术栈覆盖，不以其自身规模宣称比前轮 JHipster 大。
Admin tag 的 reactor revision 本身为 `4.1.3-SNAPSHOT`，不改 POM 或 Boot 版本。
使用 Java 21。构建跳过上游测试，不代表上游测试通过。

## 拉取与构建

以下目录位于磁盘缓存；本轮使用 `~/.cache/spring-runtime-mcp/large-matrix-20261022`。
先阅读各模块的后台任务和原生配置，再启动。所有 Maven 命令在对应仓库根目录运行。

```bash
git clone --depth 1 --branch flowable-7.2.0 https://github.com/flowable/flowable-engine flowable
git clone --depth 1 --branch v2.11.5 https://github.com/spring-cloud/spring-cloud-dataflow dataflow
git clone --depth 1 --branch 4.1.3 https://github.com/codecentric/spring-boot-admin spring-boot-admin
```

Flowable：

```bash
MAVEN_OPTS='-Xmx640m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -Pdistro -pl modules/flowable-app-rest -am \
  -DskipTests -Dmaven.test.skip=true -Dskip.test.db.drop=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
```

Data Flow：

```bash
MAVEN_OPTS='-Xmx640m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl spring-cloud-dataflow-server -am \
  -DskipTests -Dmaven.test.skip=true -Ddisable.checks=true \
  -Ddisable.nohttp.checks=true -Dmaven.javadoc.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
```

Admin：

```bash
MAVEN_OPTS='-Xmx640m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl spring-boot-admin-samples/spring-boot-admin-sample-reactive -am -PnoNpm \
  -DskipTests -Dmaven.test.skip=true -Dspring-javaformat.skip=true \
  -Dcheckstyle.skip=true -Dmaven.javadoc.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
```

`noNpm` 是上游提供的服务端构建配置，会复制前端测试占位资源；本轮没有验证 UI。
首次构建可联网下载公开依赖，缓存完成后可加 `-o`。Data Flow 原生 MariaDB 依赖使用版本范围，
因此源码 SHA 不是完整依赖锁；摘要记录实际运行 jar 文件名及其集合哈希。
**正确参数是 `-DincludeScope=runtime`，`-Dmdep.includeScope=runtime` 不会设置此插件的 scope。**
后者会混入测试依赖，不能用于原生运行结论。
Flowable 原生 WAR 把内嵌 Tomcat 标为 provided；脚本只从该 WAR 的 `WEB-INF/lib-provided/`
补回容器 jar，不引入测试依赖，不覆盖缓存 jar。

## 隔离与鉴权

`LargeProjectLauncher` 加载原生 `@SpringBootApplication`，仅添加 `DiagnosticSecurity` 配置，
安装 `BufferingApplicationStartup(8192)`。不替换业务控制器、引擎、数据库迁移或原生 POM。
本目录的 properties 是外部运维启动参数，生成内容保存在临时副本 `.large-diagnostics/`。
全部监听随机回环端口；H2 仅在内存，无 TCP/控制台；关闭 Flowable 演示定义和异步执行器、
消息集成、Config Client，以及 Admin 自注册/发现。Data Flow 云平台账号为空，不触发云客户端创建。
不提交/部署流程，不部署任务，不调用业务写接口。

Bearer admin/user 令牌只生成在内存并经环境传递，绝不写入 properties、摘要或命令参数。
Jakarta Servlet / Reactive 使用最高优先级且仅匹配 `/actuator` 的鉴权链；Data Flow 的旧版
`WebSecurityConfigurer` 不能与独立 `SecurityFilterChain` 混用，因此使用 Actuator 专用
Servlet Filter，在原生忽略路径之前强制鉴权。三项均拒绝非 GET/HEAD、无认证和权限不足访问。
保留原生业务安全配置。Flowable 默认空 role prefix，health 的授权角色须显式使用
`ROLE_DIAGNOSTICS`。其未暴露端点可能被原生 `/error` 安全链转换为 401，按不可读取记录，
不能推断为成功观察到了 404。
目标框架日志关闭；启动异常仅保留有界类型、Bean 标识和固定阶段码，丢弃消息与堆栈。

## 执行验收

回到本项目根目录，在已同步的锁定 Python 环境中执行：

```bash
uv run --no-sync python scripts/check_large_project_runtime.py \
  --name flowable --project /absolute/cache/flowable --output /absolute/cache/flowable-result.json
uv run --no-sync python scripts/check_large_project_runtime.py \
  --name dataflow --project /absolute/cache/dataflow --output /absolute/cache/dataflow-result.json
uv run --no-sync python scripts/check_large_project_runtime.py \
  --name spring-boot-admin --project /absolute/cache/spring-boot-admin --output /absolute/cache/admin-result.json
```

每项测试覆盖：八工具发现与风险注解、两种官方 SDK 协议、正常/401/403、已知 Bean/路由、
健康/启动、原生迁移或明确不可读错误、默认配置关闭、漂移、全链可见 Bean 分页、
查询参数绑定、60 秒游标过期、四路并发约 90 秒、目标停止与同一 MCP 宿主恢复。
所有调用检查 outputSchema、独立安全门，以及含重复文本/元信息/最长 request id 的完整
16,384 字节预算。保存耗时和 RSS/FD 聚合，不保存目标响应。
`totalMatched=null` 和脱敏/图预算/未知条件等 partial 必须保留，不算完整覆盖。
`accepted` 表示这些有限验收的通过与否，不代表完整 Spring 版本矩阵或长时间生产稳定性。

随机游标与安全门冲突可单独离线复现：

```bash
uv run --no-sync python scripts/probe_large_project_stability.py --output /absolute/cache/cursor-probe.json
```

该探针退出 0 表示成功复现已知缺陷，不表示缺陷已修复；不修改或绕过安全门。
