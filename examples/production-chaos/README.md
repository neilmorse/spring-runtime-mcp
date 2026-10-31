# 有生产采用记录的项目与故障注入（显式 opt-in）

只测试自行启动的临时副本，默认 pytest 不运行这些脚本。固定提交、原生 Boot 版本、已知业务路由及公开采用证据见 [projects.json](projects.json)。采用证据不表示测试接触过任何厂商的生产实例。源码文件数与运行规模分开统计；并不宣称这三个仓库都比上一轮 Flowable 源码更大。

## 构建

在磁盘缓存中克隆，不使用内存型 `/tmp` 存储整个仓库。各命令在对应仓库根运行，跳过上游测试，不据此宣称上游测试通过。

```bash
git clone --depth 1 --branch v2.7.1 https://github.com/apache/shenyu shenyu
git clone --depth 1 --branch v4.2.1 https://github.com/thingsboard/thingsboard thingsboard
git -c http.version=HTTP/1.1 clone --depth 1 --filter=blob:none --sparse --branch 3.4.3 \
  https://github.com/apache/dolphinscheduler dolphinscheduler
```

DolphinScheduler 使用 sparse checkout 获取根目录所有 `dolphinscheduler-*` 后端模块、`.mvn`、`config`、`tools`、`script`，包括 reactor 引用的 UI/dist/microbench/API-test POM；未下载全部 docs，也未初始化 CI actions 子模块。检查本地 revision 与清单一致后再运行。

ShenYu：

```bash
MAVEN_OPTS='-Xmx768m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl shenyu-admin -am -DskipTests -Dmaven.test.skip=true -Dcheckstyle.skip=true \
  -Drat.skip=true -Dmaven.javadoc.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
```

ThingsBoard 的历史验收在临时副本中添加可选诊断 profile，不更换原生 Boot/BOM，不改变本项目 Python 依赖。当前留存的 `thingsboard-actuator.patch` 为空，不能用它复现该 profile；需另行恢复补丁并在授权的隔离实例中验收。本段仅保留当时构建记录，不是当前可直接执行的复现流程。

```bash
MAVEN_OPTS='-Xmx896m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl application -am -Pruntime-diagnostics -DskipTests \
  -Dskip.installyarn=true -Dskip.yarn=true \
  -Dlicense.skipCheckLicense=true -Dlicense.skipAddLicense=true \
  -Dpkg.disabled=true -Dpkg.package.phase=none -Dpkg.process-resources.phase=none \
  -Ddockerfile.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=runtime -Dmdep.outputFile=classpath-runtime.txt
mvn -B -q --no-transfer-progress -pl application \
  org.springframework.boot:spring-boot-maven-plugin:3.4.10:build-info
```

跳过 UI 的真实参数是 `skip.installyarn` / `skip.yarn`。`pkg.disabled` 同时跳过 build-info，因此须显式补回该原生目标；操作系统打包阶段另外设置为 `none`，避免无关的 Gradle/deb/rpm 构建。安装数据目录由原生 `application/src/main/data` 与 `dao/src/main/resources/sql` 装配，安装由原生 `ThingsboardInstallApplication` / `ThingsboardInstallService` 完成。

DolphinScheduler：

```bash
JAVA_HOME=/usr/lib/jvm/java-17-openjdk PATH=/usr/lib/jvm/java-17-openjdk/bin:$PATH \
MAVEN_OPTS='-Xmx896m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -pl dolphinscheduler-standalone-server -am -DskipTests -Dmaven.test.skip=true \
  -Dcheckstyle.skip=true -Dspotless.skip=true -Drat.skip=true -Dmaven.javadoc.skip=true \
  package org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -DincludeScope=compile -Dmdep.outputFile=classpath-compile.txt
```

Java 21 构建遇到原生 Lombok 1.18.20 的 `JCTree$JCImport.qualid` 错误，改用本机 Java 17，未覆盖依赖版本。Standalone 的业务模块原生声明为 provided，因此读取 compile classpath，保留其 provided 依赖，不混入 test scope。Standalone 是上游开发装配，不代表生产分布式集群验收。

## 执行与边界

在本项目的锁定 Python 环境运行，Docker 镜像需事先准备：

```bash
docker pull eclipse-temurin:21-jdk-jammy
# ThingsBoard 另需 pgvector/pgvector:pg16；本次使用本机已有缓存。
uv run --no-sync python scripts/check_production_chaos.py \
  --name thingsboard --project /absolute/cache/thingsboard --output /absolute/cache/thingsboard-chaos.json
```

`--name` 也支持 `shenyu` / `dolphinscheduler`。脚本检查固定源码 SHA，但源码 SHA 不等于依赖锁；报告记录实际 jar 名称和运行镜像 ID。镜像 tag 可变，复验应按审计报告的 digest 固定本地镜像。

应用只向宿主 `127.0.0.1` 发布随机管理端口，数据库不发布宿主端口；独立 Docker bridge、只读应用根文件系统、限制内存/CPU，临时目录和自有控制文件可写。此 bridge **不是完整出网沙箱**；显式关闭上游外部客户端与遥测，不触及其他生产服务。不提交业务任务、工作流或设备数据。

Bearer admin/user 和数据库密码随机生成，仅内存及环境传递；不写 properties/摘要/命令参数。管理专用 Servlet Filter 先强制 GET/HEAD 与 401/403，再交给原生安全链。Boot 2 使用 javax，Boot 3 使用 jakarta；不替换业务鉴权。ShenYu 的原生 Shiro 管理路径委托发生在属性绑定之前；仅管理路径进入该强制过滤器。health details 在管理鉴权后可读；env/configprops 值始终 never，MCP 配置诊断仍默认关闭。记录仅含有界异常类型、Bean 标识和固定阶段码，原生日志/异常消息/堆栈均丢弃；Docker log driver 关闭。

额外的 `ChaosConfiguration` 是自编故障组件，不属于原生应用。它提供健康异常、实际 DataSource 连接池占满、缺失依赖/重复定义/构造器循环，以及 1000 个实际注册的 Spring Bean 和别名/依赖链。ThingsBoard 另暂停/恢复本轮私有 PostgreSQL。启动失败的异常类型来自运维启动器；Actuator 不可用时，MCP 只能报告 unavailable，不能声称自己诊断出了启动根因。

`production_fault_proxy.py` 是测试脚本内的固定 origin、固定 GET 端点代理，不是产品 URL 透传能力。它只在内存中处理本轮响应，模拟 401/403/302/429/500、HTML、重复键、非法 UTF-8、断流、超大包、延迟、父容器破损、健康 503、复杂引用和非法时间；每种异常后复测恢复。同一 SDK 宿主取消后复用；redirect / remote-ref 陷阱计数须为零。代理合成结构与原生业务证据分别标记。

每次工具结果检查公开输出 Schema、独立安全门和包含文本副本的完整 16 KiB JSON-RPC 预算。已知 LS-01 随机游标故障保留为失败；重跑成功不会擦除旧失败或证明该缺陷修复。退出时只删除本轮命名容器/匿名数据库卷/网络并停止 SDK 子进程，源码和安全聚合摘要保留。


## 已知失败与独立断言

[2026-10-23 审计](../../docs/audits/production-chaos-2026-10-23.md)记录 PC-01：健康详情的 `instructions` 被转换为 `name/value` 描述符后，现有安全门仍可能接受其中无空格的指令文本。脚本补充独立 canary 存在性断言，出现时保留 `REMOTE_INSTRUCTION_PASSTHROUGH`，不能把 `outputGuardPassed=true` 解释为指令已移除。`probe_production_chaos_findings.py` 完全离线复现工具到完整响应出口，退出 0 表示缺陷成功复现，不表示安全验收通过。此为首轮历史未修复状态；后续修复与最终复验见[修复报告](../../docs/audits/production-chaos-remediation-2026-10-23.md)。

DolphinScheduler 未暴露的迁移/OpenAPI 请求经原生错误安全链返回 401，本轮初始 404 预期属于装配错误；源清单已改为 401，历史失败记录保留，不能由 401 推断端点一定不存在。ThingsBoard 安装阶段使用 60 秒数据库 socket timeout 与 300 秒启动等待；运行期使用 2 秒 socket timeout。PostgreSQL 数据目录为 tmpfs，暂停/恢复保留该进程的数据；不验证持久性、重启后的数据保留或生产耐久性。


## 修复后复验

PC-01、PC-02、LS-01 的修复保持原目标、TTL、容量和回包预算，旧失败文件不覆盖。真实项目启动命令不变，建议输出至新的 `*-remediation.json`。离线探针用显式模式验证修复，输出至新文件：

```bash
uv run --no-sync python scripts/probe_production_chaos_findings.py --expect-repaired \
  --output /absolute/cache/production-chaos-remediation-probe.json
uv run --no-sync python scripts/probe_large_project_stability.py --expect-repaired \
  --output /absolute/cache/cursor-remediation-probe.json
```

`--expect-repaired` 退出 0 表示本次探针的修复条件满足；不带该参数仍使用历史“缺陷复现”退出语义。完整回归、原始失败与修复后安全聚合摘要见[修复报告](../../docs/audits/production-chaos-remediation-2026-10-23.md)。
