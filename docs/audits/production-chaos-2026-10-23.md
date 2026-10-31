# 生产采用项目与异常注入验收

日期：2026-10-23。承接 10-22 的用户授权：下载公开大型项目、修改可丢弃副本、编写异常用例，不限制流量。只访问本轮自行启动、固定登记的回环目标；没有访问任何组织的生产实例。

后续状态：用户已授权修复，结果见[修复与复验](production-chaos-remediation-2026-10-23.md)。以下保留修复前证据和当时结论。

## 结论

Apache ShenYu、ThingsBoard、Apache DolphinScheduler 的原生后端均完成构建并真实启动。测试包含原生数据库/连接池、自编 Spring 故障组件、固定端点的协议代理三个来源，不能混为实际生产事故记录。

本轮还记录 **PC-02：较大快照在绝对 TTL 内无法穷尽的可用性限制**。本轮新增确认 **PC-01：健康详情中的指令文本可经 name/value 描述符穿过脱敏与输出安全门**；原有 **LS-01：随机游标与安全门冲突**再次出现。不能给出全部安全、稳定性或可用性通过结论。没有修改生产分析算法、公开 MCP Schema 或 Python 运行依赖，上述修复或优化均未实施。

[机器聚合摘要](production-chaos-2026-10-23.json)、[PC-01 离线复现](production-chaos-findings-2026-10-23.json)、[构建与复现说明](../../examples/production-chaos/README.md)、[真实运行脚本](../../scripts/check_production_chaos.py)、[固定协议代理](../../scripts/production_fault_proxy.py)。默认离线回归仍为 **881 passed**；默认测试通过不能替代新增安全断言。

## 来源与实际范围

项目生产采用的公开一手证据分别为 [ShenYu 用户清单](https://shenyu.apache.org/users/)、[ThingsBoard / SenseING 案例](https://thingsboard.io/case-studies/senseing/)、[ASF DolphinScheduler 项目案例](https://news.apache.org/foundation/entry/asf-project-spotlight-apache-dolphinscheduler)。这些证据只用于选择项目，不证明此次测试等同于那些生产环境。

| 项目 / 固定 tag | 固定提交 | Boot / 构建 Java / 运行 Java | 主 Java 文件 |
| --- | --- | --- | ---: |
| ShenYu v2.7.1 | `218c5634ebffb1f0ce7e8ea921b85cd5a633cde7` | 3.3.1 / 21 / 21 | 2099 |
| ThingsBoard v4.2.1 | `292e6a36a120c2056a3c19b501d8245d9e6f2db0` | 3.4.10 / 21 / 21 | 3541 |
| DolphinScheduler 3.4.3 | `a190201acffa03d199d4ca216288734a6513de3d` | 2.7.11 / 17 / 21 | 1950（稀疏后端副本） |

文件数不是运行 Bean 数，也不宣称这些仓库源码均超过上一轮 Flowable 的 5525 个主 Java 文件。重点是增加生产采用组件、真实数据库及实际运行依赖图规模。DolphinScheduler 的主依赖 BOM 为 Boot 2.7.11，configuration-processor 为 2.6.1；按实际 classpath 与启动分析判断，未把根插件属性误当运行版本。

ShenYu 使用原生 admin/H2/Shiro。ThingsBoard 原生后端没有标准 Actuator，此次仅在临时 POM 添加可选 `runtime-diagnostics` profile，使用原生安装器创建独立 PostgreSQL schema 和系统数据，不加载 demo。运行 in-memory queue / Caffeine，关闭设备传输、edges、更新检查和外部发现；没有设备数据或业务任务。DolphinScheduler 使用上游 Standalone/H2/JDBC registry，加载原生 master/worker/API/alert 配置；这是开发装配，不是生产分布式集群验收，没有提交或执行工作流。

三者额外加载管理专用鉴权过滤器和 `ChaosConfiguration`。因此基线 Bean 数也包含少量运维测试组件，不是纯原版计数；额外 1000 个 Bean 是实际注册的 Spring 定义、别名及依赖链，不是伪造 Actuator JSON。

## 实测汇总

最终选取三项完整流程共 **399 次真实 MCP 调用**；不是无失败调用计数。

| 项目 | 调用数 | 基线 Bean / 依赖 | 加 1000 后 Bean | 可见分页 | p95 / 最大 ms | 最大回包字节 |
| --- | ---: | --- | ---: | --- | --- | ---: |
| shenyu | 118 | 699 / 957 | 1699 | 692/692 穷尽 | 1019.392 / 1953.365 | 14916 |
| thingsboard | 129 | 1280 / 5916 | 2280 | 370/1255 未穷尽 | 1912.413 / 3050.648 | 13340 |
| dolphinscheduler | 152 | 826 / 1557 | 1826 | 820/820 穷尽 | 1239.931 / 2120.73 | 13672 |

ShenYu 最终失败项为 PC-01；DolphinScheduler 保留一次 UNSAFE_OUTPUT 和两项已说明的原生 401/脚本 404 预期不符；ThingsBoard 两条连续分页链均 CURSOR_EXPIRED，未穷尽。DolphinScheduler 的重开分页链穷尽 820 个可见 Bean，但不清除第一次失败。三项基线均只有 1 个报告 Context。完整调用摘要分别见 [ShenYu](../../examples/production-chaos/results/shenyu.json)、[ThingsBoard](../../examples/production-chaos/results/thingsboard.json)、[DolphinScheduler](../../examples/production-chaos/results/dolphinscheduler.json)。

每项基线尝试连续遍历可见分页，ThingsBoard 未完成，返回预算可能把请求的每页 20 行进一步缩小。原始 Bean 名经安全投影后部分不可匹配，因此 totalMatched=null、partial 和图预算缺口保留；可见分页穷尽不等于完整原生依赖闭包。SourceCatalog 未登记，缺源条件继续 unknown/partial。

完整回包检查包含 structuredContent、兼容文本副本及元信息，均不超过 16384 UTF-8 字节。延迟包含分页、故障和恢复；项目与安装任务部分同时运行，本机曾出现明显磁盘等待，不用于跨项目性能排名或生产容量估计。本轮 SDK 真实故障矩阵使用 legacy；双协议与四路并发测试属于上一轮独立证据，没有把它们冒记为本轮新执行。

## PC-01（高优先级，未修复）

触发：远端健康详情的 `instructions` 标量进入 `normalize_health._scalars`，被投影为 `{"name": "instructions", "value": ...}`。当值采用不带空格的指令 canary 时，普通字符串识别可接受它；SanitizerPipeline 的描述符 taint 只检查凭据敏感名，不把此名称按不可信说明处理。输出安全门禁止的是字典键 `instructions`，没有在该描述符结构中识别同样的含义。

离线探针经过健康规范化、工具 finalizer、公开 outputSchema、独立安全门及完整响应序列化：状态为 ok，Schema 有效，安全门接受，最终回包仍包含指令 canary；同一输入里的已登记合成密码被正确移除。只持久化这些布尔证据和字节数，不保存工具原始结果、真实凭据或目标文本。

ShenYu 第 7 轮进一步通过官方 SDK 确认两次：额外健康组件异常、代理 HTTP 503 健康响应。两个结果均通过现有安全门，但新加入的独立 canary 断言将整轮标为 `REMOTE_INSTRUCTION_PASSTHROUGH`。第 6 轮 118 次调用在缺少该断言时曾 accepted=true；这个旧标志不足以证明无指令透传，原记录保留。ThingsBoard/DolphinScheduler 首轮完整矩阵发生在该新增断言之前，不能据其 `outputGuardPassed=true` 声称已移除指令。

此证据证明不可信文本透传，不证明下游 Agent 已执行其中内容或出现真实凭据泄漏。修复应在健康详情的字段投影与描述符上下文中阻断此类说明文本，并在出口独立检查；不能依赖逐条屏蔽该 canary，也不能把 OpenAPI 中合法的同名业务 Schema 属性一并删除。需要新增失败回归、保留凭据识别和预算守卫，再复验这两个真实 SDK 场景。本轮未修改生产实现。

## LS-01 与历史失败

ShenYu 第 5 轮及 DolphinScheduler 第 3 轮的完整分页各出现一次 `unavailable / UNSAFE_OUTPUT`，原失败标志保留，即使重新开始一条可见分页链成功也不会清除。上轮[确定性游标探针](large-project-cursor-probe-2026-10-22.json)已经复现本地随机句柄与编码敏感内容识别的冲突。未保存实测原始中间结果，不能逐条证明本轮每个同码失败都出自某个具体游标字段；现象与已知缺陷一致，不能宣称已修复。

DolphinScheduler 第 3 轮另有两个测试装配误判：未暴露的迁移和固定 OpenAPI 入口经过原生错误鉴权链返回 401，而初始脚本预期 404。源清单已改为实际 401，保留原报告，不把该预期错误归给 MCP 算法，也不把 401 推断成端点不存在。ShenYu 对这些入口返回 200 通用错误 JSON，MCP 正确拒绝为 MALFORMED_EVIDENCE；该目标的预期按结构不可解析登记，仍要求 data=null。

## PC-02（容量/可用性限制，未修复）

ThingsBoard 报告 1280 个 Bean、5916 条依赖，安全投影后有 1255 个可匹配 Bean。两次立即连续翻页分别得到 39 页/390 个、37 页/370 个后返回 CURSOR_EXPIRED，均未读全。每页请求 20，实际字节预算裁剪为 10；本轮调用 p95 为 1912.413 ms。失败没有被重开查询或修改 TTL 掩盖。

`SnapshotStore.deadline` 与 `finalize` 令后续游标继承初始观察的绝对 60 秒期限，符合当前契约；这不是“过期判断错了”。不过，`finalize` 每页仍处理完整未消费的尾部：脱敏、深拷贝、缓存序列化与再次安全验证；规模较大时，全量连续检索在本机无法在期限内完成。独立合成探针只有一次源读取、两页各 20 行，却记录到 1255/1235/1215 等完整余量参与脱敏；冻结时钟证明原始 60 秒后照常过期。探针没有做完整 CPU 归因，不能断言所有耗时都来自其中某一个函数；真实结果也受本机负载及客户端验证开销影响。

建议在保持绝对 TTL、32 MiB 缓存、16 KiB 回包、凭据更新后的复验和稳定快照的前提下，减少每页对整个剩余快照的重复处理；再用真实较大图复验。当前自愈方向是按稳定名称/类型收窄查询、重建新快照并明确新观察时间，不能把不同快照的页拼成一致全量结果。本轮没有延长产品 TTL 或弱化守卫。

## 已执行异常与证据来源

- 原生数据源：健康 UP；自编组件租满真实 Hikari 的两个连接后，原生 db 健康 DOWN；释放后 UP。ThingsBoard 另暂停/恢复本轮 PostgreSQL。私有数据目录使用 tmpfs，暂停保留数据；不验证持久性。
- 自编 Spring 启动故障：缺失依赖、同名定义冲突、构造器循环。启动器只记录异常类型和有界 Bean 标识。应用未启动时 MCP 返回 TARGET_CONNECTION_REFUSED / unavailable，不能声称 Actuator 诊断出了启动根因。恢复后的原生 db 再次可读，实际加载 1000 个额外 Bean 的末端节点可查询，并明确报告图预算 partial。
- 协议代理：401、403、302、429、500、HTML、重复 JSON 键、非法 UTF-8、声明长度大于实际断流、超过读取字节预算、延迟。逐个检查失败后在同一 SDK 宿主恢复读取；没有放宽任何产品连接器守卫。
- 合成证据代理：父 Context 自环和缺失父节点、健康 503、共享/循环/转义/远端 OpenAPI 引用、非法启动时间。保留 unknown/partial；redirect / remote-ref 陷阱读取次数为零。三项固定原生 OpenAPI 入口本轮均不可读取（ThingsBoard 实际 404，虽原生 POM 含定制 springdoc，未进一步证明未暴露原因）；OpenAPI 正向数据来自合成代理，不冒充原生 OpenAPI 正向兼容性。
- SDK 取消：确认慢请求已进入代理后取消调用，同一宿主随后恢复；这些检查不等于证明在途阻塞线程立即停止。匿名管理请求 401、低权限令牌 403。

## 装配阻塞与修正

保留每次失败摘要，不复制原生日志或堆栈。ShenYu 先后修正临时基础镜像的 JDK conf 链接、早期 Logback 路径、internal bridge 发布端口不可达、Shiro 过早绑定以及已知业务路由误写。最终第 7 轮改用标准 Temurin 21 镜像；第 6 轮是缓存 PostgreSQL 基础镜像加只读挂载主机 JDK/系统库的早期装配，不能描述成同一运行镜像。

ThingsBoard 修正原生前端插件的跳过参数；跳过 OS 包阶段后显式补回 build-info；切换原生安装 main 类；按原生数据目录布局装配 DAO SQL；安装阶段的 2 秒 socket timeout 太短，改为 60 秒；等待从 120 秒增至仅安装阶段 300 秒，运行期仍保留 2 秒数据库 socket timeout。临时 PostgreSQL 改用 tmpfs，避免把本机磁盘同步等待误当兼容性失败。

DolphinScheduler 全量浅克隆首次 RPC 失败，使用固定 tag 的稀疏后端副本完成；Java 21 编译触发原生 Lombok 1.18.20 的 JCTree 字段错误，使用本机 Java 17 构建，不覆盖其依赖版本；旧 Servlet 过滤器显式实现生命周期方法；运行 classpath 补上原生 standalone/conf。上游测试、UI 和 OS 发布包均未验证。

## 离线验证、隔离与限制

- `uv run --no-sync python -m pytest -q`：881 passed，43.42 秒。
- `uv run --no-sync python -m mypy src/spring_runtime_mcp`：53 个源文件通过。
- Ruff check / format：108 个 Python 文件通过。
- 契约：8 组工具 Schema，144+ 合成断言通过。
- PC-01 离线调查退出 0 表示成功复现缺陷，不是安全测试通过。

临时应用根文件系统只读，仅本轮控制文件和 tmpfs 可写；应用只向宿主 127.0.0.1 发布管理端口，数据库不发布宿主端口。独立 bridge 不是完整出网沙箱；关闭原生外部客户端不等于验证所有可能路径的零出网。凭据只在内存/环境传递，properties 使用占位符；Docker 禁用日志持久化，框架日志关闭，其余启动输出丢弃，仅保存安全类型/标识。没有任意 URL 透传、目标写 HTTP 请求、heapdump、原始日志或配置值树读取。

三项最终报告均确认本轮命名容器停止；部分早期装配报告尚未记录清理字段，不能补称当时逐次验证。最终独立核查没有残留 `runtime-chaos-*` 容器或网络，SDK 子进程均退出。未删除其他工作区或用户容器。

源码和安全摘要保留在 `~/.cache/spring-runtime-mcp/production-chaos-20261022`。没有提交、推送、发布或部署，也没有更改既有用户业务工作区。没有验证真实生产规模数据、全版本矩阵、分布式部署、长期资源泄漏、远程 TLS、UI、设备流量、工作流和业务写路径；有限故障矩阵不能代表所有生产异常。
