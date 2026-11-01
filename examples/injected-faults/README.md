# 隔离故障注入验收

本目录保存固定场景的安全聚合证据。三个 opt-in 脚本通过真实 MCP STDIO 调用工具；Java 故障只注入临时副本或临时覆盖层，退出时清理本轮进程。默认 pytest 不构建或启动 Spring 项目。

主代理独立复跑及最终检查汇总见 [acceptance-results.json](acceptance-results.json)。汇总只描述记录中的一次验收，不替代重新执行。

| 分支 | 实测范围 | 证据 |
| --- | --- | --- |
| 构建与旧运行态 | demo 的语法/类型编译失败、缺失依赖及多候选 Bean 启动失败；源码未重建及重建后未重启两阶段本地摘要和路由对照 | [build-results.json](build-results.json) |
| 真实运行态 | demo 条件 Bean、路由、健康与漂移故障/恢复；Flyway 错误迁移与构造器循环启动失败及恢复；JDK 原始类型告警；Admin 健康组件故障/恢复 | [runtime-results.json](runtime-results.json) |
| 合成响应 | 401/403/302、HTML、重复 JSON 键、非法 UTF-8、断流、健康 503、OpenAPI 引用和秘密/指令 canary；逐错误恢复 | [protocol-results.json](protocol-results.json) |

编译器/启动器的固定标记只证明注入发生；启动失败时 MCP 仅报告端点不可用，不输出编译或启动根因。旧运行态中的 `sourceRevision` 是调用者声明，`POSSIBLE_NOT_RESTARTED` 只作为 candidate。运行态结果中的 `partial` 和 unknown 保留实际证据缺口；健康 DOWN 是有效诊断，不是工具调用错误。

## 复跑

从仓库根目录执行。首次按[验证流程](../../docs/launch/README.md)同步锁定环境。demo 需要 Java 21、Maven 及已缓存的 demo 构建依赖；脚本使用 Maven offline 并跳过上游测试，不能据此声称上游测试通过。构建分支使用 Linux `/proc` 核对监听进程归属。

每次选择新的输出路径；`passed=true` 且退出 0 才表示该次验收通过。保存的 JSON 不是当前工作树自动通过的证明。

```bash
uv run --no-sync python scripts/check_injected_build_faults.py \
  --output /tmp/injected-build-new.json
uv run --no-sync python scripts/check_injected_runtime_faults.py \
  --admin-project /absolute/cache/spring-boot-admin \
  --source-catalog examples/injected-faults/generated-source-facts/source-catalog.json \
  --output /tmp/injected-runtime-new.json
uv run --no-sync python scripts/check_injected_protocol_faults.py \
  --output /tmp/injected-protocol-new.json
```

将 `/absolute/cache/spring-boot-admin` 替换为已准备的缓存路径。Spring Boot Admin 复用 [large-project-matrix](../large-project-matrix/README.md) 的固定源码与原生构建缓存，只在临时目录编译额外启动器、安全过滤器和健康组件。实际源码 SHA、Boot jar 版本及本轮命令见[运行态说明](runtime/README.md)和报告；不重新构建整个 Admin 源码，不更改原缓存。

本轮运行态验收显式加载[生成的 catalog](generated-source-facts/source-catalog.json)，其原始文件摘要与缺口见[静态报告](generated-source-facts/source-facts-report.json)，漂移输入见[生成参数](generated-source-facts/drift-arguments.json)。条件来源采用[操作者登记](source-condition-bindings.json)，不从 Bean 名猜测。以下命令生成新副本；输出目录必须不存在：

```bash
uv run --no-sync python scripts/generate_source_facts.py \
  --project-root . --context-id demo \
  --source examples/spring-boot-demo/src/main/java/example/PaymentGateway.java \
  --source examples/spring-boot-demo/src/main/java/example/StripeClient.java \
  --source examples/spring-boot-demo/src/main/java/example/StripePaymentGateway.java \
  --source examples/spring-boot-demo/src/main/java/example/StripeConfiguration.java \
  --source examples/spring-boot-demo/src/main/java/example/OrderController.java \
  --condition-sources examples/injected-faults/source-condition-bindings.json \
  --output-dir /tmp/generated-source-facts-new
```

支持范围见[静态事实生成](../../docs/source-facts-generation.md)；源码/产物摘要的证据边界见[本地构建证据](../../docs/build-evidence.md)。运行实例的构建身份仍为未采集，本地重建不证明旧 JVM 加载了新字节。

合成协议分支直接计量接收的完整 JSON-RPC 工具帧；构建分支同样检查线帧。SDK 驱动的运行态分支检查两份内容相等，并以最大允许请求 ID 重建完整帧校验预算，其 `reconstructedFrameBytes` 不是抓取的原始线帧长度。各分支检查输出 Schema 和独立安全门，失败只写固定分类及安全聚合事实。

默认回归只运行自建合成回环服务：

```bash
uv run --no-sync python -m pytest -q tests/integration/test_injected_fault_acceptance.py
```

该组含拒绝损坏 Schema、秘密/指令泄漏和安全失败报告的负向断言。真实运行态本轮覆盖 demo 和 Admin 两个项目；迁移失败使用临时 H2，不代表外部数据库中断或生产数据库验收。未覆盖所有 `examples` 项目、完整版本矩阵或所有静态 Java 分析规则。OpenAPI 复杂引用故障来自合成 fixture，不是原生项目生成文档的验收。
