# 风险项接手说明

修订日期：2026-10-30。本文保留阶段 0 的事实校正，并补充已有 Health 特征测试的当前状态；覆盖缺口本身不等于已确认缺陷。

原稿中的 Services 构造、错误信封断言、虚构 fixture 路径及预算注入参数与当前代码不符，本版用源码定位和待确认事项替代。历史覆盖率数值保留在 [覆盖率记录](audits/coverage-risk-zoning-2026-10-23.md)，本次未重新采集。

2026-10-30 追加：Health 组件不可读或状态缺失时，原处理器已返回 partial，但仍将可读条目数作为确切 totalMatched；现已将相关缺口传递到未知总数，保留可读条目。[回归测试](../tests/unit/test_health_incomplete_counts.py)覆盖过滤、正常空结果及真实 MCP 帧的快照续页。其他候选风险仍需按具体分支核对，不能由该修复推断均已覆盖。

同日连接器复核发现，拒绝的 HTTP 状态和不支持的 Content-Type 之前会先读取响应体；遇到缓慢错误页可将确定的拒绝变成超时。现改为先处理响应头并关闭连接，保留健康 503 正向读取；回归见 [合成响应测试](../tests/unit/test_http_rejection_read_budget.py)与自建回环测试。

后续编码复核发现，连接器此前忽略 Content-Encoding 声明，可能将声明为压缩的未解码数据当作 JSON。现支持缺省、identity 与单层 gzip，并独立限制压缩前后大小；不支持的编码链在正文读取前拒绝。响应头解析新增 32 KiB 累计预算。真实 TLS/SNI 矩阵及其他受授权约束的目标能力仍需独立处理。

本地连接复核还发现 socket 连接原未单独限制为 2 秒，已改为多个候选地址共享该时限；DNS 系统调用不能被强制终止。原读取器可能把 Content-Length 未收满但恰好可解析的 JSON 当成成功，现对普通及 gzip 响应返回 `INCOMPLETE_RESPONSE`。五种自建回环 TLS 证书场景已通过，不能外推为完整矩阵。

## 1. 第一候选切口：Health

| 位置 | 已观察到的行为 | 进入特征测试前要确认的范围 |
| --- | --- | --- |
| [diagnose_health](../src/spring_runtime_mcp/tools/diagnose_health.py) | 参数验证后按 application/liveness/readiness 选择端点；cursor 分支从内存续页 | 默认过滤、端点选择、游标行为 |
| 同上：NormalizationError | 先于 ValueError 捕获，保留 code；EndpointReadError 还保留 endpoint/http_status | 已知领域错误是否按现状保持 |
| 同上：TimeoutError | 返回 TARGET_TIMEOUT | 超时信封与取消的区别 |
| 同上：指定解析异常 | ValueError/TypeError/KeyError/RecursionError/UnicodeError → MALFORMED_EVIDENCE | 注入层次及安全错误投影 |
| 同上：Exception | 返回 INTERNAL_ERROR | 意外异常固定输出；不把异常字符串固化为输出 |
| [normalize_health](../src/spring_runtime_mcp/adapters/health.py) | 非 dict 抛 ValueError；缺 status、不可读 components、详情不可见、深度截断按不同 gaps 处理 | 缺字段与不可解析必须分别确认；不能统一断言失败 |

`failed()` 的现状见 [diagnostics.py](../src/spring_runtime_mcp/diagnostics.py)：除 INVALID_ARGUMENT 和两种 denied 码外，status 为 unavailable，coverage.state 为 unavailable，错误在 errors 数组中。原稿统一断言 `status=invalid`、`coverage.state=none` 不成立。

异常注入位置影响结果：在 transport 中抛 RuntimeError，通常先被 ResponseGateReader 转成 TARGET_CONNECTION_FAILED；这不能直接证明 Handler 的 INTERNAL_ERROR 分支。后续测试设计需区分传输边界、reader 边界和 adapter 边界。

## 2. 其余候选风险项

| 候选项 | 当前实现与风险依据 | 后续确认要点 |
| --- | --- | --- |
| [actuator_http.py](../src/spring_runtime_mcp/transport/actuator_http.py) | 共用只读连接器；历史报告记录 URL、DNS、peer、TLS 和取消路径的覆盖缺口 | 逐条对照 `_parse_base`、`_open`、`request`；不能把未覆盖直接写成安全缺陷 |
| [support.finalize](../src/spring_runtime_mcp/tools/support.py) 与 [server.py](../src/spring_runtime_mcp/server.py) | 前者减半条目数；后者校验完整协议帧并在最后出口超限时返回失败 | 分页成功、单项无法容纳、协议出口替换是不同路径；完整帧包含双副本及适用的 SDK 元数据 |
| [inspect_beans._page](../src/spring_runtime_mcp/tools/inspect_beans.py) | 响应超大时裁剪关联和条件；最终可返回 RESPONSE_TOO_LARGE | 不与 20,000 visits 的 AnalysisBudget/CallBudget 超限混为一谈 |

不以 nkey 为零、分支率 100% 或直接 import 测试数决定“无风险”。缺口需要与触发条件、真实断言和采集范围一起判断。

## 3. 可复用的现有接口与测试位置

| 对象 | 已确认的位置 / 接口 |
| --- | --- |
| Services | [services.py](../src/spring_runtime_mcp/services.py)：reader、catalog、sanitizer、snapshots，另有 targets/config_policy；没有 readers/policy 构造字段 |
| RuntimeReader | 同文件：异步 `read(target_id, endpoint_id, *, snapshot_id)` 返回 ParsedObservation |
| 协议测试辅助 | [tests/harness/host.py](../tests/harness/host.py) |
| 合成场景与 FixtureReader | [replay.py](../src/spring_runtime_mcp/replay.py)；[replay_files.py](../src/spring_runtime_mcp/transport/replay_files.py) |
| Health 现有配对测试 | [test_diagnostic_pairs.py](../tests/integration/test_diagnostic_pairs.py) |
| Health 已建立的特征测试 | [工具 A1–A16](../tests/unit/test_diagnose_health_characterization.py)、[适配器 A4–A12](../tests/unit/test_health_characterization.py)；文件注明 B1–B5 不在该基线中 |
| 回环 HTTP 与取消测试 | [test_mcp_host_and_http.py](../tests/integration/test_mcp_host_and_http.py) |
| 已有大响应契约测试 | [test_large_response.py](../tests/conformance/test_large_response.py) |
| 契约断言辅助 | [assertions.py](../tests/conformance/assertions.py) |

原稿引用的 `tests/harness/fakes.py`、`tests/fixtures/large_datasets.py` 不是现有资源，不作为复用前提。CallBudget 当前只有 deadline/visits 字段，没有 max_visits 构造参数；Handler 也没有 `_budget` 入参。测试中是否注入 scope、mock reader 或使用自建回环服务，要由具体行为清单决定。

当前锁定开发依赖不含 pytest-asyncio；已有测试使用 `asyncio.run`，不能直接套用未经配置的 `@pytest.mark.asyncio`。

## 4. 顺序与验证边界

1. 先核对已有 Health 特征测试和候选行为，不从头重复已完成的测试；B1–B5 尚未纳入上述基线，不能仅凭编号认定为缺陷。
2. 对剩余疑似问题记录输入、实际结果、规格依据和影响；先用合成数据复现，再决定是否补回归或修改实现。
3. 覆盖缺口本身不证明缺陷；涉及公开 Schema、依赖或核心保护区时遵循 [AGENTS.md](../AGENTS.md) 的授权与特征测试要求。
4. Python 改动执行全量离线 pytest、Ruff lint/format；类型、契约或打包改动另跑对应检查。

现有标准验证命令如下：

```bash
uv run --no-sync python -m pytest -q
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
```

覆盖率工具没有锁进开发依赖；覆盖率采集命令及工具版本条件见 [覆盖率记录](audits/coverage-risk-zoning-2026-10-23.md)。不预先承诺 nkey 清零、覆盖率百分比、用例数量或耗时，不以弱化断言、跳过测试达到目标。
