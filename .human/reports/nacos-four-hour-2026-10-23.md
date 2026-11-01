# Nacos 2.4.3 四小时生产模拟：功能、边界、架构、稳定性与可用性

日期：2026-10-23。目标：再次拉取一个随机抽取、有真实生产使用场景的热门
Spring Boot 项目，在本地循环回环和一次性数据库上模拟生产运行，完成四小时持续
MCP 调用、故障/恢复和资源记录。只访问自行启动的隔离目标，不接触生产 Nacos 集群，
不发布、不提交。

复现资产见 [examples/nacos-soak-matrix](../../examples/nacos-soak-matrix/README.md)、
[check_nacos_soak.py](../../scripts/check_nacos_soak.py) 和
[结果 JSON](../../examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.json)。
构建/补丁哈希见
[build evidence](../../examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23-build.json)。

## 选题与固定版本

在 Nacos、PowerJob、Sentinel 三个有真实生产采用、带 Spring Boot 运行时的热门候选
中用 `shuf -n 1` 随机抽取，选中 **alibaba/nacos**。GitHub 公开快照 33,471 stars
（2026-10-23），不是生产集群验收，也不代表完整版本矩阵。

| 项目 | 固定 tag / revision | 规模 | 原生 Boot | 运行时 |
| --- | --- | ---: | --- | --- |
| alibaba/nacos | 2.4.3 / `f4f8b189cf16186669de5b692d43630ed2c3fda2` | 2,391 Java 文件（1,526 main，22 个 Maven 模块） | 2.7.18 | Java 21 / MariaDB 11.2 |

构建使用 Maven 3.10.0、`-Prelease-nacos`，跳过上游测试、前端和发布装配。只构建
`console`/`distribution` 所需 reactor，未验证 UI、集群或安装器。

## 构建副本的 Hessian 变通

分布 jar 同时带 `com.alipay.sofa:hessian:3.3.6`（SOFA JRaft 传递）与
`com.caucho:hessian:4.0.63`（NacosHessianSerializerFactory 需要），在本机 JVM 上
3.3.6 先加载导致启动失败。运行器只复制 fat jar，并在副本中删除 3.3.6 及其
classpath 索引项；原始构建产物和源码均不改。

| 产物 | SHA256 | Hessian |
| --- | --- | --- |
| 原始分布 jar | `956d534d096455aaebb697e3e55b33b4b1b32530af7c036fc1915937677caae0` | 3.3.6 + 4.0.63 |
| 运行副本 | `b3eca64044b7d42892a06144b750ab9abbefd33b4c999d6ae9c15837b20eb74b` | 4.0.63 |

这是固定版本上的加载变通，不是生产建议；删除旧 Hessian 后 JRaft 快照序列化和
多节点一致性没有验证。

## 隔离与启动

- Nacos 只监听 `127.0.0.1`；业务端口和独立管理端口都是随机回环端口。
- MariaDB 11.2 一次性容器只发布到回环随机端口，使用上游
  `distribution/conf/mysql-schema.sql` 初始化 `nacos_config`；数据库密码通过进程环境
  变量给测试启动器，不写源码、属性文件、报告或日志。
- `NacosDiagnosticsLauncher` 启动原生 `com.alibaba.nacos.Nacos`，注入 8192 步
  `BufferingApplicationStartup`，让 `/actuator/startup` 可读。
- `DiagnosticManagementSecurity` 只在管理子上下文注册：匿名 401、普通 Bearer 403、
  管理员放行、非 GET/HEAD 405。业务端点鉴权在隔离副本中关闭，仅用于测试；
  全程不调用配置发布、服务注册、UI 登录或其他写路径。
- `env`/`configprops` 的 `show-values=never`，MCP 配置诊断仍默认关闭；所有 MCP
  响应继续经过 outputSchema、独立安全出口和 16,384 字节完整帧预算。

## 四小时执行与记录

运行窗口为 **2026-10-23T11:27:08.617Z 至 15:27:10.164Z**，实际 soak
**14,401.542 秒**（4 小时 1.5 秒），四路并发，每 60 秒采样，共 **240** 个资源样本。
MCP 宿主保持运行；目标按计划重启，数据库按计划暂停，不把故障窗口算作目标连续可用。

| 时间点 | 阶段 | 结果 |
| ---: | --- | --- |
| 30 min | 全量分页 + 六项边界 | 519 个可见 Bean，44 页穷尽 |
| 60 min | 目标停止/同宿主重启 | 10.0 秒恢复，启动 8.142 秒 |
| 90 min | MariaDB 暂停/恢复 | readiness 超时，首次检查恢复；Actuator UP |
| 120 min | 全量分页 + 六项边界 | 519 个可见 Bean，44 页穷尽 |
| 150 min | 目标停止/同宿主重启 | 10.6 秒恢复，启动 8.814 秒 |
| 180 min | MariaDB 暂停/恢复 | readiness 超时，首次检查恢复；Actuator UP |
| 210 min | 全量分页 + 六项边界 | 519 个可见 Bean，44 页穷尽 |
| 240 min | 游标过期、目标停止/重启 | 明确拒绝和恢复，最终退出 |

逐分钟记录见
本地 `examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.jsonl`（保留在磁盘并由 Git 忽略，不随仓库或分发包交付）
（SHA256 `3e1c5dd7fbcc4c3ca29e7445721a6a3b2be9316ec75219ba2070e23a1543fa0d`），
完整脱敏聚合见
[results JSON](../../examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.json)
（SHA256 `e4a5018e3ba368cb00185930d186d66fe19c32efbb33ed6d8fec6e70d4695f6d`）。

## 结果

| 指标 | 四小时结果 |
| --- | --- |
| 验收 | `accepted=true`，`failureCodes=[]` |
| 调用 | **68,260** 次真实 MCP 调用；soak 窗口 **68,189** 次 |
| 状态 | ok 25,525 / partial 42,708 / denied 2 / invalid 5 / unavailable 20 |
| 预期错误 | 401/403 `ENDPOINT_UNAUTHORIZED` 2；`INVALID_ARGUMENT` 5；`ENDPOINT_NOT_EXPOSED` 8；`CAPABILITY_DISABLED` 4；`CURSOR_QUERY_MISMATCH` 4；`CURSOR_EXPIRED` 1；`TARGET_CONNECTION_REFUSED` 3 |
| 非预期错误 | `{}`（空） |
| 延迟 | 中位 242.754 ms；p95 945.435 ms；最大 2,087.568 ms |
| 最大完整回包 | **15,242 字节**，低于 16,384 字节硬上限 |
| 基线分页 | 519 个可见 Bean / 52 页（maxResults=20） |
| 周期分页 | 3 次均为 519 个可见 Bean / 44 页（maxResults=50），无重复页/快照变化 |
| 启动 | 初始 6.878 秒；两次计划重启 8.142 / 8.814 秒；最终验收重启 9.859 秒 |
| 目标重启 | 2 次计划内停/起，恢复 9.964 / 10.623 秒；最终验收再停/起一次 |
| 数据库暂停 | 2 次，readiness 均超时约 5 秒；解锁后首次检查恢复；`actuatorObservedExternalDbOutage=false` |
| 清理 | 目标、MariaDB 容器、全部 MCP 子进程均停止；`databaseStopped=true` |

### 功能与边界

- 八工具发现、排序和四项风险注解通过；legacy 与 `2026-07-28` 两种 SDK 模式通过。
- 匿名 401、普通 Bearer 403、管理员正向读取；非法 `maxResults=0` 被拒绝。
- 游标查询绑定不匹配和 60 秒后过期均明确拒绝；没有把截断写成完整。
- 路由 `/v1/console/health/readiness`、health、startup 正向事实可读；startup 仍为
  `partial`，保留深度/时间线缺口。
- 配置诊断默认 `CAPABILITY_DISABLED`；OpenAPI 和迁移固定入口 404
  `ENDPOINT_NOT_EXPOSED`；Nacos 本身未暴露这些端点，未伪造为 ok。
- 漂移在 bean/route 预期上返回 partial，保留 `BEAN_INDEX_INCOMPLETE` 等图证据缺口，
  不把不可见写成不存在。
- Bean 图始终保留 `ASSOCIATION_LIMIT`、`BEAN_GRAPH_INCOMPLETE`、
  `NOT_FOUND_IN_COMPLETE_VISIBLE_HIERARCHY` 等缺口；分页完成由 519 个唯一 ID 与
  直接 inventory 对照确认，`totalMatched` 为 null 未被当成完整结论。

### 资源趋势

| 进程 | RSS 中位 / 范围 | FD | 线程 |
| --- | ---: | ---: | ---: |
| Nacos 目标 | 639,404 KiB / 90,508–1,025,304 KiB | 225–235 | 323–372 |
| MCP 宿主 | 77,746 KiB / 76,180–95,352 KiB | 7–8 | 22 |

- 目标 RSS 在一次重启后出现 90 MiB 的新进程启动样本，稳定期在 480–1,025 MiB 间随
  JVM GC 波动；没有按单点最低值宣称内存稳定。
- MCP 宿主 FD 全程 7（单次峰值 8），未出现随调用数单调增长；RSS 中位 77.7 MiB。
- soak 期间（排除目标停止窗口）直接 health 和 Nacos readiness 样本均为 200；目标停止
  窗口记录的 `ConnectionRefusedError` 是预期故障证据，不是通过项。
- 两次目标重启采样出现负 `cpuPercent`，原因是 PID 更换后仍沿用旧进程 CPU ticks；
  该字段不参与资源摘要和验收结论。

## 主要发现与限制

1. **Actuator 不能反映外部 MariaDB 故障**：Nacos 的 `db` health 显示内嵌 Derby；暂停
   外部 MariaDB 时 readiness 超时，但 MCP `diagnose_health` 仍可能返回 UP。报告保留
   `actuatorObservedExternalDbOutage=false`，不把 Actuator UP 当作外部数据库可用性证明。
2. 运行在 Nacos 2.4.3 固定提交、单节点 standalone、Java 21、MariaDB 11.2；没有验证
   集群/HA、Raft 多节点、鉴权插件、客户端长连接、配置发布、服务注册、告警或 UI。
3. Hessian 运行副本变通、管理 Bearer、独立管理端口、8192 步启动缓冲和业务鉴权
   关闭都是测试配置；JRaft 快照序列化未验证。
4. 四小时窗口包含计划内目标重启和数据库暂停；MCP 宿主连续运行，但目标不是单进程
   四小时不间断。分页、启动和漂移的 partial 是证据缺口，不是成功。
5. 最终 JSON 在复用工作目录时没有嵌入 `jarPatch` 元数据；原始/运行 jar 的 SHA256
   和删除项由独立 build evidence 记录，运行逻辑未改。
6. 延迟样本受四路 MCP 宿主 CPU 负载影响，不能作为 Nacos 或生产网络延迟基准。
7. 未执行 POST/PUT/PATCH/DELETE，未读取原始配置值、日志、heapdump 或业务响应正文。

## 验证

| 检查 | 结果 |
| --- | --- |
| 120 秒预检 | 667 次调用；功能/边界检查通过，但当时尚未把预期的 `ENDPOINT_UNAUTHORIZED` 归类，`accepted=false`。该分类随后修正，预检不作为正式通过 |
| 180 秒 `smoke-phases` | 904 次调用，包含分页、重启、DB 暂停，`accepted=true`，`failureCodes=[]` |
| 正式四小时 | **68,260 次调用**，`accepted=true`，`failureCodes=[]`，非预期错误为空 |
| 离线全量 | **999 passed**（44.03 秒） |
| 类型检查 | mypy 53 个源文件通过 |
| Lint/格式 | Ruff check 通过；Ruff format 检查 120 个文件已格式化 |
| 契约 | 8 个隔离 input/output Schema、144+ 合成断言通过 |
| 差异 | `git diff --check` 无空白错误 |
| 清理 | 目标、MariaDB、MCP 子进程均无残留；无发布、无提交 |

预检的 `accepted=false` 只来自预期的 401/403 错误码未加入白名单；修正分类后 180 秒
`smoke-phases` 和正式四小时均通过。没有弱化或删除失败断言，也没有把预检写成通过。

本次只新增测试材料、脚本和文档；没有修改生产 Python 代码、公开 Schema、运行依赖或
网络边界。