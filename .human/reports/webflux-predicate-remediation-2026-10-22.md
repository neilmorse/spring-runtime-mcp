# WebFlux predicate 修复与复验 — 2026-10-22

本记录接续[失败原因调查](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/audits/webflux-predicate-investigation-2026-10-22.md)。本轮修复的是
WebFlux 函数式路由解析缺口；前轮综合审查的其他五项问题不在本补丁范围内。
公开 inputSchema/outputSchema、运行依赖、目标/IP 范围和目标暴露配置均未变。

## 行为变化

新增纯解析模块 [mapping_predicates.py](../../src/spring_runtime_mcp/adapters/mapping_predicates.py)，
由 mappings 归一化器调用，路由工具与漂移分析继续共用同一归一化过程。

- 识别正向 AND 的嵌套括号，保留已有扁平 `{GET [...]}` 语法。
- 识别 `Accept:` / `Content-Type:` 的单值及列表形式，使用已有 `header` 条件字段。
  多个可选媒体类型保留在同一条头条件内，不拆成多条 AND 条件；不将 Accept 当作已证明的
  响应 Content-Type。
- 方法集合在 AND 中取交集；不同路径的交集无法用当前替代路径列表准确表达时保持未知。
- 扫描器区分分组括号与路径变量、正则和媒体列表中的分隔符，不再无条件按逗号拆分。
- 限制输入 4,096 字符、分组/分隔符深度 16、叶子条件 32、语法节点 64、输出条件 16；
  同时消耗已有每调用分析预算，不执行目标文本。
- OR、NOT、自定义 predicate、引号媒体参数、结构不完整、缺失分隔符和无法表示的路径范围
  保持 `MAPPING_PREDICATE_UNPARSED` / `partial`。不制造方法与路径的笛卡尔积，也不把
  不完整结果写成完整的路由缺失。

## 离线验证

新增 [test_webflux_predicates.py](../../tests/unit/test_webflux_predicates.py)，共 **34 个合成用例**：
独立覆盖括号和 Accept 缺口、Content-Type、媒体列表、方法交集、带逗号的路径正则、
OR/NOT、自定义/非法语法、预算边界，以及路由过滤和漂移缺失判定。没有复制真实目标响应。
修复前最初 30 个新用例为 **20 failed / 10 passed**；随后补充 4 个语法/路径范围用例。

| 实际检查 | 结果 |
| --- | --- |
| `uv run --no-sync python -m pytest -q` | **816 passed，35.76 秒** |
| `uv run --no-sync python -m mypy src/spring_runtime_mcp` | 52 个源码文件通过 |
| `uv run --no-sync ruff check src tests scripts` | 通过 |
| `uv run --no-sync ruff format --check src tests scripts` | 95 个文件通过 |
| `uv run --no-sync python scripts/validate_tool_contract.py` | 八工具、144+ 合成断言通过 |

未更改构建/资源配置，未重复构建或发布；本轮不声称完成新的安装互操作或版本矩阵。

## 真实 WebFlux 复验

复用已授权、已缓存的 `gs-reactive-rest-service` 固定提交
`a6f4ff0c651545a14ff5d1f731fde9a8d136e4d5` 的临时副本，Boot **3.2.4** / Spring **6.1.5** /
Java **21**，以原业务 Java 源码和前次相同诊断配置启动。本轮没有下载 Maven 依赖，
没有增加数据库、Spring Security 或 springdoc。

官方 SDK 经真实 STDIO 宿主完成 **12 次工具调用**。`GET /hello` 现在返回：

- `status=ok`、`totalMatched=1`、`matchingComplete=true`；
- GET 方法及 `Accept=application/json` 头条件均被保留；
- `MAPPING_PREDICATE_UNPARSED` 从路由和漂移结果中消失。

验收脚本另增加 GET、完整匹配与 Accept 条件的断言，避免只凭路径出现就判定成功。
所有结果仍检查公开 Schema、脱敏和完整响应预算。原始
[失败摘要](../../examples/upstream-guides/verification.json) 保留不变；新的
[修复后摘要](../../examples/upstream-guides/webflux-remediation-verification.json)
独立保存，并明确标记诊断仓库使用未提交补丁。实际业务源码未变，Java 进程已停止。

Bean 基础设施依赖、未提供 SourceCatalog、未建模条件、隐藏健康信息、启动深度/分页和
配置嵌套形状的既有 partial 缺口仍保留。迁移和 OpenAPI 仅验收未暴露时的安全失败；
没有新增正向迁移/OpenAPI、认证、TLS、其他 WebFlux 或 Boot 版本的证明。
