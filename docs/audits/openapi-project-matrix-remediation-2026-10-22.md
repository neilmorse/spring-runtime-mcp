# 较大项目 OpenAPI 修复与复验 — 2026-10-22

后续状态见[遗留问题闭环修复](remaining-findings-remediation-2026-10-22.md)：此前五项问题已修复，
JHipster 的独立管理端口已在本地 springdoc 补丁变体完成验收。下文保留前轮范围与当时限制。

接续[初轮真实矩阵](../../examples/project-matrix/README.md)。用户明确要求修复；
保留初轮失败摘要和其他未提交改动。未改变公开工具 Schema、运行依赖、连接器端点或 IP 白名单。

## 两个诊断实现缺陷

1. **重复引用输出不是树**：引用目标查找缓存返回同一个原始 Schema，投影时直接借用了
   `required`、`enum`、数组形式 `type` 的列表。两个引用分支因此共享可变节点，触发
   `NON_TREE_JSON`。现在每个分支独立复制这些列表，只接受有界标量成员，限制分别为
   50、16、7，并逐成员消耗现有查询分析预算。嵌套容器、非法成员或超限元数据省略并标注
   `OPENAPI_SCHEMA_PARTIAL`；预算耗尽保留 `REF_EXPANSION_LIMIT`。没有放宽树校验。
2. **业务字段名和说明字段混淆**：`properties.description` 的值是业务字段的 Schema 对象，
   脱敏器却把它当成迁移记录的说明文字清空为 null。现在属性映射仅接受经过名称过滤的
   Schema 对象，并在进入对象时重置字段上下文；输出安全门作同样的结构区分。
   对象内部继续完整递归检查，真实 `description` 注解及其他原始说明文本仍被省略/清空，
   敏感属性名与凭据仍被拒绝或脱敏。`comments`、`stackTrace`、`properties` 等同名业务字段
   也不能改变其 Schema 内容的检查语义。

新增 [21 个合成回归](../../tests/unit/test_openapi_projection_safety.py)，覆盖独立可变节点、
源文档不变、共享及二阶引用、JSON Pointer 转义、循环与深度上限、分析预算、非法/超限元数据、
业务字段名冲突、说明/凭据注入、脱敏幂等和完整工具出口。未保存真实响应为 fixture。
最初 17 个用例在修复前为 14 failed / 3 passed；随后补充了完整工具出口及三种引用深度。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| `uv run --no-sync python -m pytest -q` | **837 passed，36.37 秒** |
| `uv run --no-sync python -m mypy src/spring_runtime_mcp` | 52 个源码文件通过 |
| `uv run --no-sync ruff check src tests scripts` | 通过 |
| `uv run --no-sync ruff format --check src tests scripts` | 98 个文件通过 |
| `uv run --no-sync python scripts/validate_tool_contract.py` | 八工具、144+ 合成断言通过 |
| `uv run --no-sync python scripts/probe_openapi_matrix_findings.py` | 退出 0；树结构与 description Schema 均保留 |

未改打包配置/资源路径，未重新构建、发布或提交。默认 pytest 继续完全使用离线合成数据及自建回环服务。

## Petclinic REST 真实复验

复用初轮固定提交和原生 Boot **4.1.1** / Java **21** / H2 / springdoc **3.1.1**，
业务源码和 POM 均未改动。官方 SDK 通过真实 STDIO 完成 **15 次调用，全部验收通过**。
独立保存[修复后摘要](../../examples/project-matrix/petclinic-rest-remediation-verification.json)，
不覆盖初轮失败记录。

| OpenAPI 查询 | 修复前 | 修复后 |
| --- | --- | --- |
| Owner GET 操作 | `NON_TREE_JSON` | 1 项；partial，显式 Schema/引用深度缺口；完整响应 14,360 字节 |
| `Owner` Schema | `OUTPUT_CONTRACT_VIOLATION` | 1 项；partial，显式 Schema 投影缺口；完整响应 6,402 字节 |
| `Specialty` Schema | 成功 | 1 项；ok / complete；完整响应 3,278 字节 |

验收通过代表结构、安全、预算及预期事实均成立；复杂 Schema 的 partial 没有改写为完整证据。
未暴露迁移路径的目标 HTTP 500 行为仍保留，诊断结果仍是安全的 unavailable。

## JHipster 启动原因与可用配置

初轮独立管理端口失败发生在 MCP 调用之前。已安装的 springdoc **3.1.1** 字节码与
[同版本工厂方法源码](https://github.com/springdoc/springdoc-openapi/blob/v3.1.1/springdoc-openapi-starter-common/src/main/java/org/springdoc/core/configuration/SpringDocConfiguration.java)
一致：`springdocBeanFactoryPostProcessor3` 在 BeanFactory 后处理阶段直接依赖
`List<GroupedOpenApi>`，提前创建 JHipster 分组配置。已安装的 JHipster framework **9.4.0**
配置类仅有接收 `JHipsterProperties` 的构造器；该次启动最终在增强配置类上寻找无参构造器失败。
[对应处理器](https://github.com/springdoc/springdoc-openapi/blob/v3.1.1/springdoc-openapi-starter-common/src/main/java/org/springdoc/core/configurer/SpringdocActuatorBeanFactoryConfigurer.java)
使用分组列表判断是否应注册默认分组。结合条件及实际因果类型，这支持“分组 Bean 过早创建”的
原因判断；没有据此声称所有 JHipster/springdoc 配置都失败。

本轮没有替换/修补第三方 jar。新增显式的
[同端口验收配置](../../examples/project-matrix/jhipster-same-port.properties)：

- 业务与 Actuator 共用一个随机回环端口，保留原生 `dev,api-docs`；覆盖 dev 组以避免载入上游样例秘密配置。
- `springdoc.use-management-port=false`，通过受信配置把原生文档挂载到固定 `/actuator/openapi`。
- 沿用已授权的 `/actuator` 命名空间补丁及原 JWT 管理员规则，保持缓冲启动、内存 H2 和真实同步 Liquibase。
- 原生 POM、Boot 4.1.1、framework 9.4.0、springdoc 3.1.1 与业务代码保持；没有新增运行依赖。

这是避开失败组合的配置方案，**独立管理端口 + 原生分组的第三方初始化问题仍未修复**。
同端口结果不替代初轮原配置的失败记录，也不代表生产隔离方案。

最终[同端口摘要](../../examples/project-matrix/jhipster-same-port-verification.json)记录 **18 次调用**：
552 个 Bean / 663 条依赖，Bean 与 OpenAPI 分别验证匿名 **401**、有效非管理员 JWT **403**，
管理员可读取原生 OpenAPI 操作及 `AdminUserDTO`，二者均为 1 项 / ok / complete；
Liquibase 返回 **8 条 APPLIED**，不据此推断待执行迁移不存在。
所有调用检查输出契约、输出安全门及含重复文本/请求 ID/服务端元数据的 16,384 字节完整响应预算。

本轮两个最终真实摘要合计 **33 次调用**。签名密钥/JWT 只在内存生成；只保存有界事实，
没有原始响应、目标日志、异常栈或 env 值树。目标进程在 finally 停止；没有新建 Docker 容器。
此前五项独立审查问题仍未包含在本补丁中，也未新增 TLS、生产目标或完整版本矩阵的证明。

后续[遗留问题调查](unresolved-findings-investigation-2026-10-22.md)进一步以最小生命周期实验和
真实独立端口对照确认启动原因，并复现此前五项缺口；关闭 show-actuator 虽能启动，固定文档入口仍为 404。
