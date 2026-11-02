# 四小时生产模拟：Nacos 2.4.3（opt-in）

Nacos 是真实生产使用的服务注册与配置中心。本目录记录一次固定提交的本地隔离、
四小时持续运行验收，不属于默认 pytest，也不连接任何生产 Nacos 集群。

## 项目选择

从一组有真实生产使用、带 Spring Boot 运行时的热门项目中，用
`shuf -n 1` 随机抽取；候选池与选择结果保存在 `projects.json`。本轮选中：

| 项目 | 固定 tag / revision | GitHub | 规模 | 原生 Boot | 运行时 |
| --- | --- | ---: | ---: | --- | --- |
| alibaba/nacos | 2.4.3 / `f4f8b189cf16186669de5b692d43630ed2c3fda2` | 33,471 stars | 2,391 Java 文件（1,526 main，22 Maven 模块） | 2.7.18 | Java 21 / MariaDB 11.2 |

固定提交日期为 2024-10-12。star 数是 2026-10-23 的公开仓库快照，只用于说明
项目热度，不代表本轮已验证其所有生产功能。

## 构建

源码缓存位于运营方本地 `$NACOS_CACHE/nacos`（本轮为一次性缓存目录，不属于仓库）。

```bash
export NACOS_CACHE=/path/to/soak-matrix-20261023
git clone --depth 1 --branch 2.4.3 https://github.com/alibaba/nacos.git \
  "$NACOS_CACHE/nacos"
cd "$NACOS_CACHE/nacos"
JAVA_HOME=/usr/lib/jvm/java-21-openjdk \
MAVEN_OPTS='-Xmx2g -Djava.awt.headless=true' mvn -B --no-transfer-progress \
  -Prelease-nacos -T 1C -DskipTests -Dmaven.test.skip=true \
  -Dcheckstyle.skip=true -Drat.skip=true -Dpmd.skip=true -Dspotbugs.skip=true \
  clean install
JAVA_HOME=/usr/lib/jvm/java-21-openjdk mvn -B -q --no-transfer-progress \
  -pl console dependency:build-classpath \
  -Dmdep.outputFile=classpath-runtime.txt -DincludeScope=runtime
```

产物为 `distribution/target/nacos-server-2.4.3/nacos/target/nacos-server.jar`、
`console/target/classes` 与运营方生成的 `console/classpath-runtime.txt`。上游测试、
前端、集群与发布包安装器未在本轮验证。

### 构建副本的 Hessian 冲突

2.4.3 的 fat jar 同时包含：

- `com.alipay.sofa:hessian:3.3.6`，由 SOFA JRaft 传递；
- `com.caucho:hessian:4.0.63`，`NacosHessianSerializerFactory` 需要。

两者使用相同的 `com.caucho.hessian.io` 包，JVM 在本环境优先加载 3.3.6 时启动失败。
`check_nacos_soak.py` 只复制 fat jar，并在这个副本中删除 3.3.6 及其 classpath 索引项；
原始源码、原始构建产物均不修改。这是测试副本的构建/加载变通，不是生产建议；
未验证 JRaft 快照序列化在删除旧 Hessian 后的全部行为。

## 隔离与启动

- Nacos 只监听 `127.0.0.1`；业务端口与独立管理端口均为随机回环端口。
- MariaDB 11.2 一次性容器只发布到回环随机端口，使用上游
  `distribution/conf/mysql-schema.sql` 初始化 `nacos_config`。数据库密码只通过进程
  环境变量传给测试启动器，不写入源码、属性文件、报告或日志。
- `NacosDiagnosticsLauncher` 保留原生 `com.alibaba.nacos.Nacos`，注入 8192 步
  `BufferingApplicationStartup`，使 `/actuator/startup` 可读；不执行任何业务写入。
- `DiagnosticManagementSecurity` 只经管理子上下文注册：匿名 401、普通 Bearer 403、
  管理员放行，非 GET/HEAD 返回 405。管理端口是 MCP 唯一目标。
- 业务端点 `nacos.core.auth.enabled=false` 是本轮隔离副本配置，不等同于生产建议；
  测试只发 GET，不调用配置发布、服务注册、命名实例写入或 UI 登录。
- Actuator 暴露 health、info、beans、conditions、mappings、startup、env、configprops；
  配置中虽有 `show-values=never`，但 Boot 2.7 不支持该属性，不能据此认为目标值已全量屏蔽。MCP 自身的配置诊断仍默认关闭；目标端值保护须按[旧版配置指南](../../docs/target-app-setup.md)另行审查。

## 四小时运行

在本仓库根目录执行，先按[验证流程](../../docs/launch/README.md)准备锁定环境。每次新建结果目录：入口在启动资源前独占创建 JSON 与 JSONL 文件，任一路径已存在（含符号链接）或两者相同时退出 2。未指定 `--progress` 时使用 output 的 `.jsonl` 同名路径。启动中断可能留下空占位文件，重新运行时使用新目录。

```bash
NACOS_RESULT_DIR=$(mktemp -d /tmp/spring-runtime-nacos-XXXXXXXX)
uv run --no-sync python scripts/check_nacos_soak.py \
  --project "$NACOS_CACHE/nacos" \
  --distribution "$NACOS_CACHE/nacos/distribution/target/nacos-server-2.4.3/nacos" \
  --classpath-file "$NACOS_CACHE/nacos/console/classpath-runtime.txt" \
  --output "$NACOS_RESULT_DIR/result.json" \
  --progress "$NACOS_RESULT_DIR/progress.jsonl" \
  --soak-seconds 14400 --workers 4 --worker-delay 0.5 --sample-seconds 60
```

运行器在 14,400 秒 soak 窗口内：

- 四路并发轮换 health、beans、mappings、startup 读调用；每个结果仍经过公开
  outputSchema、独立安全出口和 16,384 字节完整帧预算。
- 在 30 分钟、2 小时和 3.5 小时做全量 Bean 分页，验证无重复页、快照稳定、
  519 个可见 Bean 与基线一致。
- 每个分页周期做非法参数、游标查询绑定、配置默认关闭、OpenAPI/迁移固定入口 404
  和路由/健康/启动正向量。
- 1 小时与 2.5 小时停止并同宿主重启 Nacos，验证停止时明确拒绝、恢复后读事实可用。
- 1.5 小时与 3 小时暂停 MariaDB，记录 Nacos 自身 readiness 和 Actuator health；
  期间不绕过 MCP，也不隐藏目标级不可用。
- 每 60 秒记录目标/MCP 宿主 RSS、FD、线程、CPU、数据库容器状态、直接 readiness
  与 Actuator health 状态到 JSONL；不保存目标响应正文或凭据。目标重启时 PID 更换，
  该采样点的 CPU 差值无效，不用于资源摘要。

短程自检（不产生正式结果）：

```bash
uv run --no-sync python scripts/check_nacos_soak.py ... \
  --soak-seconds 180 --workers 4 --worker-delay 0.5 --sample-seconds 20 \
  --smoke-phases
```

## 正式四小时结果

正式运行 `accepted=true`、`failureCodes=[]`、退出 0；soak 窗口
**14,401.542 秒**，共 **68,260 次** MCP 调用（soak 内 68,189 次），240 个逐分钟样本，
非预期错误码为空。

| 指标 | 结果 |
| --- | --- |
| 状态分布 | ok 25,525 / partial 42,708 / denied 2 / invalid 5 / unavailable 20 |
| 预期错误 | 401/403 2、非法参数 5、OpenAPI/迁移 404 8、配置关闭 4、游标不匹配 4、游标过期 1、目标停止 3 |
| 延迟 | 中位 242.754 ms；p95 945.435 ms；最大 2,087.568 ms |
| 最大完整回包 | 15,242 字节（低于 16,384） |
| Bean 分页 | 基线 519 / 52 页；三个周期均 519 / 44 页，无重复页、无快照漂移 |
| 目标重启 | 2 次计划内重启，恢复 9.964 / 10.623 秒；最终验收再重启一次 |
| MariaDB 暂停 | 2 次，readiness 均超时约 5 秒并在解锁后首次检查恢复；Actuator 始终 UP |
| 资源 | 目标 RSS 中位 639,404 KiB（90,508–1,025,304）；MCP 宿主 RSS 中位 77,746 KiB、FD 7–8 |
| 清理 | 目标、MariaDB 容器、全部 MCP 子进程停止 |

以下脱敏聚合只描述其对应固定提交、配置和运行窗口，不代表当前工作树或完整兼容矩阵；逐分钟记录另按本地留存策略处理：

- [results/nacos-four-hour-2026-10-23.json](results/nacos-four-hour-2026-10-23.json)
- `results/nacos-four-hour-2026-10-23.jsonl`：本地逐分钟记录，保留在磁盘并由 Git 忽略，不随仓库或分发包交付；公开证据使用上方聚合 JSON。
- [构建/补丁哈希](results/nacos-four-hour-2026-10-23-build.json)

已知重要限制：Nacos 的 Actuator `db` 指标来自内嵌 Derby，外部 MariaDB 暂停时
readiness 超时但 MCP `diagnose_health` 仍会显示 UP；结果保留
`actuatorObservedExternalDbOutage=false`，不把该 UP 当作外部数据库可用性证明。

## 限制

- 只验证 Nacos 2.4.3 固定提交、Boot 2.7.18、Java 21、单节点 standalone 和 MariaDB 11.2；
  不是生产集群、HA、Raft 多节点、鉴权插件、配置发布或注册中心客户端流量验收。
- Actuator 的 `db` health 来自内嵌 Derby 数据源，不能反映外部 MariaDB 故障；MariaDB
  暂停时 Nacos readiness 超时，而 MCP 的 `diagnose_health` 仍可能显示 UP。该盲区在结果
  中显式记录，不作为 PASS 依据。
- Hessian 变通、管理 Bearer、独立管理端口、启动缓冲和业务鉴权关闭均为测试配置。
- 未验证前端、上游测试、发布包安装器、生产配置写路径、真实客户端长连接与告警。