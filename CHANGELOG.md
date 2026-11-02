# 版本记录

## v0.2.9 Alpha — 2026-11-02（工具文档与复跑保护）

- 已发布到 PyPI、GitHub Alpha Release 和 MCP Registry；标签 `v0.2.9` 指向 `96d1c53c512480f2d01b15513d3b51ec89ca1b0c`。本地、候选、正式及公开产物摘要一致；公开无缓存安装、SDK 两模式、八工具回环及七 replay 通过，见[发布验证记录](docs/launch/publication-verification.json)。
- 新增八工具的人类可读字段说明、公共信封说明及经实际参数校验的查询示例；字段、默认值、组合约束与现有工具 Schema 对齐。
- 明确配置诊断默认关闭及值输出的双重授权条件，整理已有 Bearer 接入、JDK 验证前提、Maven 参数和历史引用。
- Nacos 复跑入口在初始化资源前独占创建结果文件，拒绝已有文件、目录、符号链接和相同路径，避免覆盖历史验收证据；新增 9 项合成回归。
- demo 与 Node 安全测试使用已同步的锁定项目环境。八工具公开 Schema、运行依赖、固定端点及产品安全边界保持现有范围。

## v0.2.8 Alpha — 2026-11-01（静态事实与隔离故障验收）

- 新增仅解析显式登记 Java 文件的 JDK AST 维护脚本，生成现有 Source catalog 和漂移参数；未知类型、复杂条件与映射继续保留 partial/gaps。
- 新增本地源码/产物摘要证据，区分源码未构建与构建后未重启；不以本地 jar 摘要冒充运行进程身份。
- 新增构建、真实运行态及合成协议故障验收脚本，覆盖迁移错误、构造器循环、条件 Bean、路由、健康、响应安全和恢复。
- 验收覆盖 demo 与 Spring Boot Admin；1195 项测试通过，48 次 MCP 工具调用通过。Java 静态检查限于受支持 AST 子集和已测告警，不宣称完整版本或项目矩阵。
- 八工具公开契约、固定端点和 Python 运行依赖保持现有范围；静态生成器为源码仓库维护工具，需要完整 JDK，不进入 wheel 运行时。


## v0.2.7 Alpha — 2026-11-01（文档与发行包整理）

- 已发布到 PyPI、GitHub Release 和 MCP Registry；标签 `v0.2.7` 指向 `4a7a7c74b869d3aa13f64bd5b4786c7d08085fa2`。本地/候选/正式/公开产物摘要一致，公开无缓存安装及两模式、八工具和七 replay 通过，详见[发行记录](.human/releases/release-0.2.7.md)。
- 现行文档通过 docs/README.md 按需导航；重写产品、架构和调用说明，移出未落地设计与阶段流水账。
- AGENTS.md 精简至 29 行；中英文 README 用实际问题介绍八工具，完整客户端模板移入独立指南。
- 人类资料库精简为决策、想法、最终报告、独有机器摘要及发布记录；删除可从 Git 回查的重复材料，历史引用固定到原提交。
- wheel/sdist 明确排除 .human/；版本更新为 0.2.7，诊断逻辑、公开 Schema、依赖和安全策略保持。

## v0.2.6 Alpha — 2026-11-01（具名 Bean 条件）

- 已发布到 PyPI、GitHub Release 和 MCP Registry；标签 v0.2.6 指向 `60a4bea4434413fd140ef9bddf7d5bf4133d7b68`。完整门禁、公开无缓存安装和具名条件/阻塞链回归通过，四批产物摘要一致；旧版本标签及产物保留。
- 支持单一 names 选择器的 `did not find any beans named <name>`，要求名称严格一致，接通既有工厂/属性传递阻塞分析；不扩大多要求或未知语法的归因范围。
- 新增 29 项离线回归，P4 源补丁独立验收 1172 passed；同实例基线/候选及 A–E 正反证据持久留存，实际证据缺口继续 partial/unknown。
- CGLIB 关联、图算法、公开 Schema、运行依赖、错误码、网络/鉴权/TLS、脱敏和预算保持。范围与发布批次见[0.2.6 发布记录](.human/releases/release-0.2.6.md)。

## v0.2.5 Alpha — 2026-11-01（WebFlux 函数 handler）

- 已发布到 PyPI、GitHub Release 和 MCP Registry；标签 v0.2.5 指向 `f3f99310967b50dbee847ef82228f87ac8beba27`。完整门禁、公开包无缓存安装与函数类过滤回归通过，四批产物摘要一致。
- 保留 Actuator 的结构化 `details.handlerFunction.className`，投影到现有 `controllerClass`，修复 `controllerClassPattern` 对函数路由的漏匹配；不推断业务方法或 descriptor。
- 新增 9 项离线回归；P3 重新执行的真实 MVC/JWT startup 与独立 WebFlux/Bearer 验收证据已持久留存，源码补丁验收全量 1143 passed。复杂 predicate 与 500 步分析上限继续明确 partial。
- 合并 M8ven 发布者认证徽章分支；徽章不构成安全或兼容矩阵认证。
- 公开 Schema、错误码、运行依赖、目标/IP/端点边界、HTTP/TLS、脱敏和预算未修改。范围与发布批次见[0.2.5 发布记录](.human/releases/release-0.2.5.md)。

## v0.2.4 Alpha — 2026-11-01（首次接入体验）

- 已发布到 PyPI、GitHub Release 和 MCP Registry；标签 v0.2.4 指向 `4e9e571aac001fc6fa9f95026688b54ae767202c`，完整门禁及公开安装/新提示检查通过，产物摘要一致。

- 整理公开包到第一次有效查询的主路径，补充分层排错和可编辑安装元数据强制刷新指引，保留参考客户端的未验收范围。
- CLI 缺失/空 Bearer 变量提示检查父环境和 env_vars，采用不回显变量名或值的固定文案；既有单元/进程回归加强并保持 1134 项通过。
- 工具 Schema、错误码含义、依赖、算法、安全策略和预算保持；版本批次见[0.2.4 发布记录](.human/releases/release-0.2.4.md)。

## v0.2.3 Alpha — 2026-11-01（源码目录 Context ID）

- 已发布到 PyPI、GitHub Release 和 MCP Registry，标签 v0.2.3 指向 `3f752dc46f8f5b9344bdfbde15597b95f3dd6670`；完整门禁与公开全新安装通过，三批产物及公开 PyPI 摘要一致。

- 修复 source catalog 错将 Context ID 当作 Java 符号校验的问题；允许 shop-product 等合法身份并精确关联，保留长度与 C0/DEL 限制，Java 类型/工厂字段校验保持。
- 新增 16 项回归；独立验收全量 1134 passed，mypy/Ruff/格式通过。有限 TDD 正反样本与 legacy STDIO 已证明目录工厂关联和属性负向证据，代理类型及具名 OnBean 传递链限制仍保留。
- 补充源码目录指南；公开 Schema、依赖、安全守卫和预算未修改。发布批次状态见[0.2.3 发布记录](.human/releases/release-0.2.3.md)。

## v0.2.2 Alpha — 2026-10-31（诊断修复提示）

- 已推送 `v0.2.2`（`d4388d39b2ec57160836c602bf97f4875f7f6fe3`），发布到 PyPI、GitHub Release 与 MCP Registry；完整本地/远端门禁及公开 PyPI 全新安装通过，产物摘要一致，详见[发布记录](.human/releases/release-0.2.2.md)。

- `INVALID_ARGUMENT` 改为参数修复配方：检查实际 inputSchema 的字段名、类型与约束，提示 `maxResults` 为 1–50，不回显输入；修正参数无需审批。
- startup GET 的 5xx 保留原错误码和 HTTP 状态，提示核对暴露、Boot 版本与启动采集，明确状态码不能单独确定原因；配置及重启仍需授权，不回退 POST。
- 中英文 README 补充公开发行包的 Codex Bearer 环境变量转发示例与路由参数示例。公开 Schema、运行依赖、目标配置和安全守卫未修改；发布批次状态见[0.2.2 发布记录](.human/releases/release-0.2.2.md)。
- 新增 18 项回归，全量离线测试 **1118 passed / 44.90 秒**；mypy、Ruff 与八工具契约校验通过。HTTP 回归只使用测试自建回环服务，未重启或连接 TDD 实例；未重跑真实项目验收。
- 随后经授权对 TDD 当前开发副本进行源码版针对性真实回归：JWT 匿名拒绝、参数错误与修正、MVC 路由及 startup 500 提示均符合预期；Codex 临时会话实际完成错误调用、修正及后续查询。三次完整 STDIO 回包最大 2677 字节，临时实例和数据库已清理，原工作区文件保持；未重跑完整真实项目矩阵。

## v0.2.1 Alpha — 2026-10-31（元数据修正）

- 已发布到 [PyPI](https://pypi.org/project/spring-runtime-mcp/0.2.1/)，标签 `v0.2.1` 指向 `2d8567ba9ae10ac143a24d4ec443909a9e8997cb`。
- Registry 名称与 README 所有权标记统一为 `io.github.neilmorse/spring-runtime-mcp`，项目 URL 指向当前所有者；已通过短时 GitHub OIDC 身份发布并独立回读 Registry 条目。
- 本地/远端完整门禁、1100 项测试、wheel/sdist 隔离安装及公开 PyPI 无缓存、无锁约束安装通过。版本、两种 SDK 模式、八工具回环调用和七 replay 均通过，详见[发布记录](.human/releases/release-0.2.1.md)。
- 生产诊断实现、公开工具 Schema、运行依赖与安全边界保持；动态项目的 uv.lock 条目不固化项目版本，重新锁校验通过且锁文件字节未变。0.2.0 标签和已上传产物保留。
- 目录 PR 已提交为草稿，依用户选择暂缓 Glama 账号/收录步骤；未宣称目录已正式收录。

## v0.2.0 Alpha — 2026-10-31（正式发布）

- 已发布到 [PyPI](https://pypi.org/project/spring-runtime-mcp/0.2.0/)，标签 `v0.2.0` 对应 `2394b29a84a5fcd8210d3934eee1a94e1d3fc0ac`。
- 干净提交本地完整门禁退出 0；正式 Release 的 Python 3.11–3.14、静态检查、契约、漏洞审计、构建/两产物隔离安装与发布全部通过。
- 公开 PyPI 仓库外全新环境安装通过两种 SDK 模式、八工具回环调用和七 replay；公开产物摘要与验收批次一致。首发保持 Alpha、本地回环与有限兼容范围，详见[发布记录](.human/releases/release-0.2.0.md)。
- 下列“未发布”记录保留各轮实施时状态；其中交付内容已随本版纳入，不应据历史措辞判断当前未发布。2026-10-22 的 v0.2.0 条目记录开发里程碑，不是 PyPI 首次发布日期。

## 未发布 — 2026-10-31 发布流程收口

- 将已审阅的生产修复、测试、资源、脚本和历史证据准备为同一发布提交；Nacos 原运行日志/逐分钟 JSONL 本地留存并精确忽略，聚合证据保留。
- 新增仅验证的 `Release validation only` 分支流水线，复用完整门禁，不请求 OIDC 或 PyPI 发布环境；正式标签仍需版本匹配及操作者批准。
- 修复 Git 清单的特殊文件名漏检：二进制 `git ls-files -z` 配合 `os.fsdecode`，新增 14 项真实 Git 回归。此前修复后离线 1100 passed；最终提交门禁与产物摘要另存仓库外证据，不复用旧批次。
- 核实当前仓库所有者为 neilmorse，更新发布账户核对参数；PyPI 账户访问受阻、GitHub 尚无 pypi 环境，不声明发布就绪。

## 未发布 — 2026-10-31 正式发布准备收口

- 发布 CI 复用完整预发布脚本，新增强制联网漏洞审计、敏感文件/源码检查、契约校验及 sdist 隔离安装；上传已验证的同一批 wheel/sdist，不重新构建。远端执行待验。
- 中文独立启动命令统一到锁定项目环境；保留 0.2.0 Alpha，纠正已打标签声明，公开包安装和实际客户端验收不再与 SDK 验收混同。
- sdist 排除日志、JSONL、缓存和环境文件，保留用户源文件。范围、实际证据、交付关系与人工待办见[发布准备报告](.human/reports/release-readiness-2026-10-31.md)。

## 未发布 — 2026-10-30 构建依赖锁定

- 将 Hatchling 及其构建依赖固定到明确版本，并纳入开发依赖锁文件；预发布检查拒绝未固定或未纳入锁文件审计的构建依赖。没有新增运行时依赖。
- 使用锁定依赖离线构建 wheel 和 sdist，分别通过隔离安装、CLI、两种 SDK 模式、八工具回环调用和七个 replay 场景。新增 2 项构建锁定回归；最终全量 **1084 passed / 44.43 秒**，mypy 53 个源文件、Ruff 124 个文件及八工具契约通过。`uv audit --locked` 对 43 个包未发现已知漏洞；仅代表当时的联网查询结果。

## 未发布 — 2026-10-30 HTTP 读取边界修复

- 增加 32 KiB 响应头累计预算，覆盖状态行、临时响应和最终响应，解析时超限返回 `RESPONSE_HEADERS_TOO_LARGE`。单成员 gzip 增量解压分别限制编码体和解码体，拒绝损坏、截断、尾部数据和多成员；其他编码仍拒绝。
- 提前断开且未收满 Content-Length 时返回 `INCOMPLETE_RESPONSE`，不将偶然合法的 JSON 片段当作完整证据。多个解析后地址共享 2 秒 socket 连接时限，连接后恢复本次调用剩余读取时限；操作系统 DNS 解析本身仍不能由 Python 强制终止。
- 新增合成和自建回环回归，覆盖响应头、gzip、健康 503、分块传输、双重大小限制、正文截断及连接时间预算。全量 **1082 passed / 44.67 秒**；mypy 53 个源文件、Ruff 124 个文件及八工具契约通过。Python 3.11/3.14 仅对响应头解析边界做了本地补充验证。
- 本地自建 TLS 测试使用一次性合成证书和内存文件，验证可信证书成功、主机名不符、不受信、过期及 IP 名称不符拒绝；失败时没有发送 HTTP 请求。主机名场景的 SNI 为登记主机，IP 字面量未发送 SNI。这是有限回环样本，不代表完整 TLS/SNI 版本矩阵。
- 历史 LS-01 与 PC-01/PC-02 的离线修复探针以 `--expect-repaired` 再次通过；临时探针输出已清理，未重跑历史真实项目矩阵。

## 未发布 — 2026-10-30 sdist 净室安装验收

- 预发布净室阶段要求各一个 wheel 与 sdist，分别校验版本和运行资源；sdist 额外拒绝缓存、构建产物、敏感环境文件及符号链接。两种产物分别在独立环境中按锁文件约束安装运行依赖，并完成 CLI 版本、SDK 两种模式、八工具回环链路和七个 replay 场景。
- 新增 6 项 sdist 失败回归，覆盖产物缺失、版本或资源不一致、缓存、危险链接与安装失败。真实净室阶段通过；全量 **1055 passed / 38.85 秒**，Ruff 123 个文件通过。构建后端仍按声明范围从本地缓存解析，不由运行依赖约束锁定；本轮未发布。

## 未发布 — 2026-10-30 HTTP 响应编码守卫

- 对声明了非 identity Content-Encoding 的 JSON 响应，在读取正文前返回 `UNSUPPORTED_CONTENT_ENCODING`；错误保留已登记端点与 HTTP 状态，不回显编码或正文。缺省和 identity 继续读取；gzip 解压尚未实现。
- 新增 12 个离线回归，覆盖编码链、未知编码、正常 identity、错误信封和自建回环慢速响应。首次全量测试暴露旧超时 fixture 的响应头模拟不准确及回环事件竞态，已修正测试环境并保留原断言；最终全量 **1049 passed / 40.51 秒**。mypy 53 个源文件、Ruff 123 个文件和八工具契约通过；未修改工具 Schema 或运行依赖。

## 未发布 — 2026-10-30 HTTP 拒绝响应读取修复

- 连接器在读取正文前检查 HTTP 状态和 Content-Type；重定向、鉴权失败、不可用端点及非 JSON 类型不再主动读取错误页，响应门仍返回原有固定错误。健康端点有效 503 JSON 继续读取；可接受 JSON 类型的判断由连接器与响应门共用。
- 先用合成响应复现错误页读取，再用自建回环服务验证慢速正文不会把 302、401 或错误 Content-Type 转为超时。新增 17 项回归；定向网络测试 118 passed，全量 **1037 passed / 36.78 秒**；mypy 53 个源文件、Ruff 123 个文件和八工具契约通过。未改变只读网络边界、公开 Schema 或运行依赖。

## 未发布 — 2026-10-30 Health 证据总数修复

- Health 组件不可读或状态缺失时，`coverage` 继续记录缺口，`totalMatched` 改为 null；可读组件与未知状态仍保留。此前可能在 partial 结果中返回确定的 0 或可读条目数，误示匹配范围完整。
- 新增 7 项合成回归，覆盖不可读组件、路径过滤、合法组件共存、缺状态、完整空结果及 MCP 快照续页。全量 **1020 passed / 36.38 秒**；mypy 53 个源文件、Ruff 122 个文件及八工具契约通过。未修改公开 Schema 或目标访问策略，未连接真实 Spring 实例。

## 未发布 — 2026-10-30 预发布检查与工作区盘点

- 预发布脚本读取 Hatch 动态版本，检查源码版本一致性，并在净室阶段校验 wheel 元数据与 CLI 版本。wheel 安装使用 `uv.lock` 导出的离线约束；跳过构建、允许脏工作树或接受跳过测试均标为不完整。
- 漏洞审计独立为 `--audit`：调用 `uv audit --locked`，审计失败或不可用阻断；未启用时明确报告未执行。门禁返回 0 表示完整通过、1 表示失败、2 表示不完整。
- 新增 14 个离线门禁回归，覆盖漏洞、超时/工具缺失、动态版本冲突、wheel/CLI 版本不一致、跳过检查、锁文件约束以及 Git 状态或跟踪文件不可读。全量 **1013 passed / 34.54 秒**；mypy 53 个源文件、Ruff 121 个文件、八工具契约及 `git diff --check` 通过。独立执行的 `uv audit --locked` 对 40 个包未发现已知漏洞；联网审计为当时的查询结果，不能替代后续复查。
- 净室阶段实际构建并验证 wheel 资源、锁定安装、CLI 版本、官方 SDK 两种模式、八工具回环链路和七个 replay 场景。端到端自检首次发现 `pytest` 可执行文件无法导入新增测试所需的项目脚本，已改为仓库规定的 `python -m pytest` 入口。
- 工作区文件盘点见[交付清单](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/worktree-inventory-2026-10-30.md)；清单不代替逐文件内容审查。未改公开 Schema、生产诊断逻辑或运行依赖；未提交、未发布。

## 未发布 — 2026-10-23 热门生产项目 Nacos 四小时持续运行

- 新增[Nacos 四小时生产模拟](examples/nacos-soak-matrix/README.md)：从 Nacos、PowerJob、Sentinel 候选中随机抽取 alibaba/nacos 2.4.3 固定提交 `f4f8b189cf16186669de5b692d43630ed2c3fda2`（2,391 个 Java 文件 / 1,526 个主 Java / 22 个 Maven 模块，Boot 2.7.18 / Java 21 / MariaDB 11.2），在回环地址、一次性 MariaDB 和独立管理端口上运行四小时。原始分布 jar 的 SOFA Hessian 3.3.6 与 Nacos 需要的 4.0.63 冲突只在复制 jar 中移除旧版；管理 Bearer、8192 步启动缓冲和业务鉴权关闭均为测试配置。
- 正式 soak **14,401.542 秒**，**68,260 次真实调用全部满足断言**：519 个可见 Bean 基线 52 页、三个周期各 44 页穷尽且无漂移；1/2.5 小时目标重启恢复 9.964/10.623 秒；1.5/3 小时 MariaDB 暂停后 readiness 超时并在解锁后首次检查恢复；最大完整回包 15,242 字节；中位/p95 延迟 242.754/945.435 ms；240 个逐分钟样本，非预期错误为空。结果见[审计报告](.human/reports/nacos-four-hour-2026-10-23.md)、[脱敏聚合](examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23.json)和[构建/补丁哈希](examples/nacos-soak-matrix/results/nacos-four-hour-2026-10-23-build.json)。
- 记录目标级健康盲区：Actuator 的 `db` 指标来自内嵌 Derby，外部 MariaDB 暂停时 readiness 超时但 MCP `diagnose_health` 仍为 UP；报告保留 `actuatorObservedExternalDbOutage=false`，不把该结果当作外部数据库健康证明。只验证固定提交的单节点 standalone，不验证集群/HA、配置发布、服务注册、UI、客户端长连接或 JRaft 多节点；未改生产 Python 代码，未提交、未发布。当时离线全量 **999 passed**。

## 未发布 — 2026-10-23 小型生产调度器 XXL-JOB 验收

- 新增[调度器项目矩阵](examples/xxl-job-matrix/README.md)：拉取 XXL-JOB v3.4.0 固定提交 `555b48f2edf0e51cd77971565342d80c15c9f18d`（157 个 Java 文件 / 136 个主 Java，Boot 4.0.5 / Java 21 runtime / MariaDB 11.2），完成八工具功能、稳定性和可用性验收。未修改生产 Python 代码；SSO actuator 放行、管理 Bearer Filter 和 Logback 遮蔽均为临时测试配置。
- 正式 300 秒运行 **2449 次真实调用全部满足断言**：356 个 Bean / 402 条依赖，356 个可见 Bean 经 35 页穷尽；路由与 db 健康 ok/complete；带原生 SSO 的业务 UI 未绕过；MariaDB 暂停后健康 DOWN、Bean 读取仍可用、恢复后 UP；最大完整回包 15,638 字节；目标停止/同宿主重启恢复。结果见[审计报告](.human/reports/xxl-job-2026-10-23.md)与[脱敏聚合](examples/xxl-job-matrix/results/xxl-job-final-300s.json)。
- 启动树仍为 partial，迁移端点 404 负向；未验证执行器任务、告警、生产调度集群或 UI。当时全量 **925 passed**；未提交、未发布。

## 未发布 — 2026-10-23 小众生产项目 HertzBeat 验收

- 新增[小众生产项目矩阵](examples/niche-project-matrix/README.md)：拉取 Apache HertzBeat v1.7.3 固定提交 `67ad4b04ef1b06b62f0e5030a26d0ca069294fa3`（1387 个 Java 文件 / 975 个主 Java，Java 17 / Boot 3.4.2 / Maven / 内嵌 H2），完成八工具功能、稳定性和可用性验收。未修改生产 Python 代码；测试用的管理 Bearer Servlet Filter、Sureness `/actuator/**` 放行规则和 2048 步启动缓冲均只存在于临时副本。
- 正式 300 秒运行 **1594 次真实调用全部满足断言**：875 个 Bean / 1167 条依赖，873 个可见 Bean 经 87 页穷尽；Flyway 5 条 APPLIED；路由和 db 健康 ok/complete；启动树仍为 partial 并保留节点/深度缺口；最大完整回包 15,072 字节；目标停止/同宿主重启恢复。结果见[审计报告](.human/reports/niche-project-hertzbeat-2026-10-23.md)与[脱敏聚合](examples/niche-project-matrix/results/hertzbeat-final-300s.json)。
- HertzBeat 的 Spring AI MCP server 保留原生启用，未调用外部模型；首次关闭该 server 会导致 `webMvcSseServerTransportProvider` 缺少依赖 Bean。H2 为内嵌数据库，本轮没有数据库暂停场景；未验证 UI、上游测试、告警投递或生产集群。未提交、未发布。

## 未发布 — 2026-10-23 MCP 交付专项门禁

- MCP 宿主启动时核对八工具契约与处理器集合；缺失或多余处理器立即拒绝启动，移除路由中的 `CAPABILITY_DISABLED` 占位兜底。配置诊断未授权时仍由真实处理器返回该安全拒绝，不修改公开 Schema、依赖或目标策略。
- 净室门禁逐字节比对 wheel 的 Schema、`py.typed` 与全部 replay JSON；安装后从仓库外执行官方 SDK 两模式、分阶段原始管道握手、八工具真实 HTTP 路由、未掩码配置脱敏、16 KiB 回包和七个 replay 场景。replay 使用 `importlib.resources` 定位包内资源，保留无符号链接、有界文件读取。
- 修正 source catalog STDIO 测试的 EOF 竞态，读取回复后再关闭输入；配置 CLI 集成测试改为自建回环 fixture，避免探测固定端口上的未知服务。证据及限制见 [MCP 交付专项核验](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/mcp-release-gate-2026-10-23.md)。

## 未发布 — 2026-10-23 交付前总核验

- 源码与依赖闭环：生产代码无 TODO/FIXME/HACK/XXX、`NotImplementedError` 或调试断点；八个公开工具全部绑定真实处理器；运行时第三方导入只有 `mcp` 与 `jsonschema`，二者均已声明；配置诊断默认关闭，未登记时返回 `CAPABILITY_DISABLED`。
- CLI 启动加固：`--source-catalog` 只接受常规文件，并按 256 KiB 上限分块读取，避免无界内存占用、FIFO 阻塞或设备文件读取；非文件、超限、目标不匹配、缺少令牌变量和非法参数均以具体且不包含值/路径的提示退出（exit 2）。新增 `--version`，与 `__version__`、wheel 元数据一致。
- 安全依赖：开发依赖 pytest 由 8.4.2 升级至 9.0.3，关闭 `uv audit` 报告的 PYSEC-2026-1845；`uv audit` 对 40 个已解析包报告无已知漏洞。Git 全历史与工作区扫描未发现真实凭证，命中的 PEM/Bearer 均为合成测试向量。
- 净室验证：wheel 与 sdist 包含 `tools-contract.json`、`py.typed` 与 `replay_data`，不包含测试缓存、`target/` 或示例 jar；在全新 venv 中从 wheel 和 sdist 安装后，`--version`、legacy/2026-07-28 两种 MCP 协议和安装包内 replay 均通过。`uv lock --check` 通过。
- 文档对齐：README/README.zh-CN/SPEC 增补 `--version`；修正 SPEC 中过期的 `mypy src scripts`、默认测试范围、演示校验命令和“`--version` 未交付”表述；清理文档中的用户主目录绝对路径。
- 最终离线 **922 passed**，mypy 53 个源文件、Ruff 113 个文件、八工具契约通过；没有 skip/xfail。详见[交付前总核验](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/final-delivery-audit-2026-10-23.md)。版本仍为 0.2.0，Git 无发布标签；本轮未提交、未发布，也不声称新增真实目标或生产矩阵验收。

## 未发布 — 2026-10-23 超大型生产系统 Fineract 验收

- 新增 [超大型项目矩阵](examples/ultra-project-matrix/README.md)：拉取 Apache Fineract 1.9.0 固定提交 `5d96e8cc32ff63f97d5ac15e19c6fafee0c31357`（4565 个 Java 文件 / 4087 个主 Java，Java 17 / Boot 3.1.7 / Gradle 8.5），在一次性 PostgreSQL 16 和回环 HTTP 上启动原生 provider，完成八工具功能、稳定性与可用性验收。临时构建仅在 `pluginManagement` 增加公共镜像以解析已停用 JCenter 的文档插件依赖；Boot/BOM、运行依赖和诊断网络边界未改。
- 发现并修复 mappings 对 JAX-RS 业务路由的假阴性：Actuator `servlets` 显示 Jersey `/api/*` 覆盖时，查询路径可能由其提供但 DispatcherServlet 无记录；修复后返回 `partial`、`totalMatched=null` 和 `NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED`。新增 4 个离线回归，全量 **913 passed**。
- 正式 300 秒运行 **1202 次真实调用全部满足断言**：2544 个 Bean / 5626 条依赖，2524 个可见 Bean 经 252 页穷尽；最大完整回包 15,170 字节；数据库暂停后健康不再 UP、Bean 读取仍可用、恢复后 UP；目标停止/同宿主重启恢复；JAX-RS 业务路由探针为 partial/gap。8192 步启动快照触发 `NORMALIZATION_LIMIT`，测试启动器改用 2048 步取得正向证据，保留容量限制。结果见[审计报告](.human/reports/ultra-project-fineract-2026-10-23.md)与[脱敏聚合](examples/ultra-project-matrix/results/fineract-final-300s.json)。
- 首轮完整门禁在重负载后有 1 个 STDIO 进程测试失败，单独及第二次全量均通过；保留为时序波动，不修改测试或放宽断言。未提交、未发布；不声称生产集群、完整版本矩阵或长期稳定性通过。

## 未发布 — 2026-10-23 故障矩阵问题修复

- 关闭 PC-01、PC-02、LS-01，见[调研、修复与复验](.human/reports/production-chaos-remediation-2026-10-23.md)。说明/异常字段的 name/value 描述符传播 taint，独立出口拒绝未脱敏值；编码或无法安全输出的名称不能恢复关联值，同名 OpenAPI 业务 Schema 保留。健康错误仅提取全限定类型形态，原消息不回显。
- 游标登记前校验安全性和唯一性，最多 16 次候选；失败不污染缓存。分页改用共享编码快照和偏移，正常续页仅处理当前页，保留原始 60 秒 TTL、32 MiB/LRU、16 KiB 完整回包及凭据策略刷新后的整快照复验/删除。
- 新增 28 个合成回归，最终 **909 passed**，mypy/Ruff/契约通过。三项真实项目最终 **425 次调用全部满足断言**，ThingsBoard 首次连续 125 页穷尽 1255 个可见 Bean，指令 canary 均未透传，旧失败记录不覆盖。未修改公开 Schema、运行依赖或目标策略，未发布；不声称生产集群或完整版本矩阵通过。

## 未发布 — 2026-10-23 真实项目故障注入

- 增加[生产采用项目故障矩阵](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/production-chaos-2026-10-23.md)：ShenYu、ThingsBoard、DolphinScheduler 原生后端构建/隔离启动，选定流程 399 次真实 MCP 调用，覆盖 PostgreSQL 暂停、连接池耗尽、启动冲突/缺依赖/循环、1000 个额外实际 Bean、坏响应与取消恢复。ThingsBoard 仅在临时副本增加可选 Actuator，DolphinScheduler 使用开发 Standalone，均不代表生产集群验收。
- 新确认 PC-01 健康详情 name/value 指令透传，补独立 canary 断言并保留真实失败；PC-02 记录 ThingsBoard 大快照连续分页在绝对 60 秒 TTL 内无法穷尽的可用性限制；旧随机游标 LS-01 仍未修复。新增离线调查探针，退出 0 表示缺陷复现；默认仍 881 passed，不能据此声称安全/稳定性全部通过。生产实现、公开 Schema、Python 运行依赖未改，未提交或发布。

## 未发布 — 2026-10-22 综合审查修复

- 增加[大型原生项目稳定性矩阵](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/large-project-stability-2026-10-22.md)：Flowable、Spring Cloud Data Flow、Reactive Spring Boot Admin 固定提交构建与隔离运行，最终 1748 次真实调用，覆盖完整可见分页、四路并发、两种 SDK 协议和实例重启恢复。发现并确定复现随机游标与输出安全门冲突；保留真实 `UNSAFE_OUTPUT` 失败，生产修复尚未实施。默认离线测试仍为 881 passed，不将短时运行或 partial 结果声明为完整稳定性/兼容性通过。
- 关闭遗留 R1–R5：保留 PathItem 非冲突相邻字段，冲突/不可读操作计数 unknown；修复 Schema resource 方言继承；统一受限 RFC3339 校验及精确时间排序，非法启动时间不再冒充完整漂移比较。新增 44 个合成回归，全量 **881 passed**。通过可复现的本地 springdoc 3.1.1 源码补丁修复过早分组实例化及固定文档入口，JHipster 独立管理端口完成 18 次验收，Petclinic REST 复验 15 次通过；缓存 jar、公开工具 Schema 和 Python 运行依赖未改。见[闭环报告与限制](.human/reports/remaining-findings-remediation-2026-10-22.md)。
- 修复较大项目暴露的两个 OpenAPI 缺陷：共享引用的数组元数据改为有界独立投影；业务属性 `description` 的 Schema 不再被误清空，原始说明/凭据仍受递归脱敏与输出安全门限制。新增 21 个合成回归，全量 837 passed；Petclinic REST 15 次复验通过。JHipster 保留原生 API-docs/JWT/Liquibase 的同端口配置完成 18 次验收；独立管理端口组合的第三方初始化故障仍未修复。见[修复与限制](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/openapi-project-matrix-remediation-2026-10-22.md)。
- 增加[较大公开项目真实矩阵](examples/project-matrix/README.md)：保留 Petclinic、Petclinic REST、JHipster 的原生 Boot 版本，主矩阵记录 43 次调用，覆盖 416–486 个 Bean、分页、数据库健康、原生 OpenAPI 简单 Schema、JWT 401/403 和 8 条已应用 Liquibase。复杂 OpenAPI 的两个诊断缺陷及 JHipster API-docs 启动阻塞保留为失败，不计作通过；本次只新增验收材料，未修复这些缺陷。
- 修复真实 WebFlux 函数式路由的嵌套 AND、`Accept:` / `Content-Type:` predicate 解析；未知 OR/NOT/自定义语法继续 partial。新增 34 个离线回归，全量 816 passed；Boot 3.2.4 / WebFlux / Java 21 的 12 次真实调用验收通过，原始失败证据保留。见 [修复与复验](.human/reports/webflux-predicate-remediation-2026-10-22.md)。
- 关闭 [综合审查](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/comprehensive-review-2026-10-22.md)的 CR-01 至 CR-13；逐项证据见[修复验收报告](.human/reports/comprehensive-remediation-2026-10-22.md)。超长请求 ID 在 SDK 前拒绝并以 null ID 结束会话；真实 SDK 工具出口再次检查 16 KiB 上限。
- 下沉共享 `Services` 与安全诊断信封，八工具共用每目标两个读取槽和一个 15 秒 deadline；排队、读取、协作分析及输出检查使用同一预算。
- 修复 OpenAPI 组合/字典 Schema、本地 PathItem/Response 引用及 3.0/3.1 `$ref` 语义；未知 Schema 语义明确 partial。修复迁移缺证据推导、checksum 可比性、Bean 类型查询的父子遮蔽、成功迁移状态及隐藏 UP 组件的可见性结论。
- STDIO 进程测试按回复完成再关闭输入，并使用有时限的管道读取。CI/发布复用校验工作流，发布依赖全部门禁且校验版本标签；没有执行发布。
- 增加 `uv.lock`、固定开发工具版本及 wheel 的 `py.typed`。隔离安装通过官方 SDK 2.3.0 客户端的 legacy / 2026-07-28 发现及工具错误检查。
- 增加本地受信 `--token-env` Bearer 绑定，限制令牌格式并纳入已知秘密脱敏；不增加任意头透传或 Basic 支持，不改变工具公开 Schema、运行依赖或回环边界。
- 明确批准后，针对 `<TDD checkout>` 的已提交 S8 副本完成 Boot 3.5.16 / Java 21 / MVC / JWT / 临时 PostgreSQL 16 验收。TDD 原工作区保留未完成业务代码，只新增已批准的可选 Actuator Maven profile。六个诊断端点均只读，匿名拒绝，环境和配置值端点关闭；结果见 [Shop 摘要](examples/tdd-runtime/verification.json)。这不代表全版本矩阵或 TDD 当前红阶段业务已完成。
- 离线全量 **782 passed**，mypy 51 文件、Ruff、八工具契约、wheel/sdist 构建及安装验证通过。
- 交付审计追加修复：drift 在 startup 证据缺失时返回显式 `STARTUP_EVIDENCE_UNAVAILABLE` 而不是 `ok`；mappings 对不可读 patterns/methods 标记 partial 并禁止伪造 unrestricted；Bean 缺失类型/scope、health details/startup tags 截断、迁移预算耗尽及 date-time 输出契约均显式标注；配置诊断新增 `--config-prefix/--config-property/--config-profiles/--config-allow-values`；replay fixtures 随包分发，安装 wheel 后可重放。修复与验证证据见 [交付审计修复与验证](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/delivery-audit-remediation-2026-10-22.md)。

## v0.2.0 — 2026-10-22

- 关闭 2026-10-18 逻辑与边界审计的 TC-BUG-01 至 15；连接器增加数字地址固定与 peer 校验，安全静态清单仅对 `transport/actuator_http.py` 放行 `socket`/`http.client` 导入并新增禁止原始套接字写入。全量 730 passed。
- 工具契约 JSON 移至 `src/spring_runtime_mcp/schemas/`，通过 `importlib.resources` 加载，随 wheel 分发。
- 增加 hatchling 构建后端、Apache-2.0 许可证、英文 README、`SECURITY.md` 与 GitHub Actions CI（Python 3.11–3.14 测试、mypy/ruff、wheel 构建及干净环境 stdio 握手）。`uv build` 产物已在隔离虚拟环境安装并完成 `initialize`/`tools/list`。
- STDIO 宿主迁移到官方 `mcp` Python SDK 2.x 的 lowlevel `Server`，新增运行依赖 `mcp>=2.3,<3`。握手协商、初始化门禁、JSON-RPC 错误映射与取消由 SDK 负责；工具描述符、outputSchema 校验、脱敏与 16 KiB 预算是本项目逻辑。
- 协议行为变化，客户端可能感知：
  - `initialize` 之前只接受 `ping`；提前的 `tools/*` 返回 JSON-RPC `-32602`。
  - 未知工具返回 `-32602`（此前为 `-32600` 或失败信封）。
  - 不支持握手版本（如 `2026-07-28`）协商到 SDK 的最新 handshake 版本 `2025-11-25`，不回显请求版本。
  - 传输层无法解析的帧（非法 JSON、`jsonrpc` 非 `"2.0"`、非字符串/布尔/浮点 id、`params` 非对象）被直接丢弃而不回应；原有“不触达处理器、零 IO”的安全性质由 SDK 解析边界保证，对应测试改为断言该性质。
  - 16 KiB 预算现在包含 2026-era 响应的 `io.modelcontextprotocol/serverInfo` `_meta` 戳。
- 安全静态清单把 `mcp`/`mcp_types` 的导入范围限制在 `server.py` 与 `cli.py`；`transport/stdio.py` 仍只服务重放 CLI。
- 真实应用验证：新增 `examples/spring-boot-demo`（Spring Boot 3.4.5 / Java 21、H2 + Flyway、独立只读管理端口、`BufferingApplicationStartup`）与 `scripts/check_demo_app.py`；提交的 `transcript.jsonl` 覆盖 initialize、tools/list 及六个读工具。
- 修复真实 `/actuator/beans` 互操作缺陷：Boot 仅对子上下文输出 `parentId`，缺省应视为根上下文而不是未知父容器；此前所有真实单上下文应用都会被判为 partial 且缺失 Bean 分析无法给出阻塞链。对应回归见 `tests/unit/test_bean_graph.py` 与 `test_rw06_architecture_regressions.py`。
- 验证计数更新为 730 passed；真实应用验证不属于默认离线门禁，需先启动演示应用且只访问回环管理端口。

## v0.1.0 — 2026-10-17

首次源码封板，版本号与 `pyproject.toml`、MCP `serverInfo.version` 一致。本记录描述本地 Git 提交范围，不代表包发布、部署或生产验收。

### 交付范围

- 八个按名称排序注册的诊断工具：Bean/条件、路由、健康、迁移、启动、配置、OpenAPI 与漂移。
- Bean 别名和父子容器依赖图、嵌套条件三值归因、同文档 OpenAPI 引用展开，以及缺证据时的 partial/unknown 结果。
- 自实现 STDIO JSON-RPC 宿主、启动时登记 origin 的标准库 HTTP 连接器和固定场景离线重放 CLI。
- 固定 GET 端点、不跟随重定向、字段投影和双层脱敏、查询绑定游标，以及包含 structuredContent 与文本副本的 16,384 字节完整回包预算。
- 八工具 JSON 契约、合成多版本 fixtures、离线/回环集成及安全回归，目标配置与客户端接入文档。

### 封板验证

在仓库根目录实际执行，全部使用缓存依赖；未连接真实 Spring Boot 或生产目标。HTTP 集成仅使用测试自行启动的回环 fixture 服务。

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 全量测试 | `uv run --offline --no-project --with pytest==8.4.2 --with jsonschema==4.25.1 python -m pytest -q` | 639 passed，22.35 秒 |
| 类型检查 | `uv run --offline --no-project --with mypy==1.18.2 --with jsonschema==4.25.1 python -m mypy src/spring_runtime_mcp` | 48 个源文件通过 |
| Lint | `uv run --offline --no-project --with ruff==0.14.1 ruff check src tests scripts` | 通过 |
| 格式 | `uv run --offline --no-project --with ruff==0.14.1 ruff format --check src tests scripts` | 75 个文件通过 |
| 契约 | `uv run --offline --no-project --with jsonschema==4.25.1 python scripts/validate_tool_contract.py` | 8 组独立 input/output schemas、144+ 合成断言通过 |

本次未单独执行 Node 包装入口、wheel/sdist 构建、客户端互操作或真实实例版本矩阵。

### 已知限制

- 当前宿主未使用官方 MCP Python SDK；有限 JSON-RPC 方法测试不能证明完整 MCP 协议合规或所有客户端兼容。
- HTTP 连接器尚无完整的 DNS 全组白名单验证、数字 IP 固定建连、实际 peer IP/port 校验和目标凭据绑定；HTTPS 使用默认 TLS 上下文，尚无真实 TLS/SNI 矩阵验收。远程/生产使用仍需完成安全规格的独立验收。
- 上游读取有字节上限和套接字超时，但完整绝对时限、解压预算与在途请求取消仍需独立验收。
- Boot 2.7/3.x/4.x、MVC/WebFlux 的证据来自合成 fixtures，未完成真实 Java/Boot/认证组合验收；源码类型与工厂关联仍依赖显式 SourceCatalog 事实。
- 尚无显式构建后端、依赖锁文件或已验证的分发产物。本版不宣称满足 SPEC 中全部产品目标。
- [红队审计](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/security-redteam-2026-10-17.md)及其机器清单是较早代码基线的历史证据，不是新增模块的完整审计。

本次封板整理不改变公开 inputSchema/outputSchema、运行依赖、目标白名单或目标配置。
