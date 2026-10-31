# 正式发布准备收口 — 2026-10-31

当前仍为 **0.2.0 Alpha、限定范围发布候选**。本报告保存前两轮本地验证与缺陷修复历史；本轮已获授权形成发布提交，并在该提交上运行不带旁路标志的完整门禁。最终提交 SHA、门禁退出码和同批产物 SHA256 写入仓库外的 `/tmp/spring-runtime-release-evidence/final-gate.json`，避免为补录结果改变被验证提交。只有该记录退出码为 0 才表示最终本地门禁通过。历史批次不作为最终发布产物。

## 本轮发布提交范围与流程

- 生产实现、全部关联离线测试、Schema/py.typed/replay 资源、发布脚本、锁文件和既有历史审计/修复记录成套纳入。已核对受改网络/协议/脱敏/分页边界、两个新增生产模块及对应回归，所有新增 Python/JSON 可解析，公开工具 Schema 无变化。保留原有暂存重命名，不删除用户文件，不将旧失败记录改写为成功。
- Nacos 的 `.stdout.log` 和逐分钟 `.jsonl` 保留磁盘，以两个精确 `.gitignore` 路径排除；只提交脱敏聚合 JSON 和报告。已将指向未交付 JSONL 的 Markdown 链接改为本地留存说明。现有缓存/coverage/JAR/target/build/dist 继续排除；sdist 继续排除所有 log/jsonl，wheel 仅运行包。既有 demo 的已跟踪协议 transcript 不删除，sdist 仍排除 JSONL。
- 材料检查另确认 springdoc 与 Fineract 历史补丁需要保留原始上下文空白：以精确路径 `.gitattributes` 排除源码空白规则，不改补丁字节；四份非空补丁均通过 `git apply --numstat` 语法解析。ThingsBoard 旧补丁为空，已撤下 README 的 `git apply` 命令并明确该历史 profile 复现材料不完整，不影响限定范围的 Python/fixture 发布验收。
- 提交按逐文件审核清单显式暂存，不使用 `git add .` 或 `git add -A`。发布准备分支使用 `codex/release-*`；先在本地干净提交运行用户指定门禁，再仅推送该分支进行验证，不推正式标签、不触发发布。
- 新增 `.github/workflows/release-check.yml`：分支 push / workflow_dispatch 调用共享 checks 的 `full-release-gate: true`，运行 Python 矩阵、静态检查和完整联网审计门禁。它没有 publish job、`pypi` environment 或 `id-token: write`；发布 workflow 仍以 `verify-release: true` 额外强制版本标签匹配。两入口复用相同产物检查/隔离安装实现。官方 actionlint 临时二进制在仓库外执行（关闭外部 shellcheck/pyflakes 集成），退出 0。
- GitHub 实际仓库是 `neilmorse/spring-runtime-mcp`，旧 Kaelenx 地址重定向；插件连接只读，本机 gh 登录 neilmorse 且 REST 返回 admin/push=true。Actions 已启用、允许所有 actions；管理员查询 `environments` 返回 `total_count=0`，`pypi` 详情返回 404：这是当前未建立环境/保护规则的实际证据，不再仅标待核实。未擅自建立环境或授权。
- PyPI 项目和 0.2.0 JSON 端点均返回 404，只能证明本轮查询时未公开，不证明名称没有保留或一定可创建。PyPI 管理页要求登录，用户反馈无法加载该站点；账户角色及（含 pending）Trusted Publisher 无法核实。预期 publisher 参数为 owner `neilmorse`、repo `spring-runtime-mcp`、workflow `release.yml`、environment `pypi`；发布前须由有权限的操作者核实并配置。项目作者名和旧项目链接保留；`server.json` 的 `io.github.Kaelenx` 命名空间授权在后续 Registry 阶段另审，当前不执行 Registry。
- 其他客户端继续未验证；不新增支持范围、运行依赖、目标/IP/端点或资源预算。Codex 历史单调用探针不在本轮重复运行。

最终本地命令（输出目录须为空，不携带 --allow-dirty / --skip-build / --allow-skipped）：

```bash
uv run --no-sync python scripts/pre_release_check.py --audit --output-dir /tmp/spring-runtime-release-final
```

证据目录 `/tmp/spring-runtime-release-evidence/` 保存逐文件暂存清单、actionlint.log、final-gate.log、final-gate.json 和远端 CI/账户核实摘要；它不在 Git 或分发包中。门禁实际产物仅在 `/tmp/spring-runtime-release-final/`，发布前必须绑定最终提交并核对摘要。若远端运行发现新问题，修复形成新提交后重新完成完整门禁，旧批次作废。

仍阻断发布：最终本地完整门禁必须 exit 0；同提交的验证型远端 CI 必须成功；PyPI 登录/项目权限/Trusted Publisher 和 GitHub pypi 环境保护必须齐备。满足后才向用户请求批准推送 `v0.2.0`，不使用正式标签试运行。后续账户或验证结果写入外部证据记录，避免污染已验证提交。以下各节保留此前工作树证据，涉及“未提交”“未执行远端”“待人工决定”的描述以其历史阶段为准。

## 基线与交付关系

HEAD 为 `49ffdb9cdcd905666fef93ce2a3cc13ab3872280`，实际验收对象为其上的用户工作树加本轮补丁，不是该提交单独通过。本地 `git tag --list` 为空；不推断远端标签状态。版本源 `src/spring_runtime_mcp/__init__.py`、动态 Hatch 元数据和 `server.json` 均为 0.2.0；继续保留 Alpha。OS Independent 是元数据，不是 Windows 验收证明。

保留全部既有变更及暂存重命名。旧盘点见 [工作区清单](worktree-inventory-2026-10-30.md)，它是历史快照。本次提交选择必须人工审阅：

| 交付组 | 必须成套审查的内容 |
| --- | --- |
| 生产代码与资源 | 全部 `src/spring_runtime_mcp/`；未跟踪的 `adapters/mapping_predicates.py` 与 mappings 一起交付，`models/timestamps.py` 与 server/contracts/startup/drift 一起交付；Schema、`py.typed`、全部 replay JSON 不可遗漏。 |
| 回归测试 | `tests/unit/test_webflux_predicates.py`、`test_mappings_servlet_coverage.py` 对应 mappings；health 的 characterization/incomplete_counts 对应 health；http_connect_deadline/http_rejection_read_budget 对应连接器；openapi_projection_safety、remaining_findings、production_chaos_repairs 对应既有修复；handler_registration、cli_startup_contract 与集成测试对应宿主/CLI；pre_release_check 对应门禁。完整 tests 应随候选审阅。 |
| 发布必需 | pyproject、uv.lock、LICENSE、双语 README、CHANGELOG、server.json、三个 workflows、pre_release_check/validate_tool_contract/check_stdio_install；本报告及关联发布草稿。 |
| 历史与可选材料 | docs/audits 的原失败及修复/复验报告、examples 各矩阵和对应探针脚本成组审阅，是否全部纳入 Git 仍由用户决定；不删除原始失败。 |
| 不进入分发包 | .env、凭据、缓存、数据库、JAR、target/build/dist、日志与 JSONL；sdist 新增排除规则，原日志不删除。Nacos stdout.log 是否纳入 Git 仍须单独人工审阅。wheel 仅含运行包与元数据；sdist 包含测试、脚本、文档和示例的获选文本材料。 |

## 范围与证据

状态分开标记；“本轮验证”仅指合成 JSON/自建回环 fixture，不是重新运行 Java 项目。

| 维度 | 已实现 / 本轮验证 | 历史固定样本 / 实验性 / 未实现 / 未验证 |
| --- | --- | --- |
| OS、Python | 本轮 Linux x86_64、Python 3.12.15 | Python >=3.11 为声明范围；CI 配置 3.11–3.14，本轮远端未运行；Windows/macOS 未验证。 |
| Boot、Java | 本轮不启动 Boot/Java；使用内置 2.7 servlet、3.4 servlet、4.1 WebFlux 合成 replay | 历史真实样本包括 Boot 3.5.16 / Java 21 / MVC / JWT / 临时 PostgreSQL；其他项目样本见 CHANGELOG 和对应报告。WebFlux 属有限样本/实验性适配，不承诺完整 Boot/Java/MVC/WebFlux 组合。 |
| 认证与目标 | 回环、无认证或登记环境变量 Bearer；本轮验证隔离安装的 fixture 链路与脱敏 | Basic、自定义头、非回环/生产访问未实现，不在首发范围。 |
| 管理路径和端口 | 固定 `/actuator` 与逻辑端点，启动时登记 origin 及端口 | 自定义管理基路径未实现。独立管理端口历史有固定样本及上游补丁限制，不代表自动发现；不扩大端口或路径白名单。 |
| OpenAPI | 固定 `/actuator/openapi`，有界解析、本地引用分析 | `/v3/api-docs` 候选/回退未实现；禁止远程 `$ref` 请求。 |
| 工具、安全 | 原有八工具，GET/HEAD、禁代理/重定向、TLS 校验、双层脱敏、16 KiB 完整工具回包；证据不足 partial/unknown | 配置诊断默认关闭，需预登记范围；未改公开 Schema、认证、预算、生产诊断算法或运行依赖。 |
| 官方 SDK | 锁定 mcp 2.3.0，legacy 与 2026-07-28 两模式；wheel/sdist 各自验收 | SDK 验收不是桌面客户端验收；不保证其他 SDK 版本。 |
| 实际客户端 | codex-cli 0.164.0 独立临时会话退出 0，真实调用一次自建 fixture `/actuator/health`；未修改全局配置 | Codex 全工具/续页/异常客户端交互未验证。VS Code 1.143.0 x64 仅发现安装，扩展列表未发现 Copilot；Claude/Cursor 命令未发现；这些客户端仍未验证。 |

## 已解决问题和 CI 门禁

- 中文 README 移除 `--no-project --with jsonschema` 的不完整依赖路径，源码启动使用锁定项目；wheel 入口与发布后的 PyPI 安装明确分开。replay 仍为一次性命令。
- 纠正发布草稿“已打标签”、Registry 已验和命名空间已授权的无当前证据表述。
- PR 流水线保留 3.11–3.14 离线测试/契约与 3.12 静态检查；正式发布额外调用 `pre_release_check.py --audit --output-dir dist`，不允许旁路标志。该脚本复用 Git/凭据及源码检查、离线锁检查、构建依赖固定校验、联网 audit、Ruff/mypy、契约、严格 pytest、构建、资源/版本比对、wheel/sdist 分别隔离安装及 SDK/八工具/replay。
- 门禁新增契约检查和已验证产物保留；失败安装不导出产物，非空输出目录拒绝覆盖。发布上传只取该目录的 wheel/sdist，publish 下载同一 artifact，不重新生成。标签同时匹配源码、Registry 及包版本。
- 凭据检查扩展到未忽略的新文件，仍为有限模式筛查，不能代替人工敏感材料审阅。新增回归验证契约失败阻断、产物导出/失败不导出及新文件盘点。
- 本轮没有执行 GitHub Actions，YAML 的本地审查不等于远端门禁通过。账户与索引访问不属于本轮自动执行。

## 实际验证记录

本节保留首次收口的历史证据；后续凭据扫描修复及当前指纹见末节，旧指纹和产物摘要不代表修复后源码。

环境：uv 0.13.6；Linux 6.18.59-1-lts x86_64 / glibc 2.44；Python 3.12.15；锁定 mcp 2.3.0、jsonschema 4.25.1。`uv sync --dev --locked --offline` 成功。网络仅用于依赖漏洞查询；测试网络仅为自建回环服务。未执行 npm/Maven 或真实 Spring 集成。

所有结果对应脏工作树，不作为干净提交的正式门禁证据。最终命令：

```bash
uv run --no-sync python scripts/pre_release_check.py --allow-dirty --audit --output-dir /tmp/spring-runtime-release-20261031-final
```

结果 **exit 2**：唯一 WARN 是脏工作树，其他阶段全部 PASS。首次检查为 1085 passed；补齐新文件扫描回归后，以最终 **1086 passed in 43.62s** 为准，没有 skipped/xfail。首次构建目录 `...-verified` 已由 `...-final` 取代，不用于发布。

| 实际子命令 / 检查 | 结果 |
| --- | --- |
| `git status --porcelain`、`git ls-files --cached --others --exclude-standard` 与内置敏感模式扫描 | 通过有限模式检查，工作树警告；未显示凭据内容。 |
| 生产 AST 检查、全量 tests 内已有源码 stdout/logger/只读安全断言 | 通过；未把可选启发式 `scripts/ai_audit.py` 当作已运行。 |
| `uv lock --check --offline`、固定构建依赖检查、`uv audit --locked` | 通过；联网审计无已知漏洞。没有把历史审计结果复用成本轮结果。 |
| `uv run --no-sync ruff check .`、`uv run --no-sync ruff format --check .` | 通过，包含 src/tests/scripts。 |
| `uv run --no-sync mypy` | 通过，按 pyproject 的 packages 配置覆盖 src 中 53 个生产模块，不声称测试类型验收。 |
| `uv run --no-sync python scripts/validate_tool_contract.py` | 八工具契约通过。 |
| `uv run --no-sync python -m pytest -q -ra --strict-markers` | 1086 passed，包含自建回环与安全断言。预期诊断拒绝及故障场景均由测试断言确认。 |
| `uv build --offline --out-dir <临时目录>` | wheel/sdist 构建通过，版本 0.2.0；比对 Schema、py.typed、全部 replay JSON。 |
| `uv export --frozen --offline --no-dev --no-editable --no-emit-project --no-hashes -o <约束文件>`，分别 `uv venv <临时环境>`、`uv pip install --python <隔离python> --offline -c <约束文件> <wheel或sdist>` | 两种产物独立安装通过，不使用项目 .venv 运行宿主。 |
| 两环境各自 CLI `--version`、`<隔离python> -I <仓库>/scripts/check_stdio_install.py --command <隔离入口>` | SDK legacy/2026-07-28、原始管道 initialize、排序八工具及四注解、八个 fixture HTTP 路由、文本与 structuredContent、stdout 纯协议、stderr 脱敏、16 KiB、七 replay 和退出清理均通过。 |
| 额外 zipfile/tarfile 逐字节检查 | 两产物全部 53 个生产 Python 文件与当前 src 一致，含两个未跟踪生产模块；sdist 无 log/jsonl/pyc。 |
| README 源码启动/一次性 replay | `uv run --locked --offline --project /home/neil/Projects/codcli/spring-runtime-mcp spring-runtime-mcp --version` 返回 0.2.0；中文 parent-child replay 示例以 `--locked --offline` 执行，JSON 工具结果 isError=false。未使用该命令访问既有目标。 |
| `git diff --check`、受改文档本地 Markdown 目标路径检查 | 通过；外部账户、Registry 在线 Schema、远端 CI 不据此判通过。未安装 actionlint，也未声称运行它。 |

普通元数据安装另做一次，明确不等同于联网用户安装：从 `/tmp` 新建 `/tmp/spring-runtime-release-user-20261031`，执行 `uv pip install --offline --python /tmp/spring-runtime-release-user-20261031/bin/python /tmp/spring-runtime-release-20261031-final/spring_runtime_mcp-0.2.0-py3-none-any.whl`，**没有 -c 约束**；随后该入口 `--version` 及隔离 Python `-I` 执行上述完整 check_stdio_install，均通过。解析使用本地缓存，mcp 2.3.0 / jsonschema 4.25.1，部分传递依赖与锁文件不同（如 opentelemetry-api 1.45.1、pydantic 2.14.1、sse-starlette 3.5.0、starlette 1.9.0）；uv 报告未缓存较新候选后选择可用缓存，未联网下载。该证据证明包元数据的缓存安装链路，不证明 PyPI 已发布或所有未来依赖组合。sdist 的无约束普通元数据安装本轮未验。

源码证据指纹（不含文档）：对 src/tests/scripts/.github/workflows 的所有文件（排除 __pycache__、pyc/pyo）及 pyproject.toml/uv.lock/server.json，按路径排序后顺序拼接 `相对路径 UTF-8 + NUL + 文件字节 + NUL`，251 个文件 SHA256：`b240b6c69581bdbad0bab7d108f9e1ead05d135aa780455e0cbe65d934d7b7c4`。最终报告在构建后补录证据，因此 sdist 内报告是补录前版本；正式发布必须在最终干净提交重建/重验，不能直接上传本轮临时产物。

| 已验临时产物 | SHA256 |
| --- | --- |
| `/tmp/spring-runtime-release-20261031-final/spring_runtime_mcp-0.2.0-py3-none-any.whl` | `c5575199a3fd4ef268cc561cfb4af7709a3f2c0e89e31e97275436011fbaa168` |
| `/tmp/spring-runtime-release-20261031-final/spring_runtime_mcp-0.2.0.tar.gz` | `d7c4c73d745fc5bd80f5fa869ce2dc566242e102a69d1fde8f5f682fb9721dda` |

完整门禁控制台记录在 `/tmp/spring-runtime-release-20261031-final-gate.txt`；临时目录不是持久发布存储。

## 实际 Codex CLI 探针

使用 OpenAI Docs 技能核对 [官方 MCP 配置文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)，并检查本地 `codex exec --help` 的临时配置参数。执行 `/tmp/spring-runtime-client-probe-20261031.py`（由 `uv run --no-sync python` 启动）：自建 127.0.0.1 随机端口 HTTP fixture，仅合成 health UP；创建仓库外临时 cwd；启动如下实际客户端，复用既有登录，不读取或输出凭据、不改全局配置：

```text
codex exec --ignore-user-config --ephemeral --skip-git-repo-check -s read-only -C <临时目录> --json
  -c 'mcp_servers.release.command="/tmp/spring-runtime-release-user-20261031/bin/spring-runtime-mcp"'
  -c 'mcp_servers.release.args=["--base-url","http://127.0.0.1:<随机端口>"]'
  'Acceptance test only. Use the release MCP server springboot_diagnose_health tool exactly once with empty arguments. Do not execute shell commands, read files or use other tools. Report its status and coverage.'
```

结果：codex-cli 0.164.0，宿主 0.2.0 / Python 3.12.15，exit 0，七个 stdout 客户端事件，观察到工具事件和恰好一次 fixture `/actuator/health` GET；未命中认证/连接错误。stdout 为 Codex 事件流，不是宿主 stdout 验收；宿主协议纯净性由独立管道门禁证明。此探针只证明一次真实客户端接入和路由，不代替 SDK 的完整字段断言，也不证明客户端所有工具/分页/错误模式。子进程正常退出，finally 关闭 fixture、socket 与线程，临时 cwd 自动清理；仅保留无原始响应的摘要 `/tmp/spring-runtime-client-probe-20261031-result.json`。未保留原始客户端日志。

## 发布阻断与人工清单

1. 人工决定历史矩阵、日志与未跟踪文件的提交范围，审核全部 diff，确保生产文件、资源、测试及发布脚本成套进入提交。不得自动暂存整个工作树。形成干净提交后运行 `uv sync --dev --locked` 和 `uv run --no-sync python scripts/pre_release_check.py --audit --output-dir <空产物目录>`，要求返回 0；记录最终提交 SHA 和产物 SHA256。
2. Codex 已有本轮真实单调用冒烟，不承诺完整客户端矩阵。若首发宣称 Claude/Cursor/VS Code 支持，先补对应验收；否则继续标未验证。最短人工步骤：在仓库用 `uv run --no-sync python -m pdb scripts/check_stdio_install.py --command <隔离入口>`，于当前脚本第 124 行设断点 `b 124` 后 `c`，以 `p server.server_port` 获取自建 fixture 端口；在客户端临时配置中登记 `<隔离入口> --base-url http://127.0.0.1:<端口>`。发现八工具后调用 health，记录客户端及宿主版本、结果和安全检查；关闭客户端，在 pdb 中 `clear`、`c` 让脚本跑完并清理 fixture。断点行随脚本变动需核实；不要修改全局配置或使用真实业务实例。SDK 脚本本身不能代替实际客户端。
3. 账户侧均为**待核实**：PyPI 项目名称/版本占用和发布权限；Trusted Publisher owner `Kaelenx`、repo `spring-runtime-mcp`、workflow `release.yml`、environment `pypi`；GitHub `pypi` 环境保护、审批人与 tag 权限。此为当时未访问账户的记录；本轮实际结果见开头流程章节。
4. 人工审阅远端发布门禁。当前 release.yml 的 `v*` 标签会自动走 OIDC 发布，不要用正式标签试跑未经批准的发布；先在独立无 publish 的验证分支/工作流确认 reusable checks 的 release gate 成功。远端 CI 成功及账户确认后，才由操作者批准发布。
5. 标签必须来自最终验证提交且等于 `v0.2.0`；提交后人工执行 `git tag -a v0.2.0 -m 'v0.2.0'`、推送提交/标签。不要覆盖既有远端标签。下载 workflow 产物并核对摘要与版本；发布后从仓库外全新环境按普通元数据安装 `spring-runtime-mcp==0.2.0`，复验版本与 STDIO，不携带诊断目标凭据。
6. MCP Registry：核对 server.json 当前官方 Schema、命名空间授权和 PyPI README 中 `mcp-name`；PyPI 可安装后，由有权限操作者审阅 metadata、登录 publisher 并发布。目录投稿/公告另行批准，本轮没有外部提交。

发布前失败：停止标签/发布，保留证据，修复后重新完成门禁。发布后缺陷：停止公告和 Registry 扩散，PyPI 由维护者按影响选择 yank（不是安全删除用户已安装版本），标注原因并发布更高补丁版本；不要重用版本或移动发布标签。Registry 由操作者同步撤回/更正；客户端回退到已验版本，保持只读安全约束。

已接受限制：本地回环、STDIO、固定路径和逻辑端点、Bearer 环境绑定、八工具、有限样本及缺证据降级。后续可选能力为远程目标、其他认证、自定义基路径、OpenAPI 回退和完整版本矩阵，均不以本轮名义实现或承诺。


## 验收反馈修复：Git 特殊路径漏检

验收发现 P2：原 `git ls-files` 输出采用 Git 引号转义，`splitlines()` 和路径 `is_file()` 会静默丢掉中文等文件名；这使此前有限凭据扫描存在漏检，不能据旧扫描结果声明此分支安全。

修复仅涉及 `scripts/pre_release_check.py` 和对应单测：清单使用 `git ls-files -z --cached --others --exclude-standard`，独立读取二进制 stdout，按 NUL 拆分后以 `os.fsdecode` 还原路径。不经过公共命令助手的 `.strip()` 或文本模式的换行转换。读取失败/超时或非零返回仍转为阻断，不输出 Git 原始错误内容。

新增 14 项真实 Git 回归：普通、中文、制表符、换行、回车、前导空格及尾随空格文件名，分别覆盖未跟踪和已提交干净仓库；每项检查文件清单与合成凭据的实际 FAIL 结果，不仅 mock 命令。修复前运行这些测试得到预期的 **12 failed / 2 passed**，修复后门禁单测 **38 passed**。

本次仍使用此前 uv.lock 环境：Linux / Python 3.12.15 / uv 0.13.6，HEAD 仍为 `49ffdb9cdcd905666fef93ce2a3cc13ab3872280` 上的脏工作树。修复后按上文同一算法得到 251 文件源码指纹 `a0820dabe0fde4c3ce9ea9e3bcedbd5cdd75a9ec9a81ca8c543ddbc20f34c003`。

实际检查：`uv run --no-sync python -m pytest -q tests/unit/test_pre_release_check.py` 38 passed；`uv run --no-sync ruff check src tests scripts` 通过；`uv run --no-sync ruff format --check src tests scripts` 124 文件通过；直接调用当前工作树 `check_git_and_secrets(Path.cwd(), allow_dirty=True)` 返回 WARN，唯一原因是 115 处工作树变更；`git diff --check` 通过。`uv run --no-sync python -m pytest -q` 全量 **1100 passed / 43.74 秒**。

本轮没有重跑 mypy、契约、联网漏洞审计、构建/隔离安装或实际客户端：没有 src、Schema、依赖或打包配置改动，之前结果仅保留为历史证据。旧 sdist 包含修复前的脚本、测试和报告；wheel 的运行源码未变，但仍不能用旧批次摘要替代最终发布批次的验证。正式发布仍须在干净提交执行完整门禁、验证远端 CI，并核实 PyPI/OIDC 账户；没有提交或发布。
