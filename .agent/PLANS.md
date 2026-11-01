# 2026-10-22 综合审查修复与 TDD 真实验收

目标：修复 docs/audits/comprehensive-review-2026-10-22.md 中 CR-01 至 CR-13，补齐与本轮有关的工程交付缺口，并使用 `<TDD checkout>` 的真实 Shop 应用独立验收。

边界：公开工具 Schema、八工具排序、只读和脱敏约束保持；不发布、不扩大回环目标边界。TDD 的任务文件和看板业务代码为用户改动，保留；真实隔离方案已获明确批准，不重复请求。

1. [完成] 已准备并校验诊断 profile/隔离方案；用户明确批准新增可选 Actuator、JWT 回环实例和临时 PostgreSQL，已应用仅 Maven profile 补丁。
2. [完成] 统一 Services/诊断信封与调用预算；SDK 最终工具帧、ID、两个读取槽和总时限均有回归。
3. [完成] 修复 OpenAPI 组合、包装引用、3.0/3.1 语义和未知结构/方言降级。
4. [完成] 修复迁移证据/校验和/应用状态、Bean 遮蔽及健康可见性；离线回归通过。
5. [完成] 修复进程测试时序和发布门禁；补齐 py.typed、uv.lock 与当前文档。
6. [完成] 离线全量 782 passed，类型 51 文件及契约/lint/格式通过。隔离安装官方 SDK 两种模式通过。原 TDD 红阶段缺 DashboardService 实现 Bean，改用提交 b7c54641 的临时副本完成 Boot 3.5.16/JWT/PostgreSQL 验收；原工作区仅新增已批准 pom profile。
7. [完成] 综合修复报告已写入；最终 wheel/sdist 资源及安装来源验证通过，官方 SDK 两种模式通过；本地文档链接和差异检查通过。临时源码、classpath、进程和本轮数据库容器均已清理；未发布。

# 2026-10-22 较大公开项目真实诊断矩阵

授权：用户要求增加稍大型项目，不再限制流量；沿用可修改临时副本、启动隔离实例的授权。
只使用回环监听和临时数据库/合成凭据，不发布，不连接既有业务数据；默认 tests 仍保持离线。
保留当前 WebFlux 修复及其他未提交改动。临时项目根位于 `/tmp/spring-runtime-projects-QIYBYhaR`。

1. [完成] 固定三个项目提交，检查原生构建、业务启动配置和安全链。主 Java 文件分别 30/87/81。
2. [完成] 保留 Boot 4.1.0/4.1.1 原生 POM 与依赖，三个项目编译成功；配置随机回环监听、内存 H2 和缓冲启动。JHipster 仅同步管理命名空间的两处规则，JWT 管理员限制保留。
3. [完成] 主矩阵保存 43 次调用：Petclinic 13 次通过；REST 15 次中两个复杂 OpenAPI 检查失败、简单 Schema 通过；JHipster API-docs 变体启动阻塞，关闭该 profile 的补充变体 15 次通过，含 401/403 与 8 条 APPLIED Liquibase。
4. [完成] examples/project-matrix 保存原失败、最终矩阵、启动因果类型、精确命名空间补丁及复现说明；独立合成探针复现共享引用输出别名和 description 属性 Schema 清空，未修改核心算法或公开 Schema。
5. [完成] Ruff、mypy 与契约通过；默认全量 816 passed。目标进程均由 finally 停止，最终核查不遗留实例；只用内存数据库，无本轮 Docker 容器。未发布。

# 2026-10-22 较大项目缺陷修复

授权：用户明确要求开始修复，沿用临时副本和隔离实例授权；保留初轮失败与此前未提交改动。

1. [完成] 新增合成回归，复现共享引用的可变数组别名及 description 属性 Schema 冲突；不复制真实目标响应。
2. [完成] 修复独立、有界且消耗共享预算的元数据投影；脱敏器和输出门区分业务属性名与说明字段，保留全部安全守卫。
3. [完成] Petclinic REST 原生构建的 15 次复验通过，复杂 OpenAPI 返回有效数据及显式 partial 缺口，原失败记录不覆盖。
4. [完成] 根据已安装字节码和同版本源码定位 JHipster 分组的过早初始化；保留原配置失败，新增原生 API-docs/JWT/Liquibase 同端口方案，18 次验收含 Bean/OpenAPI 的 401/403。
5. [完成] 全量 837 passed，mypy、Ruff、契约及独立探针通过；修复报告、独立摘要和复现说明已补齐。独立管理端口的第三方初始化故障及此前五项独立审查问题仍未修复；未提交、未发布。

# 2026-10-22 遗留原因研究

用户要求研究未修复原因；本轮不实施生产算法/依赖修复。

1. [完成] 离线合成探针复现五项已知缺口；记录具体代码原因、覆盖缺口及现有契约内的修复方向；明确此前属于范围遗漏，不是授权/技术阻塞。
2. [完成] 三个无网络 Spring 生命周期对照定位分组实例过早创建；按定义查询的对照成功，未声称完整第三方补丁验收。
3. [完成] 真实 JHipster 独立端口关闭 Actuator 文档收集后成功启动；六次定向读取确认分组 Bean 存在，但固定文档入口 404，保留第二层集成缺口。
4. [完成] 调查报告和有界摘要保存；64 项定向回归、mypy、Ruff 通过；进程由 finally 停止；不提交、不发布，不将预期失败记作通过。

# 2026-10-22 遗留问题闭环修复

用户明确要求开始修复，包含五项本项目缺口和 JHipster 独立端口链路；保留所有历史证据与用户改动。

1. [完成] 新增 44 个合成回归，统一严格时间解析和未知证据处理，修复 OpenAPI PathItem、方言作用域与计数；原五项探针不再复现。
2. [完成] 准备固定源码哈希的 springdoc 三文件补丁，四个真实处理器对照通过；原缓存 jar/POM 不改，编译依赖不进入运行时。
3. [完成] 全量 881 passed，mypy 53 文件、Ruff、契约及两个旧探针通过；JHipster 实际独立端口 18 次、原生 REST 15 次通过，原失败摘要保留。
4. [完成] 闭环报告、复现脚本及限制补齐；目标进程 finally 停止；不提交、不发布，不声明未打补丁的上游或完整版本矩阵已修复。

# 2026-10-22 大型公开项目稳定性矩阵

授权：用户继续要求拉取更大型公开项目，验证健壮性、稳定性与可用性；沿用临时副本、隔离启动和无流量限制授权。
保留所有既有补丁；源码/构建放在 `~/.cache/spring-runtime-mcp/large-matrix-20261022`，不占用 tmpfs。

1. [完成] 固定 Flowable 7.2.0、Data Flow 2.11.5、Admin 4.1.3 提交并审阅后台任务；分别有 5525、1110、242 个主 Java 文件，Admin 用于 Reactive 多样性。
2. [完成] 三项原生模块构建成功并在 Java 21 回环启动。纠正 Maven includeScope 参数，排除测试依赖；Flowable 仅补回其原生 WAR 的 lib-provided 容器。临时 H2、管理专用 Bearer、禁用对外客户端/流程任务，未更换原生 POM/Boot 版本。
3. [完成] 最终三项共 1748 次真实调用，完成全链可见分页、四路约 100 秒并发、60 秒游标过期、两协议与同宿主停止/重启恢复；保留 Data Flow/Admin startup 和 Flowable 历史分页的 UNSAFE_OUTPUT。离线确定复现随机游标与安全门冲突，作为 LS-01 未修复缺陷，不改生产算法或绕过守卫。
4. [完成] 聚合摘要、验收脚本、调查探针和复现说明落盘；881 passed、mypy 53 文件、Ruff 105 文件、契约及两协议入口检查通过。目标与 MCP 子进程停止，源码缓存保留，不提交、不发布。

# 2026-10-22 至 10-23 生产采用项目与故障注入矩阵

授权：用户要求继续拉取更大型、有真实上线记录的公开项目，并自行编写用例/临时修改来模拟生产异常；沿用无流量限制、隔离副本启动和临时数据库授权。只访问自行启动并登记的回环诊断目标，不接触他人生产实例。保留现有补丁，不以屏蔽失败来验收。

1. [完成] 一手资料核实采用证据，固定 ThingsBoard 4.2.1、ShenYu 2.7.1、DolphinScheduler 3.4.3 提交；主 Java 分别 3541/2099/1950（后者稀疏后端），不宣称都比 Flowable 源码更大。
2. [完成] 三项原生后端构建/启动。ThingsBoard 临时 profile 添加原生 BOM 管理的 Actuator，原生安装器装配私有 PostgreSQL；DolphinScheduler 以 Java 17 构建、Boot 2.7.11 Standalone/H2 在 Java 21 运行，明确非生产集群。修正和保留所有装配失败摘要。
3. [完成] 最后三项 399 次真实 SDK 调用，连接池耗尽、PostgreSQL 暂停恢复、三类启动失败、额外 1000 个真实 Bean、固定协议异常/坏图/复杂引用/敏感 canary 与取消恢复均执行。未在本轮重跑上一轮四路并发和双协议矩阵，未声称默认离线用例包含真实项目。
4. [完成] 独立确认 PC-01 健康详情指令透传，真实 ShenYu SDK 两次及离线完整响应出口复现；ThingsBoard 两次分页均在 60 秒原始 TTL 内未穷尽，记录 PC-02 规模可用性限制及合成工作量证据。保留 ShenYu/DolphinScheduler 的 UNSAFE_OUTPUT 与上轮 LS-01，不实施生产算法修复、不弱化守卫。881 passed，mypy 53、Ruff 108、契约通过；报告/完整安全聚合/脚本落盘，最终无本轮容器或网络、SDK 子进程退出。保留源码缓存，不提交或发布。

# 2026-10-23 生产故障矩阵问题闭环

用户要求调研并修复 PC-01、PC-02 及 LS-01；保留历史失败和既有工作树修改。沿用临时副本/数据库/重启授权，不改公开 Schema、依赖或网络边界。

1. [完成] 首轮 16 项失败回归明确复现，最终新增 28 个合成回归；涵盖描述符指令/异常/编码标签、随机游标候选拒绝/碰撞、分页工作量与共享缓存安全边界。
2. [完成] 字段上下文脱敏与独立出口；句柄登记前 16 次有界校验；共享不可变编码分页快照，按页解码/校验。缓存只存不含明文凭据的策略戳，凭据变化后整快照复验并清理全部句柄，保留 60 秒绝对 TTL 与 32 MiB 上限。
3. [完成] 最终 909 passed / 32.11 秒、mypy 53、Ruff 109、契约与两探针通过。编码标签及缓存策略戳最终加固后再次运行三项真实矩阵，425 次调用通过；ThingsBoard 首次 125 页穷尽 1255 个可见 Bean，三项原生与代理 canary 均未透传，预期故障后恢复。较早的一轮修复复验独立保留。
4. [完成] 修复报告、新旧安全摘要与哈希落盘，调用策略文档和变更记录更新。最终无本轮自有容器/网络、MCP 子进程退出；源码缓存保留，不提交或发布。不扩大生产稳定性、完整版本矩阵或任意语义提示注入免疫的结论。

# 2026-10-23 超大型生产系统：Fineract

用户要求自行拉取超大型项目，在本地离线模拟线上生产环境做功能、稳定性和可用性测试。只使用临时副本、回环监听和一次性 PostgreSQL，不接触生产实例，不执行写请求。

1. [完成] 拉取 Apache Fineract 1.9.0 固定提交 `5d96e8cc32ff63f97d5ac15e19c6fafee0c31357`（4565 个 Java 文件 / 4087 个主 Java），Java 17 + Boot 3.1.7，Gradle 8.5。临时副本仅在 `pluginManagement` 增加公共镜像以解析已停用 JCenter 的文档插件依赖；运行时 Boot/BOM/驱动不变。
2. [完成] 新增 `examples/ultra-project-matrix/`、Fineract 反射启动器、管理专用 Bearer 过滤器、一次性 PostgreSQL 和 `scripts/check_ultra_project_runtime.py`。原生 `application.properties` 保持可见，外部配置改走 `ultra.properties` + 命令行参数，避免 classpath 遮蔽。
3. [完成] 发现并修复 `springboot_verify_mappings` 对 JAX-RS/Jersey 路由的假阴性：Actuator mappings 的 `servlets` 显示 `/api/*` 由 Jersey ServletContainer 覆盖，旧实现却返回 `ok/complete` 空结果。新增 4 个回归，路径可能由非 DispatcherServlet 覆盖时返回 partial、unknown total 和 `NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED`。
4. [完成] 正式 300 秒运行 `accepted=true`、1202 次调用；252 页穷尽 2524 个可见 Bean；最大回包 15,170 字节；数据库暂停后降级、Bean 读取仍可用、恢复后 UP；目标停止/重启恢复；JAX-RS 路由 partial/gap。审计报告、脱敏聚合、README/SPEC/HANDOVER/CHANGELOG 已更新；全量 913 passed、mypy 53、Ruff 111、契约通过。首轮全量有 1 个 STDIO 进程测试在重负载后失败，单独及第二次全量通过，保留为时序波动。未提交、未发布；目标/数据库/MCP 进程全部清理。

# 2026-10-23 小众生产项目：HertzBeat

用户要求再拉取一个规模适中、偏小众但真实生产使用的项目，继续做本地隔离功能、稳定性和可用性验收。只用临时副本、回环 H2；不连接生产监控目标。

1. [完成] 拉取 Apache HertzBeat v1.7.3 固定提交 `67ad4b04ef1b06b62f0e5030a26d0ca069294fa3`（1387/975 个 Java），Java 17 + Boot 3.4.2 + Maven + 内嵌 H2；构建 manager 及 reactor 依赖，跳过上游测试/UI/发布装配。
2. [完成] 新增 `examples/niche-project-matrix`、纯 Servlet 管理 Bearer Filter、Sureness `/actuator/**===*` 前置配置、2048 步启动缓冲和 `scripts/check_niche_project_runtime.py`。首次关闭 Spring AI MCP server 导致 `webMvcSseServerTransportProvider` 缺 Bean，保留原生启用且不调用外部模型。
3. [完成] 快速验收 415 次调用通过；正式 300 秒 **1594 次调用 `accepted=true`**：875 个 Bean / 1167 条依赖、873 个可见 Bean / 87 页穷尽、Flyway 5 条 APPLIED、路由/db 健康 ok/complete、启动/漂移显式 partial、最大回包 15,072 字节、目标重启恢复、MCP 子进程退出。
4. [完成] 审计报告、脱敏聚合、README、CHANGELOG 和计划记录落盘；未修改生产 Python 代码，未提交、未发布；H2 临时数据保留在缓存副本。

# 2026-10-23 小型生产调度器：XXL-JOB

用户要求继续找项目适配。本轮选中真实生产使用的 XXL-JOB v3.4.0，规模小但保留 Boot 4、SSO、MyBatis/MariaDB、Actuator。

1. [完成] 拉取固定提交 `555b48f2edf0e51cd77971565342d80c15c9f18d`（157/136 个 Java），Java 17 source / Java 21 runtime、Boot 4.0.5、MariaDB 11.2；构建 admin/core，跳过上游测试/UI/执行器。
2. [完成] 新增 `examples/xxl-job-matrix`、纯 Servlet 管理 Bearer Filter、`xxl-sso.client.excluded.paths=/actuator/**`、2048 步启动缓冲和 `scripts/check_xxl_job_runtime.py`；由于原生 logback 在 Boot 配置前写 `/data/applogs`，用 classpath 前置 root OFF 的 `logback.xml` 遮蔽。
3. [完成] 快速验收 575 次调用；正式 300 秒 **2449 次调用 `accepted=true`**：356 个 Bean / 402 条依赖、35 页穷尽、路由/db 健康 ok/complete、启动 partial、迁移 404 负向、MariaDB 暂停 DOWN 后恢复、最大回包 15,638 字节、目标/数据库/MCP 全部清理。
4. [完成] 审计报告、脱敏聚合、README、CHANGELOG、HANDOVER/SPEC 和计划记录落盘；未修改生产 Python 代码，未提交、未发布。

# 2026-10-23 交付前六维总核验

用户要求按功能闭环、边界防御、安全脱敏、测试真实性、净室构建、文档与版本一致性做交付前核验；只做离线与本地净室检查，不启动真实诊断目标，保持只读边界和未发布状态。

1. [完成] 生产代码无 TODO/FIXME/HACK/XXX、`NotImplementedError` 或调试断点；八工具全部绑定 `HANDLERS`；第三方导入仅 `mcp`、`jsonschema` 且均已声明；配置诊断默认关闭并返回 `CAPABILITY_DISABLED`。
2. [完成] 修复 `--source-catalog` 无界读取：仅接受常规文件并按 256 KiB 分块读取；CLI 启动错误改为按参数给出具体且不含值的提示；新增 `--version`。HTTP 超时、分页/截断、游标 60 秒/32 MiB、双读取槽、连接关闭与 15 秒总预算复核通过。
3. [完成] Git 33 个提交全历史与工作区凭证扫描只命中原有合成测试向量；私网 IP 命中为 SSRF 测试地址和 `derby-10.14.2.0.jar` 版本号误报；日志/STDOUT/路径遍历/出口守卫复核通过。pytest 8.4.2→9.0.3 关闭 PYSEC-2026-1845，`uv audit` 40 包无已知漏洞。
4. [完成] 新增 9 个 CLI/版本回归，全量 **922 passed**，无 skip/xfail；Mock 仅用于网络隔离、时钟和故障注入；E2E 走真实处理器与 STDIO 子进程。mypy 53、Ruff 113、契约通过。
5. [完成] wheel/sdist 无缓存、`target/`、jar；全新 venv 从 wheel 与 sdist 安装，`--version`、两种 MCP 协议和安装包内 replay 通过；`uv lock --check` 通过。
6. [完成] README/README.zh-CN/SPEC 增补 `--version`；HANDOVER/CHANGELOG 更新；`__version__`、wheel 元数据和 CLI 输出均为 0.2.0；Git 无标签，未提交、未发布。

# 2026-10-23 热门生产项目：Nacos 四小时持续运行

用户要求再次拉取项目，随机抽取 GitHub 上符合当前 MCP 要求、有真实生产场景的热门项目，
在本地离线模拟生产环境做功能、边界、架构、稳定性和可用性测试，并维持四小时持续运行测试
与记录。只用临时副本、回环端口和一次性 MariaDB；不接触生产集群，不发布。

1. [完成] 用 `shuf -n 1` 从 Nacos、PowerJob、Sentinel 候选池随机选中 alibaba/nacos；
   固定 2.4.3 / `f4f8b189cf16186669de5b692d43630ed2c3fda2`（33,471 stars；2,391 Java
   文件，1,526 main，22 个 Maven 模块；Boot 2.7.18）。
2. [完成] 原生 release 构建成功；一次性 MariaDB 11.2 与 `mysql-schema.sql` 初始化成功。
   副本 fat jar 的 SOFA Hessian 3.3.6 与 Nacos 4.0.63 冲突只在复制的 jar 中移除旧版并
   记录为测试变通；运营启动器提供 8192 步 startup 缓冲，管理子上下文 Bearer 过滤器
   强制匿名 401、普通 403、管理员放行、非 GET 405。
3. [完成] 120 秒预检通过功能/边界检查，但暴露预期 401/403 错误码未归类的测试分类
   缺口；修正后 180 秒 `smoke-phases` 通过（904 次调用，包含八工具、两 SDK 协议、
   519 个可见 Bean 全量分页、游标绑定/过期、路由/健康/启动正向、配置默认关闭、
   OpenAPI/迁移 404、目标停止/重启、MariaDB 暂停后 readiness 超时与恢复）。
4. [完成] 正式 soak 14,401.542 秒、68,260 次调用、`accepted=true`、`failureCodes=[]`；
   240 个逐分钟样本；519 个可见 Bean 的基线与三个周期分页一致；两次计划内目标重启
   恢复 9.964/10.623 秒，两次 MariaDB 暂停后 readiness 超时并在解锁后恢复；非预期
   错误为空；最大完整回包 15,242 字节。结果与构建哈希写入
   `examples/nacos-soak-matrix/results/`，报告见 `docs/audits/nacos-four-hour-2026-10-23.md`。
   记录 Actuator 内嵌 Derby health 不反映外部 MariaDB 的真实盲区。
5. [完成] 完成性审计与清理：2026-10-23 当前离线全量 **999 passed**（44.03 秒），mypy 53
   个源文件、Ruff check/format 120 个文件、八工具契约和 `git diff --check` 通过；目标、
   MariaDB 容器和全部 MCP 子进程停止，运行目录及手工探针凭据文件删除；源码缓存保留。
   未提交、未发布。

---

# Bean 未创建根因与证据完整性专项（2026-11-01）

- [x] 读取双方规则，创建 codex/bean-evidence-integrity；记录当前源码摘要并复制 TDD（含未提交源码）。
- [x] 使用独立回环 PostgreSQL 与 shop-product，保留 JWT；仅暴露 health/info/beans/conditions。
- [x] 不带目录建立业务 Bean、依赖与已知条件样本基线；手工核实最小 source catalog，再对照。
- [x] 分类证据缺口；选择一个实测可重复缺陷，离线 RED → 最小修复 → GREEN。
- [x] 完整离线回归、真实样本复验、清理；仓库外交付脱敏报告。

外部工作区与报告：/home/neil/bean-evidence-review-20261101
约束：不修改 TDD 原目录、不新增依赖/公开 Schema、不扩大守卫或预算、不发布。
