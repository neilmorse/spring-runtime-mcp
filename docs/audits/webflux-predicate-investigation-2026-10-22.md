# WebFlux 路由验收失败原因 — 2026-10-22

本文保留修复前调查结果；后续实现与新验收见[修复记录](webflux-predicate-remediation-2026-10-22.md)。

## 结论与证据范围

Boot 3.2.4 / Spring Framework 6.1.5 / Java 21 的官方 Reactive REST 示例已启动，
`greetingHandler` Bean 和登记的 mappings 端点可读。验收失败发生在本项目
`adapters/mappings.py` 的函数式路由 predicate 解析，不是目标没有注册路由。
本轮仅研究原因，没有修改生产解析器或将失败验收改为通过。

本轮复用前次下载和构建的临时工程，仅重新启动这个可丢弃的回环实例，读取一次
登记的 mappings；没有执行示例业务 HTTP 客户端、请求业务 URL 或下载 Maven 依赖。
进程已停止。原始响应、predicate、日志和异常栈均未保存；以下语法示例使用自行构造的路径。

## 真实观察与框架源码对照

对实际响应只投影了固定字段和布尔事实：

| 核查 | 结果 |
| --- | --- |
| 包含已登记示例路径的 mappings 记录 | 1 条 |
| predicate 与依据示例源码、框架 `toString()` 规则构造的字符串完全一致 | true |
| 该记录包含结构化 `requestMappingConditions` | false |
| 当前 `_parse_predicate` 接受该记录 | false |
| 目标进程已停止 | true |

这与前次 [真实验收摘要](../../examples/upstream-guides/verification.json) 一致：
`guidePathTokenObserved`、`conjunctionObserved`、`acceptConditionObserved` 为 true，
`parserAcceptedGuidePredicate` 为 false。

Boot 3.2.4 的
[DispatcherHandlersMappingDescriptionProvider](https://github.com/spring-projects/spring-boot/blob/v3.2.4/spring-boot-project/spring-boot-actuator/src/main/java/org/springframework/boot/actuate/web/mappings/reactive/DispatcherHandlersMappingDescriptionProvider.java)
为函数式路由填写 `handlerFunction`，并把 `predicate.toString()` 放入 predicate；
注解映射分支才填写 `requestMappingConditions`。因此本例需要 predicate 回退解析。

Spring Framework 6.1.5 的
[RequestPredicates](https://github.com/spring-projects/spring-framework/blob/v6.1.5/spring-webflux/src/main/java/org/springframework/web/reactive/function/server/RequestPredicates.java)
中，`GET(path)` 本身是 method 与 path 的合取；再次 `.and(accept(...))` 形成嵌套合取。
`AndRequestPredicate.toString()` 为每次合取添加括号，单媒体类型的 accept 条件输出
`Accept: ` 加媒体类型。由此可构造以下**合成**等价形式：

```text
((GET && /diagnostic-example) && Accept: application/json)
```

## 两个独立缺口

1. **未解析嵌套括号。**
   [mappings.py](../../src/spring_runtime_mcp/adapters/mappings.py) 第 34–36 行只剥除一层
   外括号，随即按逗号或 `&&` 扁平拆分。上例第一个片段仍为 `(GET`，不能匹配 HTTP
   method，最终在条件正则分支返回失败。即使把 Accept 换成当前支持的条件，仍失败。
2. **不支持实际 Accept 条件语法。**
   第 12–19 行只接受 `consumes [...]`、`produces [...]`、`headers [...]`、
   `params [...]`。即使事先去掉嵌套层级，`Accept: application/json` 仍无法匹配。
   这两个问题需要分别修复，单独放宽其中一个不足以识别本例。

解析失败后，第 270–284 行清空路径、方法和条件并记录
`MAPPING_PREDICATE_UNPARSED`。随后 `/hello` 过滤无法命中，记录被跳过；工具返回
空 items，但保留 `partial` 与 `totalMatched=null`。这解释了验收的
`REGISTERED_ROUTE_NOT_RETURNED`，不应将空 items 解释为路由不存在。

漂移分析也复用 `normalize_mappings`，因此继承该缺口。
[drift.py](../../src/spring_runtime_mcp/adapters/drift.py) 的 `_route_records` 在解析不完整时
不会把未匹配预期生成为已观察到的 absent。因此此时 `missingInRuntime=[]` 不能证明
路由维度已完成匹配，必须同时看 coverage/gaps。

## 离线隔离复现与测试盲点

本轮用四个自行构造的字符串直接调用现有解析器，结果为：

| 合成输入 | complete | 原因 |
| --- | --- | --- |
| `(GET && /synthetic && produces [application/json])` | true | 当前支持的扁平形式 |
| `((GET && /synthetic) && produces [application/json])` | false | 仅增加嵌套就失败 |
| `(GET && /synthetic && Accept: application/json)` | false | 仅更换 Accept 语法就失败 |
| `((GET && /synthetic) && Accept: application/json)` | false | 与框架生成语法等价 |

实际执行 `uv run --no-sync python -m pytest -q
tests/unit/test_rw06_architecture_regressions.py -k functional_route`，结果
**1 passed，8 deselected**。该既有测试使用 `{GET [/functional/orders]}` 与
`{GET [/functional/items], produces [application/json]}`，能够验证这些扁平输入及未知
grammar 的 partial 行为，但没有覆盖框架生成的嵌套形式和 Accept 条件。
测试通过不能据此声明本例的函数式路由已支持。

## 建议修复范围（尚未实施）

- 用有长度、节点数和深度预算的分词/语法分析处理已知正向 AND 分组，不能只删括号。
- 显式识别 `Accept:` 和 `Content-Type:` 的单值/多值形式，按现有条件字段保留其
  请求匹配含义；不静默丢弃条件，不修改公开 Schema 来掩盖问题。
- OR、NOT、自定义 predicate 和无法完整建模的形式继续保留 unknown/partial。
  不将不同分支的路径与方法扁平做笛卡尔积，否则会制造不存在的路由组合。
- 增加上述两个独立最小回归、带过滤的工具回归，以及 OR/NOT/深度/分隔符边界用例；
  最后重跑同一真实 WebFlux 验收。保留当前失败记录，成功后另存新的验收记录。

本轮没有处理前次审查的其他五项问题，也没有扩大对其他 Boot/WebFlux 版本的支持结论。
