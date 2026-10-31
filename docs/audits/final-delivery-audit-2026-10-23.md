# 交付前总核验 — 2026-10-23

对象：`master` 提交 `49ffdb9` 及其未提交工作树。范围：功能闭环、边界防御、安全脱敏、测试真实性、净室构建、文档与版本一致性。本轮只做离线测试、本地构建和净室安装，不启动真实诊断目标、不连接生产实例、不发布。

后续的 MCP 宿主、只读脱敏与 wheel 资源专项复核见 [MCP 交付专项核验](mcp-release-gate-2026-10-23.md)：补齐自动净室协议/八工具/replay 检查，并移除缺处理器的旧占位分支。下文数字保留本报告初轮结果。

结论：离线交付面通过；发现并修复 3 个代码/交付问题（`--source-catalog` 无界读取、CLI 启动错误不可定位、缺少 `--version`），并关闭开发依赖 pytest 的已知漏洞。公开 inputSchema/outputSchema、八工具排序、只读 GET、回环目标、16 KiB 结果预算和脱敏边界均未改变。真实目标与生产矩阵不在本轮结论内。

## 1. 功能闭环与零伪实现

- `src/` 内无 `TODO`、`FIXME`、`HACK`、`XXX`、`NotImplementedError`、`breakpoint()` 或 `pdb.set_trace()`。
- 八个公开工具全部绑定在 `tools/registry.py` 的 `HANDLERS`；未知工具返回协议错误 `UNKNOWN_TOOL`，已声明但未实现的分支返回受控 `CAPABILITY_DISABLED`。
- 生产源码的第三方导入只有 `mcp` 与 `jsonschema`，均在 `pyproject.toml` 的运行时依赖中；开发依赖 `pytest`、`mypy`、`ruff` 均被使用。未发现幽灵依赖或误放在 dev 组的运行时包。
- `replay_data/` 只被独立的离线 replay 入口使用；在线宿主始终装配真实 `ActuatorHttpTransport`，没有 Mock/夹具回退。
- 配置诊断默认关闭：未注册选择器时 `springboot_inspect_config` 返回 `CAPABILITY_DISABLED`；`--config-allow-values` 单独出现会在启动阶段被拒绝。`env`/`configprops` 只在显式登记后进入读取能力集合。

## 2. 边界防御与优雅降级

| 边界 | 实际约束 |
| --- | --- |
| 工具输入 | 8 个 inputSchema 均 `additionalProperties: false`；`maxResults` 1–50、`maxDepth` 0–16、字符串长度/正则/枚举完整；`validate_arguments` 另限 12 个顶层键、深度 8、序列化 16 KiB |
| HTTP | 默认 5 秒，范围 `(0, 60]`；连接、读取、TLS 握手共用单调时钟 deadline；工具总预算 15 秒；每目标两个读取槽 |
| 上游响应 | 最多读取 8 MiB + 1 字节；要求 JSON 或 Actuator v2/v3 media type；拒绝重定向、401/403、非 JSON、重复键、NaN、非树结构与超深/超节点 JSON |
| 回包 | 整帧 `structuredContent` + 文本副本 + serverInfo 最多 16,384 UTF-8 字节；超限先对半缩页，单条仍超限则返回 `RESPONSE_TOO_LARGE` |
| 游标 | 60 秒绝对 TTL、32 MiB LRU、偏移续页；查询摘要绑定全部非游标参数；凭据/策略变化后整快照复验或清理 |
| 资源释放 | `http.client` 连接在 `finally` 关闭；超时/取消通过 `abort()` 关闭 socket；replay 文件描述符逆序关闭；`quiet_console` 在 `finally` 恢复 fd |
| 路径 | 工具参数不能选 URL、路径或请求头；replay 读取使用 `O_NOFOLLOW`、目录 fd 逐段打开、仅常规文件、8 MiB 上限 |

本轮修复：CLI 原用 `Path.read_bytes()` 读取 `--source-catalog`，在超大文件、FIFO 或设备文件上可能无界占用或阻塞。现改为 `os.open(..., O_NONBLOCK)` + `fstat` 常规文件校验 + 256 KiB 分块上限读取；非文件、超限、目标不匹配均在启动阶段以 exit 2 退出，不进入 STDIO 循环。

残余限制：操作员可用主机名登记目标，`getaddrinfo` 由工作线程执行；请求和事件循环受 deadline 约束，但操作系统级解析线程不能在 Python 内强制终止。解析阶段仍受循环回环校验和 peer 校验保护。

## 3. 安全红线与隐私脱敏

- 扫描 Git 全部 33 个提交与 370 个当前文件，未发现真实私钥、云/代码托管平台令牌或 `.env`/keystore 文件。命中的 PEM/Bearer 均为 `tests/security/` 和 `tests/unit/test_sanitization.py` 的合成脱敏向量；`examples/tdd-runtime/DiagnosticsLauncher.java` 只从临时数据库对象读取生成密码，没有字面量。
- 私网 IP 扫描的 3 处命中均已核实：`tests/security/helpers.py` 的 SSRF 测试地址，以及 `derby-10.14.2.0.jar` 版本号被四段 IP 正则误报。没有真实内网地址。
- 清理了文档中 9 处用户主目录绝对缓存路径，统一为 `~/.cache/...`。
- `SanitizerPipeline` 字段白名单/凭据掩码与 `output_guard` 独立出口检查均保留；生产源码没有 `print`/`logging`；STDIO stdout 只写 JSON-RPC，固定错误提示写 stderr 且不回显值、路径、堆栈或远端文本。
- 工具没有文件读写或命令执行入口；迁移/配置读取均为只读 Actuator GET，不拼接 URL、不跟随重定向、不使用环境代理。
- `uv audit` 初次发现 pytest 8.4.2 的 2 条 `PYSEC-2026-1845`（tmpdir 处理），已升级至 9.0.3；复查 40 个已解析包无已知漏洞。运行时依赖与传递依赖无告警。

## 4. 测试真实性与覆盖质量

- 全量 **922 passed**，0 failed、0 skipped、0 xfailed；`--strict-markers` 生效。
- Mock 使用审计：`conftest.py` 只禁网；少量 `monkeypatch` 用于禁 DNS、模拟时钟/预算/拒绝连接或注入故障；没有把被测核心算法替换成 Mock 的测试。
- 真实链路：E2E 直接调用真实工具处理器并校验 outputSchema/两种文本表示；STDIO 测试启动真实子进程；HTTP 集成测试启动自身回环 fixture 服务；conformance 覆盖 8 工具 Schema、错误信封、16 KiB 预算、分页与多版本 fixtures。
- 新增 9 个 CLI/版本回归：`--version` 与 `__version__`/wheel 元数据一致、缺失令牌变量、非法超时、非回环 origin、超大/非文件/目标不匹配的 source catalog，以及启动错误不回显令牌。
- Node 入口的 5 个红队向量（network/readonly/leakage/injection/stdio）在 pytest 9.0.3 下 5/5 通过。
- mypy strict 53 个源文件、Ruff 113 个文件、8 工具契约（144+ 断言）全部通过。

## 5. 净室构建与安装

- `uv build` 成功：wheel 118 项、约 182 KB；sdist 约 0.74 MB。两者均含 `spring_runtime_mcp/schemas/tools-contract.json`、`py.typed` 和 `replay_data`；不含 `__pycache__`、`.pytest_cache`、`tests/fixtures` 缓存、`examples/**/target/` 或 27 MB 示例 jar。
- wheel 与 sdist 分别安装到全新临时 venv（不依赖源码目录）：`spring-runtime-mcp --version` 输出 `0.2.0`；安装包内 `replay` 可读取 `replay_data` 并返回 3,398 字节的合法 JSON-RPC frame，结构化结果与文本副本一致。
- 使用官方 SDK 客户端对安装后的入口做 legacy 与 `2026-07-28` 两种协议发现和工具错误检查，均通过。
- `uv lock --check` 通过；`pre_release_check.py` 6/6 阶段通过（工作区未提交仅记为 WARN）。

## 6. 文档、配置与版本一致性

- 新增 `--version`；`__init__.py`、wheel 元数据、CLI 输出均为 `0.2.0`。Git 当前没有标签，因此没有 tag/版本可比较；发布时应先决定是否升版并创建匹配的 `vX.Y.Z` 标签。
- README、README.zh-CN、SPEC 的参数表已补充 `--version`；默认值 `127.0.0.1:18081`、5 秒、`maxResults=50`、16 KiB、15 秒工具预算与代码一致。
- 修正 SPEC 的过期复现命令：类型检查改为 `mypy src/spring_runtime_mcp`；默认 pytest 范围包含 conformance 与自建回环/子进程集成测试；演示校验改为 `scripts/check_demo_app.py`；移除“`--version` 未交付”的过期表述；CI 描述与实际工作流一致，不再声称默认 CI 启动真实 Spring 组合。
- CLI 启动失败现在按参数给出可读提示（例如 `--token-env` 变量缺失、`--timeout` 越界、`--source-catalog` 非文件/超限/目标不匹配、非回环 `--base-url`），不打印底层异常栈。
- 本地 Markdown 链接检查覆盖 41 个文档、0 个断链；本轮新增的路径替换未引入失效链接。

## 修复清单

| 文件 | 变化 |
| --- | --- |
| `src/spring_runtime_mcp/cli.py` | 有界读取 source catalog；具体且含值最小化的启动错误；`--version` |
| `tests/unit/test_cli_startup_contract.py` | 9 个启动/版本/边界回归 |
| `tests/integration/test_cli_config_wiring.py` | 适配新的启动错误契约，仍检查无 traceback |
| `tests/integration/test_stdio_host_process.py` | 适配启动错误文案，并加强“不回显令牌/路径”的断言 |
| `pyproject.toml`、`uv.lock` | pytest 8.4.2 → 9.0.3 |
| `tests/security/redteam-audit.test.ts` | 同步 pytest 固定版本 |
| `README.md`、`README.zh-CN.md`、`SPEC.md`、`CHANGELOG.md`、`HANDOVER.md`、`.agent/PLANS.md` | 参数、验证结果与交接状态 |
| 6 个审计/示例文档 | 用户主目录绝对缓存路径 → `~/.cache` |

## 实际验证

| 检查 | 结果 |
| --- | --- |
| 全量测试 | **922 passed / 0 failed / 0 skipped**，33.54 秒 |
| 类型 | mypy strict，53 个源文件通过 |
| Lint / 格式 | `ruff check`、`ruff format --check` 通过，113 个文件 |
| 契约 | 8 个 input/output Schema，144+ 断言通过 |
| 锁文件 | `uv lock --check` 通过 |
| 漏洞 | `uv audit`：40 个包，无已知漏洞 |
| 构建 | wheel/sdist 成功；资源齐全，无缓存/构建产物 |
| 净室 | wheel + sdist 全新 venv 安装、CLI、两种协议、replay 通过 |
| 红队入口 | Node 5/5（network/readonly/leakage/injection/stdio） |
| 文档 | 41 个 Markdown 文件本地链接 0 断链 |

## 未解决限制

- 本轮没有重新启动真实 Spring Boot 目标；真实项目矩阵、生产规模、长期稳定性和完整版本矩阵仍以既有审计报告的固定样本为限。
- `pre_release_check.py` 的版本阶段对动态版本只打印 `dynamic`，且 `pip-audit` 未安装时静默跳过；本轮用 `--version`、wheel 元数据测试、`uv audit` 和独立净室命令补齐。后续若把它作为唯一发布门禁，应先修复这两个盲区。
- 本机未安装 gitleaks/trufflehog；本轮使用等价的 Git 全历史正则、文件名与当前文件扫描。`git grep` 不检查二进制 blob，也未覆盖仓库外的构建缓存或凭证。
- 依赖审计覆盖 `uv.lock` 中的 Python 运行时与开发依赖；示例 Maven 工程和 GitHub Actions 未做独立 CVE 扫描。
- `uv audit` 依赖 OSV 数据且仍标记为 experimental；“无已知漏洞”不等于无漏洞。
- 历史审计文档保留当时的 pytest 8.4.2 固定命令作为证据；当前复现以 `uv.lock`、README 和本报告为准。
- sdist 按 `pyproject.toml` 声明包含 tests/docs/examples，属于源码分发的内容选择；已确认不包含构建产物或缓存，但不是最小分发包。
- 版本 0.2.0 尚未对应 Git 标签，本轮未提交、未发布。
