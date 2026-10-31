# 小众生产项目矩阵：Apache HertzBeat（opt-in）

HertzBeat 是真实生产使用的实时可观测/监控平台，规模明显小于前几轮的金融核心和大型
数据平台，但保留了完整的 Spring Boot、JPA/Flyway、H2、Sureness 鉴权和 Web UI 启动链。
本目录只用于用户明确授权的临时副本验收，不属于默认 pytest，也不连接任何生产实例。

| 项目 | 固定 tag | 总 / 主 Java 文件 | 原生 Boot | 构建 | 运行时 |
| --- | --- | ---: | --- | --- | --- |
| Apache HertzBeat | v1.7.3（`67ad4b04ef1b06b62f0e5030a26d0ca069294fa3`） | 1387 / 975 | 3.4.2 | Maven / Java 17 / Boot 3.4.2 | 原生 manager + 内嵌 H2 文件 |

## 拉取与构建

源码缓存位于 `/home/neil/.cache/spring-runtime-mcp/niche-matrix-20261023/hertzbeat`。
使用固定 tag 浅克隆，跳过上游测试和文档检查；manager 是启动应用，不需要单独的前端构建。

```bash
git clone --depth 1 --branch v1.7.3 https://github.com/apache/hertzbeat.git hertzbeat
cd hertzbeat
JAVA_HOME=/usr/lib/jvm/java-17-openjdk \
MAVEN_OPTS='-Xmx1536m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl hertzbeat-manager -am -DskipTests -Dmaven.test.skip=true \
  -Dcheckstyle.skip=true -Dspotless.skip=true -Dmaven.javadoc.skip=true -Drat.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
```

产物为 `hertzbeat-manager/target/classes`、各模块 `target/classes` 和
`hertzbeat-manager/classpath-runtime.txt`。上游测试、前端 UI 和发布包没有在本轮验证。

## 运行与隔离

`Manager` 使用原生 `application.yml` 的 `prod` profile 和 H2/Flyway。外部配置通过
`niche.properties` 以命令行参数传入，文件不命名为 `application.properties`，避免遮蔽
原生配置。H2 文件位于临时副本的 `.niche-diagnostics/data/`，全部监听回环随机端口。

`DiagnosticSecurity.java` 是测试专用的纯 Servlet Filter（不引入 Spring Security），
只匹配 `/actuator/**`：强制 GET/HEAD，匿名 401，普通 Bearer 403，管理员放行。
HertzBeat 的 Sureness 默认规则会拦截合成 Bearer，因此临时 classpath 前置一份
`sureness.yml`，仅追加 `/actuator/**===*` 放行；业务 `/api/**` 的 Sureness 规则保持原样。
这属于测试配置，不是生产推荐。

HertzBeat 的 Spring AI MCP server 保持原生启用；关闭它会导致
`webMvcSseServerTransportProvider` 缺少依赖 Bean。测试不调用外部模型或业务监控任务。

```bash
uv run --no-sync python scripts/check_niche_project_runtime.py \
  --project /home/neil/.cache/spring-runtime-mcp/niche-matrix-20261023/hertzbeat \
  --output /home/neil/.cache/spring-runtime-mcp/niche-matrix-20261023/hertzbeat-final-300s.json \
  --soak-seconds 300
```

## 正式 300 秒结果

最终运行 `accepted=true`、退出 0、`failureCodes=[]`：**1594 次调用**；875 个 Bean /
1167 条依赖，873 个可见 Bean 经 **87 页穷尽**；Flyway **5 条 APPLIED**；路由和 db 健康
均 ok/complete；最大完整回包 **15,072 字节**；中位/p95/最大延迟 547.253 / 1136.386 /
1849.020 ms；启动 13.653 秒、同宿主重启 14.395 秒；目标停止后重启恢复。脱敏聚合报告见
[results/hertzbeat-final-300s.json](results/hertzbeat-final-300s.json)。

## 验收内容

- 八工具按名称字母序发现、四项风险注解、两种官方 SDK 协议、非法参数拒绝。
- 管理端匿名 401、普通 Bearer 403、管理员正向读取；非 GET/HEAD 被过滤器拒绝。
- 真实 H2 库存的 Bean 全链分页、稳定快照、查询绑定和 60 秒游标过期。
- 原生 `/api/monitors` 路由、db 健康、2048 步启动树、Flyway 已应用迁移、配置默认关闭、
  OpenAPI 固定入口不可读负向、跨域漂移。
- 四路并发约 300 秒；目标停止返回 `TARGET_CONNECTION_REFUSED`，同一宿主重启后恢复。
- 每个结果检查 outputSchema、独立安全门和包含文本副本、服务端元信息及最长 request id
  的完整 16,384 字节预算。

## 限制

- 只验证 HertzBeat v1.7.3 / Java 17 / Boot 3.4.2 / H2 的一个固定提交，不是生产集群、
  MySQL/PostgreSQL、HA、长期运行或真实监控业务流量验收。
- H2 是内嵌数据库，本轮没有数据库暂停/恢复场景；可用性只覆盖目标停止/重启和健康读取。
- 管理 Bearer 过滤器和 Sureness 放行规则是测试注入，不是上游生产安全配置。
- 启动树为 partial，保留 `STARTUP_NODE_LIMIT`、`STARTUP_DEPTH_LIMIT` 等缺口；Bean 图
  仍有预算/源事实缺口，`totalMatched=null` 是预期结果。
- 前端 UI、上游测试、发布包和真实告警通道未验证。