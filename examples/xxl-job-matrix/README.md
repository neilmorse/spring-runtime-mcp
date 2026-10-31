# 调度器生产项目矩阵：XXL-JOB（opt-in）

XXL-JOB 是真实生产使用的小型分布式任务调度平台，规模明显小于 Fineract/Flowable，
但包含 Spring Boot 4、SSO 拦截器、MyBatis、MariaDB 持久化和原生 Actuator。本目录只用于
用户明确授权的临时副本验收，不属于默认 pytest，也不连接任何生产调度器。

| 项目 | 固定 tag | 总 / 主 Java 文件 | 原生 Boot | 构建 | 运行时 |
| --- | --- | ---: | --- | --- | --- |
| XXL-JOB | v3.4.0（`555b48f2edf0e51cd77971565342d80c15c9f18d`） | 157 / 136 | 4.0.5 | Maven / Java 17 source / Java 21 runtime | 原生 admin + 一次性 MariaDB 11.2 |

## 拉取与构建

源码缓存位于 `/home/neil/.cache/spring-runtime-mcp/niche-matrix-20261023/xxl-job`。

```bash
git clone --depth 1 --branch v3.4.0 https://github.com/xuxueli/xxl-job.git xxl-job
cd xxl-job
JAVA_HOME=/usr/lib/jvm/java-21-openjdk \
MAVEN_OPTS='-Xmx1536m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl xxl-job-admin -am -DskipTests -Dmaven.test.skip=true \
  -Dcheckstyle.skip=true -Dspotless.skip=true -Dmaven.javadoc.skip=true -Drat.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
```

产物为 `xxl-job-admin/target/classes`、`xxl-job-core/target/classes` 和
`xxl-job-admin/classpath-runtime.txt`。上游测试、UI、执行器部署和发布包未在本轮验证。

## 隔离与启动

- MariaDB 11.2 一次性容器，仅发布到 `127.0.0.1` 随机端口；初始化使用上游
  `doc/db/tables_xxl_job.sql`，数据库 `xxl_job` 和用户 `xxl` 由容器随机密码创建。
- 外部配置通过 `niche.properties` 传入，未命名为 `application.properties`；关闭
  `/xxl-job-admin` context path，Actuator 位于 `/actuator`。
- `xxl-sso.client.excluded.paths=/actuator/**` 让原生 SSO 拦截器不处理管理端点；
  业务 UI 的 SSO 规则保持原样。测试专用纯 Servlet Filter 只匹配 `/actuator/**`：
  GET/HEAD、匿名 401、普通 Bearer 403、管理员放行。
- XXL-JOB 自带的 `logback.xml` 在 Spring Boot 配置前被 Logback 加载，会尝试写
  `/data/applogs`；临时 classpath 前置 root OFF 的 `logback.xml` 遮蔽它。未修改上游
  资源。
- 启动器保留原生 `XxlJobAdminApplication`，注入 2048 步启动缓冲；不启动任何业务任务。

```bash
uv run --no-sync python scripts/check_xxl_job_runtime.py \
  --project /home/neil/.cache/spring-runtime-mcp/niche-matrix-20261023/xxl-job \
  --output /home/neil/.cache/spring-runtime-mcp/niche-matrix-20261023/xxl-job-final-300s.json \
  --soak-seconds 300
```

## 正式 300 秒结果

最终运行 `accepted=true`、退出 0、`failureCodes=[]`：**2449 次调用**；356 个 Bean /
402 条依赖，356 个可见 Bean 经 **35 页穷尽**；路由和 db 健康 ok/complete；迁移/OpenAPI
固定入口 404 负向；启动 partial；最大完整回包 **15,638 字节**；中位/p95/最大延迟
272.912 / 639.210 / 3042.335 ms；启动 2.838 秒、同宿主重启 3.702 秒；MariaDB 暂停后
健康 DOWN、Bean 读取仍可用、恢复后 UP。脱敏聚合报告见
[results/xxl-job-final-300s.json](results/xxl-job-final-300s.json)。

## 验收内容

- 八工具发现、两项 SDK 协议、风险注解、非法参数拒绝。
- 管理端匿名 401、普通 Bearer 403、管理员正向读取；非 GET/HEAD 被过滤器拒绝。
- 356 个 Bean / 402 条依赖的完整分页、游标绑定/过期、路由、健康、启动树、配置默认关闭、
  OpenAPI 与迁移端点负向、跨域漂移。
- 四路并发约 300 秒；目标停止/同宿主重启；MariaDB 暂停后健康 DOWN、Bean 读取仍可用、
  恢复后 UP。
- 每个结果检查 outputSchema、独立安全门和完整 16,384 字节预算。

## 限制

- 只验证 XXL-JOB v3.4.0 / Boot 4.0.5 / Java 21 runtime / MariaDB 11.2 的一个固定提交，
  不是生产调度集群、执行器网络、任务执行、告警或长期运行验收。
- 管理 Bearer 过滤器、SSO actuator 放行和 Logback 遮蔽是测试配置，不是上游推荐。
- 启动树为 partial；迁移端点不可用；数据库暂停只验证短时恢复，不验证复制/HA/持久性。
- 未验证 UI、上游测试、执行器任务和发布包。