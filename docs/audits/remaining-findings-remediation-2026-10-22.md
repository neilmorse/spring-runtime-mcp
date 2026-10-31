# 遗留问题闭环修复 — 2026-10-22

接续[原因调查](unresolved-findings-investigation-2026-10-22.md)，用户明确要求开始修复。
R1–R5 已在诊断内核修复；JHipster 的原独立管理端口链路通过本地 springdoc 源码补丁完成验收。
**未打补丁的第三方 jar 不在本轮被修改，也不声称它已自行恢复。**
保留全部修复前失败和此前未提交改动；未提交、发布或部署。

## 本项目五项修复

| 项目 | 最终行为 | 实现 |
| --- | --- | --- |
| R1 PathItem 相邻操作 | 两级本地引用的 GET/HEAD 和当前 POST 均保留；重复字段不选择覆盖方，保留其他字段并显式 partial | `adapters/openapi.py` 的专用 `_path_item`；Parameter/Response 包装引用不改变合并语义 |
| R2 非法启动时间 | 缺失、非字符串、不可解析或无时区的启动时间产生 `STARTUP_TIMING_UNOBSERVED`；drift 为 partial，计数 unknown | `tools/detect_drift.py` |
| R3 时间格式及比较 | 输入、输出校验、startup 和 drift 使用同一受限 RFC3339 解析器；拒绝基本日期、周日期、空格分隔、非法日历/偏移、偏移秒；接受小写 t/z、带偏移时间及合法位置的闰秒 | 新增 `models/timestamps.py`；不增加运行依赖 |
| R4 方言作用域 | 内联子 Schema 继承当前 resource 的方言；引用按目标所在位置计算方言；文档默认未知时，已支持根方言内的 `$defs` 共享引用仍可解析 | `adapters/openapi.py`；目标指针与方言缓存不借用调用方的上下文；跨入含不支持 `$id`/动态锚点的 resource 仍保留未知基址缺口 |
| R5 不完整枚举计数 | 无法解析的 PathItem、字段冲突、不可读操作返回 `totalMatched=null`；已证明存在的操作仅因 Schema 深度不足时仍保留操作数；不匹配的路径仍可为完整零 | `tools/search_openapi.py`，不把所有 partial 都改成未知计数 |

时间比较保留完整小数位并为显式闰秒保留排序位置，验证了纳秒差异以及
23:59:59.9 → 23:59:60 → 次日 00:00:00 的顺序。
解析器上限 64 字符，受 Python 日历/UTC 可表示范围限制；校验闰秒的 UTC 月末位置，
不维护历史或未来闰秒公告表。startup 遇到显式闰秒时保留合法时间字段，但时间跨度为 unknown，
不会据此伪造精确耗时。

引用扫描继续阻断远程引用，保留 JSON Pointer 转义、环检测、深度上限及共享分析预算。
PathItem 字段遍历和目标作用域扫描均消耗该预算；超长引用在指针扫描前拒绝。
没有放宽树结构、脱敏、凭据、GET、固定端点或 16,384 字节输出守卫。
公开 inputSchema/outputSchema、八工具注册及风险注解保持原样。

新增 [44 个合成回归](../../tests/unit/test_remaining_findings.py)。最初 33 项在修复前为
23 failed / 10 passed；随后补充了非法 resource 方言、PathItem 环/预算、超长指针、非法路径名、
startup 的非法根时间、小写时间和闰秒跨度。未复制真实响应为 fixture。
独立 conformance 时间 oracle 保持独立，没有改成调用新实现。

## JHipster 独立端口修复

固定应用提交仍为 `6b000b5d23a36c45e01472471b84a44fa2464044`：Boot **4.1.1**、
Java **21**、JHipster framework **9.4.0**，原生 JWT、同步 Liquibase、临时 H2。
沿用先前获准的管理命名空间补丁；业务源码、原生 POM 和缓存中的依赖 jar 均未再修改。

本地 [springdoc 3.1.1 三文件补丁](../../examples/project-matrix/springdoc-3.1.1-diagnostics.patch)处理两个独立问题：

1. 后处理器工厂不再要求提前创建 `List<GroupedOpenApi>`；处理器通过
   `getBeanNamesForType(..., allowEagerInit=false)` 检查已有分组定义/单例。
   保留旧列表构造器及其 null 输入兼容性；无分组时仍注册默认分组。
2. 多分组管理资源新增空后缀的 **GET** 映射，仅选择已有的 `springdocDefault` 分组，
   使固定 `/actuator/openapi` 可读；不提供任意 URL、路径或分组透传，不增加重定向。
   入口沿用原 `/actuator/**` JWT 管理员规则，未新增公开 permitAll。

[准备脚本](../../scripts/prepare_springdoc_patch.py)核对官方 v3.1.1 三份源码的固定 SHA256，
应用补丁并编译 10 个 class；产物只放在临时项目的 `target/springdoc-patched-classes`。
Maven 缓存 jar 保持原样。Querydsl/Data REST/Reactor 等额外输入只用于 javac 编译完整原配置类，
由独立[编译 POM](../../examples/project-matrix/springdoc-compile-pom.xml)解析，**不进入目标 JVM classpath**，
不修改本项目 `pyproject.toml`/`uv.lock` 或应用 POM。

验收 harness 在启动前核对补丁摘要及各 class 的哈希，再将这些 class 放在原依赖之前。
结果摘要保存相同 manifest，明确标注本地补丁，避免把它当成未经修改的上游版本验收。
Java 编译报告了上游 `RestControllerEndpoint` 的弃用警告；未更换其 API，后续 Boot/springdoc 版本需另验。

### 补丁处理器对照

[SpringdocPatchedProbe.java](../../examples/project-matrix/SpringdocPatchedProbe.java)
调用真实补丁处理器，测试无分组、显式分组定义、配置文件分组及旧 null 列表构造器。
四项均通过；显式分组 supplier 被设置为一旦实例化即失败，实际未触发。
记录见[四项摘要](../../examples/project-matrix/springdoc-patched-probe-verification.json)。
这些对照不启动服务器、不使用目标响应或凭据。

### 真实官方 SDK 验收

[独立端口摘要](../../examples/project-matrix/jhipster-separate-port-remediation-verification.json)
完成 **18 次真实工具调用，全部验收通过**：

- 启动无原构造异常；544 个 Bean、632 条依赖。启动器比较实际业务/管理端口，摘要明确 `portMode=separate`，并有验收断言。
- Bean 和 OpenAPI 分别验证匿名 **401**、有效非管理员 JWT **403**；管理员可读取固定文档入口。
- 原生 `/api/admin/users` 的 OpenAPI 操作与 `AdminUserDTO` 均为 1 项、ok / complete。
- Liquibase 返回 **8 条 APPLIED**；不据此推断所有待执行迁移不存在。
- 配置默认关闭、精确登记属性/活动 profile、健康、startup、分页和漂移仍通过原有断言，必要 partial 缺口保留。

此前独立端口启动失败、关闭 Actuator 文档后的 404、同端口替代方案的摘要均保留，未覆盖为成功。

## 实际检查

| 检查 | 结果 |
| --- | --- |
| `uv run --no-sync python -m pytest -q` | **881 passed，35.33 秒** |
| `uv run --no-sync python -m mypy src/spring_runtime_mcp` | 53 个源码文件通过 |
| `uv run --no-sync ruff check src tests scripts` | 通过 |
| `uv run --no-sync ruff format --check src tests scripts` | 103 个文件通过 |
| `uv run --no-sync python scripts/validate_tool_contract.py` | 八工具、144+ 合成断言通过 |
| 原五项调查探针 | 退出 0，五项均不再复现；[新摘要](unresolved-review-remediation-2026-10-22.json) |
| 先前两个 OpenAPI 缺陷探针 | 退出 0；[新摘要](openapi-projection-remediation-2026-10-22.json) |
| 原生 Petclinic REST 复验 | **15 次通过**；[最终摘要](../../examples/project-matrix/petclinic-rest-final-remediation-verification.json) |
| 带本地 springdoc 补丁的 JHipster 独立管理端口 | **18 次通过**，含文档入口 401/403 |

两个最终真实摘要合计 **33 次调用**，均校验输出契约、安全门和包含文本副本、最长请求 ID、
服务端元数据的完整响应预算。合成 JWT/签名密钥仅在内存生成，没有保存原始响应、环境值树、
目标日志或异常栈。所有本轮目标进程由 finally 停止；未使用本轮 Docker 容器。

未更改打包配置/资源路径，未重新打包发布。默认 pytest 仍离线，不启动这些公开项目。
本轮只证明这些固定版本和临时配置；不宣称未打补丁的上游、所有自定义分组、TLS/生产环境或完整版本矩阵均通过。
固定默认入口需要 `springdocDefault` 分组；其他分组仍不由 MCP 任意选择或请求。

复现命令见[项目矩阵 README](../../examples/project-matrix/README.md#final-separate-port-remediation)。
