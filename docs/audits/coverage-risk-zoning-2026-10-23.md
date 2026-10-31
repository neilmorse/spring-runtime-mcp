# 历史覆盖率与风险分区 — 2026-10-23

## 记录状态与本次校正

原始记录基于 `master @ 49ffdb9` 加当时未提交工作树，记载 925 passed / 49.78s / exit 0。本次阶段 0 修订只核对文档、源码和已有报告，没有重新运行测试或采集覆盖率。

现有 `coverage.json` 的 metadata 为 coverage.py 7.17.0、branch_coverage=true，时间字段为 `2026-10-23T17:02:15.972546`（未携带时区）。报告没有绑定各源码文件哈希，不能证明它覆盖当前每一处未提交代码。下表是历史测量，不是当前安全验收。

本版保留原始数值表，撤回根据这些数值直接得出的“最高危”“边际收益最低”“全是 happy path”等未经行为核对的判断。当前依赖数、入口和数据流见 [系统地图](system-map-2026-10-23.md)；候选切口与确认顺序见 [接手说明](../RISK_ITEMS_HANDOFF.md)。

## 数据口径与复现限制

| 数据 | 原始方法 | 可解释范围 |
| --- | --- | --- |
| 行 / 分支覆盖 | coverage run --branch 后生成 JSON | 此次运行实际采集到的行和分支；子进程是否计入需另查采集配置 |
| commits | 六个月 Git 历史按路径计数 | 本仓当前共 15 次提交，不能代表长期修改趋势；未提交修改另计 |
| dir / via | 测试文件 AST import 与辅助模块引用闭包 | 测试文件数，不是测试用例数；不能证明某一分支已断言 |
| nkey | AST 关键构造探测行与 missing_lines/missing_branches 联合，连续区间聚类 | 启发式缺口数，不等于缺陷数；原始计算脚本未随记录提交，本次未复算 |

原 nkey 扫描涵盖 except、raise、else/elif、部分预算/边界比较、failed/partial 返回路径。它可能漏掉 continue、assert、动态调用和捕获分支的语义差异；不能宣称它是唯一有效指标。

`coverage.json`、`.coverage` 等是本地报告，不是已提交证据。原记录称 coverage 仅安装在 `.venv`，当前 `pyproject.toml` / `uv.lock` 未将其锁为开发依赖；复测前应确认环境中确有该工具。以下是历史采集命令，**本次未执行**，它们会写本地报告：

```bash
uv run --no-sync python -m coverage run --branch --source=src/spring_runtime_mcp -m pytest -q
uv run --no-sync python -m coverage json -o coverage.json
```

这只能重采行/分支覆盖，不能自动复现 nkey 或测试耦合指标。后续使用数据时需一并记录源码基线、工具版本、命令和子进程采集范围。

## 历史数值表

原分区定义：热为 commits≥3；“明”为行覆盖>80%且 nkey=0；红为热且盲，或热且明且边界；黄为非热且盲或仅间接测试；绿要求热、明、有直接测试且非边界。红-A 表示零直接测试，红-B 表示有直接测试。“准绿”和 ⚠️ 是原作者补充标签，不是新的测量值。

该分类把所有协议边界排除在绿区之外，也会因低提交次数低估公共契约风险；它只保留为历史标签，不决定实施顺序。`state` 是原测量时的 Git 状态。零分支文件的“100%”不表示实际执行了条件分支。

| 模块 | 行% | 分支% | nkey | commits | dir | via | state | 分区 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adapters/beans.py | 86.6 | 85.0 | 3 | 2 | 3 | 0 | clean | 黄 |
| adapters/conditions.py | 85.6 | 79.7 | 1 | 1 | 2 | 0 | clean | 黄 |
| adapters/config.py | 77.6 | 65.6 | 4 | 3 | 0 | 0 | clean | **红-A** |
| adapters/drift.py | 71.6 | 61.6 | 5 | 3 | 0 | 0 | clean | **红-A** |
| adapters/health.py | 88.2 | 78.8 | 1 | 3 | 0 | 0 | M | **红-A** |
| adapters/mapping_predicates.py | 97.2 | 91.9 | 4 | 0 | 0 | 0 | **??** | 黄 |
| adapters/mappings.py | 75.7 | 72.9 | 9 | 3 | 2 | 0 | M | **红-B** |
| adapters/migrations.py | 87.0 | 77.0 | **0** | 3 | 2 | 0 | clean | **绿** |
| adapters/openapi.py | 83.9 | 80.7 | 7 | 3 | 3 | 0 | M | **红-B** |
| adapters/source_catalog.py | 89.3 | 76.9 | 6 | 1 | 5 | 0 | clean | 黄 |
| adapters/startup.py | 83.7 | 76.6 | 3 | 3 | 1 | 0 | M | **红-B** |
| analyzers/bean_graph.py | 96.0 | 90.0 | 1 | 2 | 1 | 0 | clean | 黄 |
| analyzers/condition_failures.py | 84.5 | 81.2 | 1 | 1 | 1 | 0 | clean | 黄 |
| cli.py | 84.4 | 77.3 | 7 | 3 | 1 | 0 | M | **红-B** |
| contracts/definitions.py | 81.8 | 77.0 | **14** | 2 | 14 | 9 | M | 黄 ⚠️ |
| diagnostics.py | 94.2 | 78.6 | 3 | 1 | 0 | 0 | clean | 黄 |
| models/bean_graph.py | 100.0 | 100.0 | 0 | 1 | 1 | 0 | clean | 准绿 |
| models/common.py | 95.5 | 75.0 | 3 | 2 | 21 | 0 | clean | 黄 |
| models/conditions.py | 100.0 | 100.0 | 0 | 1 | **0** | 0 | clean | 黄 |
| models/queries.py | 100.0 | 100.0 | 0 | 1 | 8 | 0 | clean | 准绿 |
| models/source_catalog.py | 100.0 | 100.0 | 0 | 1 | 13 | 0 | clean | 准绿 |
| models/timestamps.py | 95.2 | 85.7 | 0 | 0 | 0 | 0 | **??** | 黄 |
| policy/configuration.py | 89.5 | 66.7 | 2 | 1 | 5 | 0 | clean | 黄 |
| policy/output_guard.py | 84.5 | 86.8 | 5 | 1 | 3 | 0 | M | 黄 |
| policy/sanitization.py | 93.6 | 90.8 | 6 | 3 | 16 | 0 | M | **红-B** |
| replay.py | 60.5 | 64.3 | **11** | 4 | 15 | 3 | M | **红-B** |
| server.py | 86.1 | **57.1** | 7 | **5** | 10 | 2 | M | **红-B** |
| services.py | 96.2 | **50.0** | 1 | 1 | 3 | 0 | clean | 黄 |
| snapshots.py | 89.8 | 76.6 | 9 | 2 | 13 | 0 | M | 黄 ⚠️ |
| tools/analyze_startup.py | 85.4 | 87.5 | 3 | 3 | **0** | 0 | clean | **红-A** |
| tools/check_migrations.py | 91.9 | 85.7 | 4 | 3 | **0** | 0 | clean | **红-A** |
| tools/detect_drift.py | 90.3 | 85.0 | 5 | 3 | 1 | 0 | M | **红-B** |
| tools/diagnose_health.py | 93.9 | **100.0** | 3 | 3 | **0** | 0 | clean | **红-A** |
| tools/inspect_beans.py | 88.5 | 81.9 | 9 | 3 | **15** | 5 | M | **红-B** |
| tools/inspect_config.py | 85.2 | 85.7 | 3 | 3 | **0** | 0 | clean | **红-A** |
| tools/registry.py | 96.3 | 83.3 | 1 | 2 | 14 | 0 | M | 黄 |
| tools/search_openapi.py | 85.4 | 83.3 | 3 | 3 | **0** | 0 | M | **红-A** |
| tools/support.py | 92.2 | 71.4 | 4 | 3 | 1 | 0 | M | **红-B** |
| tools/verify_mappings.py | 82.9 | 75.0 | 3 | 3 | **0** | 0 | clean | **红-A** |
| transport/actuator_http.py | 85.1 | 66.1 | **19** | 3 | 2 | 0 | clean | **红-B** |
| transport/bounded_json.py | 95.4 | 91.2 | 5 | 2 | 3 | 0 | clean | 黄 |
| transport/replay_files.py | 90.0 | 75.0 | 4 | 1 | 1 | 0 | clean | 黄 |
| transport/response_gate.py | 95.1 | 87.5 | 4 | 2 | **10** | 1 | clean | 黄 |
| transport/responses.py | 97.1 | 91.7 | 1 | 2 | 7 | 11 | clean | 黄 |
| transport/stdio.py | **28.6** | **0.0** | 1 | 1 | 0 | 0 | clean | 黄 |


## 对原解释的更正

| 原解释 | 当前核对结果 |
| --- | --- |
| server 分支覆盖 57.1% 全仓最低 | 表中 services 为 50%，transport/stdio 为 0%；撤回最低排名 |
| server 执行二分分页降级 | 条目减半在 tools/support.finalize 与 tools/inspect_beans._page；server 校验并替换超限协议结果 |
| Health 分支 100% 即异常路径都经过 | 历史 JSON 仍记录 missing_lines=[81,83,85]；这些行对应失败返回。行/分支数值本身有效，但不能单独证明异常路径覆盖充分 |
| 所有 Health 缺字段都应返回 MALFORMED_EVIDENCE | 非 dict 才在 adapter 入口抛 ValueError；缺 status、组件不可读、深度限制走各自 gaps，须逐条确认 |
| transport/stdio 的 run_stdio 由子进程测试驱动 | run_stdio 在 server.py；transport/stdio 提供 replay 的控制台隔离。子进程可能造成采集缺口，但本报告没有逐用例归因证据 |
| inspect_beans 的 RESPONSE_TOO_LARGE 是 20K visits 超限 | 该 `_page` 分支针对完整响应字节预算；不能与分析访问次数超限合并解释 |
| nkey=0 表示无风险 | migrations 仍有未覆盖分支；启发式扫描没有涵盖所有构造 |
| 直接 import 为零表示无测试 | 可经 registry、replay 或子进程间接驱动；导入数量也不表示断言质量 |
| 未跟踪的新模块使当前 HEAD 构建必然 ImportError | 未跟踪文件确有交付遗漏风险，但 HEAD 与当前修改文件集是不同基线；未构建 HEAD 就不能断言必然失败 |
| 应先提交新模块再谈测试 | 提交状态不替代行为确认、测试或验收；此记录不授权提交 |
| 只需 nkey 清零就能调整风险等级 | 原分区受热度、边界等多个条件影响，且 nkey 未复算；不能承诺自动升区 |

## 当前可采用的结论

- Health 的历史报告显示高覆盖率仍有异常返回行未执行，适合作为较小的行为确认候选；这不等于已确认其行为都应保持。
- HTTP 连接器、协议出口、契约验证、共享预算和脱敏具有跨工具影响，选取切口时要同时看影响范围与证据缺口。
- 原记录中的按行号推断、测试方案及优先级不能直接转成实现任务；阶段 1a 的行为确认先于新增特征测试。
- 本次未重算红黄绿数量、nkey、dir/via，也未声明历史覆盖率已更新。

## 相关记录

- [现状惯例](../../LEGACY_CONVENTIONS.md)
- [当前系统地图](system-map-2026-10-23.md)
- [候选风险项接手说明](../RISK_ITEMS_HANDOFF.md)
- [最终交付审计](final-delivery-audit-2026-10-23.md)（独立历史记录）
