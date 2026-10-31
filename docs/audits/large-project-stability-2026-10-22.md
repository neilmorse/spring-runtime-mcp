# 大型公开项目：健壮性、稳定性与可用性验收

日期：2026-10-22。用户明确授权继续下载更大型项目、修改临时副本并进行真实运行测试，不限制流量。
源码保留在 `~/.cache/spring-runtime-mcp/large-matrix-20261022`；全部目标和 MCP 子进程已停止。
本轮只增加验收脚本、外部启动配置、离线调查探针和证据，未修改生产诊断算法、公开工具 Schema 或运行依赖。

## 结论

三项固定提交的原生服务模块均构建成功，并以 Java 21 在随机回环端口启动。
最终完整验收共 **1748 次真实 MCP 调用**，每项覆盖四路并发、全链可见 Bean 分页、游标过期、
鉴权和目标重启恢复。Data Flow 与 Admin 在并发 startup 调用中各出现一次 `UNSAFE_OUTPUT`；
Flowable 前一轮分页也出现同码错误，最后一轮 637 次调用没有再出现。
因此本轮**不能给出无缺陷稳定性结论**，也不能用 Flowable 最后一轮通过覆盖此前失败。

独立离线探针已确定一项未修复的缺陷：本地随机游标可能被后续输出安全门拒绝。
所有观察到的错误均安全失败，没有放行不安全内容；现有默认离线测试仍为 **881 passed**。

机器摘要：[完整有界聚合](large-project-stability-2026-10-22.json)、
[游标调查](large-project-cursor-probe-2026-10-22.json)。
复现入口：[配置、启动与构建说明](../../examples/large-project-matrix/README.md)、
[真实验收脚本](../../scripts/check_large_project_runtime.py)、
[离线调查脚本](../../scripts/probe_large_project_stability.py)。

## 固定项目和实际规模

| 项目 | 固定提交 | 原生 Boot | 主 Java 文件 | Actuator Bean / 依赖 / Context |
| --- | --- | --- | ---: | --- |
| Flowable 7.2.0 | `11a1cf83a8c03e343040b4d8edc751f9534d7323` | 3.5.4 | 5525 | 484 / 569 / 1 |
| Spring Cloud Data Flow 2.11.5 | `aded769567a338ee32c1606ab78ec848e89d3b4e` | 2.7.18 | 1110 | 638 / 858 / 2 |
| Spring Boot Admin tag 4.1.3 | `9d667167671483d93c1265545c68c0c6d6618405` | 4.1.1 | 242 | 368 / 443 / 1 |

源码文件数按整个固定仓库的主 Java 目录统计；不代表所有模块或类都进入被测进程。
Flowable 仓库明显大于前轮应用，但其实际暴露的 Bean 数少于前轮 JHipster 的 544；
Data Flow 此次暴露 638 个 Bean。Admin 是 Reactive 技术栈补充，不宣称其规模更大。
Admin 的 tag 中 reactor revision 本身是 `4.1.3-SNAPSHOT`，保留原样。
Context 数是 beans 端点实际报告的数量；独立管理端口不保证端点必然报告独立管理 Context。

原始代码来源：
[Flowable](https://github.com/flowable/flowable-engine/tree/11a1cf83a8c03e343040b4d8edc751f9534d7323)、
[Data Flow](https://github.com/spring-cloud/spring-cloud-dataflow/tree/aded769567a338ee32c1606ab78ec848e89d3b4e)、
[Admin](https://github.com/codecentric/spring-boot-admin/tree/9d667167671483d93c1265545c68c0c6d6618405)。

## 真实测量

以下为每项最后一轮完整流程；保留此前独立失败作为历史证据。

| 项目 | 总调用 / 并发阶段调用 | 可见 Bean / 页数 | p95 / 最大耗时（ms） | 最大完整响应（字节） | 该轮验收 |
| --- | ---: | ---: | ---: | ---: | --- |
| Flowable | 637 / 570 | 481 / 48 | 915.221 / 1257.365 | 14112 | 通过有限检查；历史分页失败仍有效 |
| Data Flow | 510 / 428 | 632 / 63 | 1169.634 / 1822.481 | 15332 | 失败：一次 startup `UNSAFE_OUTPUT` |
| Admin | 601 / 546 | 362 / 36 | 1137.321 / 1474.362 | 14936 | 失败：一次 startup `UNSAFE_OUTPUT` |

每项四个 worker，持续发起调用约 90 秒，等待在途调用及进度轮询结束后的测量时长约 100 秒。
并发组合为已知 Bean、原生路由、健康和启动分析。延迟统计包含该轮基线/分页/错误/恢复调用，
且 Data Flow/Admin 同时运行，最后 Flowable 主要单独运行；这些是本机观察值，不是跨项目性能排名。
完整响应测量包含 structuredContent、兼容文本副本、serverInfo 元信息及最长 request id，均小于 16384 字节。

| 项目 | 宿主预热后 → 并发结束 RSS（KiB） | FD | 原生启动 / 重启（秒） |
| --- | ---: | --- | --- |
| Flowable | 86164 → 100596 | 7 → 7 | 5.258 / 5.302 |
| Data Flow | 89960 → 100080 | 7 → 7 | 10.898 / 7.048 |
| Admin | 81892 → 94108 | 7 → 7 | 6.333 / 3.170 |

三项 MCP 宿主在并发结束后仍存活；目标停止时返回 `TARGET_CONNECTION_REFUSED`，
原目标在同端口重启后，同一个 MCP 宿主重新读到已知原生 Bean。所有被跟踪的 MCP 进程均已退出，
目标进程均由清理逻辑停止。上述短时 RSS 增量不构成长期内存泄漏或无泄漏证明。

## 已确认缺陷 LS-01（P2，未修复）

位置：[`SnapshotStore.put`](../../src/spring_runtime_mcp/snapshots.py#L96)。
生成逻辑只检查 `secrets.token_urlsafe(32)` 的唯一性，随后直接登记并返回游标；
[`SanitizerPipeline.high_risk`](../../src/spring_runtime_mcp/policy/sanitization.py) 会递归解码编码候选，
[`ensure_safe_output`](../../src/spring_runtime_mcp/policy/output_guard.py) 又在缓存/完整响应出口进行独立检查。
随机字节的解码结果可能偶然呈现 userinfo 等敏感形状，从而拒绝本地生成的句柄。

离线确定性探针用运行时构造的合成字节替换随机生成结果：存储接受句柄，完整响应出口确定返回
`UNSAFE_OUTPUT`。不打印或持久化句柄和解码内容，不绕过安全门。
另一次独立随机抽样中，10000 个候选有 43 个被同一检查拒绝；这只是该次样本，
**不是全部工具调用错误率**。一次多页查询会生成多个游标，错误也可能出现在分页链中途。

真实证据：Flowable 第二次纯运行依赖验收在第 41 次调用时，于 `full-bean-page` 收到
`unavailable / UNSAFE_OUTPUT`，分页中断；Data Flow 和 Admin 最终并发轮的
`soak-analyze_startup` 各收到同码错误，数据为空。此前 Data Flow 第一轮并发也有一次同码错误，
当时仅有聚合计数，没有记录具体工具，因此不为它补造工具归属。
未保存失败调用的原始中间结果，不能逐条证明每个实测 `UNSAFE_OUTPUT` 都来自同一字段；
随机句柄与安全门冲突本身已被独立确定复现，且与这两类需要分页的调用一致。

建议的修复边界：在登记游标前，用该宿主的同一个 SanitizerPipeline 检查候选并做有界重新生成；
保留唯一性、凭据识别、TTL、容量预算和出口安全门。候选全部失败时返回明确错误，避免留下无法交付的缓存条目。
后续回归须覆盖“首个候选被拒绝、下一候选可交付”和“持续拒绝时有界退出”，再复验真实长分页。
本轮未应用该生产修复，未弱化安全测试。

## 已验证行为与证据边界

- 八工具按字母序发现、四项风险注解、outputSchema 和独立安全门均逐调用检查。
  官方 SDK `legacy` 与 `2026-07-28` 模式均完成已知 Bean 正向读取及非法参数拒绝。
- 三项匿名读取均被 401 拒绝，非管理员令牌均被 403 拒绝。
  Flowable 保留原生业务 Basic 安全链；Data Flow 使用管理路径专用 Servlet Filter；
  Admin 保留 secure profile，不启用原生 insecure profile。
- 分页无重复、快照一致，可见标识计数与内存中的安全投影计数一致，游标链能走到末端。
  请求每页 20，响应预算可能进一步缩小页大小。脱敏后分别少 3/6/6 个可匹配 Bean；
  因此三项 `totalMatched` 均为 null、coverage 为 partial，不能把可见行数当成完整原生总数。
- `CURSOR_QUERY_MISMATCH` 和超过 60 秒后的 `CURSOR_EXPIRED` 均实际观察到；
  拒绝后仍能进行新查询和目标重启恢复。
- 原生 Bean/路由、条件补充读取、健康、启动信息、默认配置关闭及跨域漂移检查均执行。
  Flowable 最终数据库健康有完整可见证据；Data Flow 聚合健康仍有
  `HEALTH_DETAILS_NOT_VISIBLE`，单独授权的相同配置探针确认 `db` 组件已观察且 UP，
  这不表示其他组件详情完整。
- Data Flow 原生 Flyway 已应用迁移被观察到。Flowable/Admin 没有本轮可读的标准迁移端点。
  三项均未增加 OpenAPI 依赖：Admin/Data Flow 固定文档入口 404，Flowable 未暴露入口经原生错误安全链返回 401。
  这是明确不可读取的负向验收，不新增真实 OpenAPI 正向兼容性结论。
- `REDACTED_IDENTIFIERS`、`NOT_FOUND_IN_COMPLETE_VISIBLE_HIERARCHY`、`GRAPH_LIMIT_REACHED`、
  `STARTUP_NODE_LIMIT`、`STARTUP_DEPTH_LIMIT`、`STARTUP_ORPHAN_STEP` 等真实 coverage gaps 保留在摘要。
  本轮未登记 SourceCatalog，缺失条件的未知语法与源事实不足继续 unknown/partial。
  这些结果不计作完整依赖闭包或完整启动时间线。

## 测试装配修正和历史失败

初始 Maven 类路径命令误用了 `mdep.includeScope`，测试依赖混入运行路径，
导致 Data Flow 额外客户端尝试访问默认本地服务并连接失败。
改为正确的 `includeScope=runtime` 后重新构建和验收，旧结果不作为兼容性结论。
Flowable 仅补回其原生 WAR 内 `lib-provided` 的三个 Tomcat jar。
没有替换项目 POM、降级 Boot、添加替代业务处理器或修改 Maven 缓存。

另外修正了运维装配中“同端口配置 management.server.address”、
旧版 `WebSecurityConfigurer` 与独立链冲突、Flowable 空 role prefix、
空 OpenAPI 查询参数、以及新协议首次通信前读取 PID 的竞态。
最初脚本把 `totalMatched=null` 当作分页失败，也已改为检查完整可见集合并保留 partial。
这些都属于测试装配问题，与 LS-01 分开记录。
新脚本在分页失败时保留失败，可重新开始一次查询继续完成独立检查；重试成功不会清除失败标志。

## 实际离线检查与限制

- `uv run --no-sync python -m pytest -q`：**881 passed，38.02 秒**。
- `uv run --no-sync python -m mypy src/spring_runtime_mcp`：53 个源文件通过。
- `uv run --no-sync python scripts/validate_tool_contract.py`：8 组工具 Schema、144+ 合成断言通过。
- Ruff check / format：105 个 Python 文件通过。
- 已安装入口的官方 SDK 两种模式发现/工具错误检查通过。
- 游标离线探针退出 0 代表成功复现缺陷，绝不表示缺陷修复。

真实测试与默认离线测试分开；默认 pytest 未引入下载、外部项目或业务目标。
本轮未新增运行依赖、修改公共 Schema、构建本项目发行包、提交、推送或发布。
上游 Maven 构建跳过上游测试，不宣称其测试通过。Data Flow 的原生依赖版本范围不是完整依赖锁。
没有覆盖 UI、完整 Data Flow streams/调度/部署、工作流执行、外部消息中间件、生产数据库、容器平台、
远程 TLS 或全天候压力运行；也不声明完成整个 Spring Boot 版本矩阵。
