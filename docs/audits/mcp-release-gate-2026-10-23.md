# MCP 交付专项核验 — 2026-10-23

范围：`v0.2.0` 未发布工作树上的 MCP STDIO、只读与脱敏边界、wheel 净室资源。沿用此前审查修复，不覆盖用户改动。本轮不启动真实 Spring Boot、不访问生产实例、不提交、不发布，也不修改公开 inputSchema/outputSchema、运行依赖或目标白名单。

## 宿主与真实路由

- `src/` AST 安全测试禁止 `print()` 及非指定位置联网；源码没有 stdout logging handler。真实子进程逐行读取 stdout，初始化、发现、八次调用及进程结束后均检查协议流，额外输出会失败。
- 官方 SDK legacy 与 `2026-07-28` 两种模式完成发现、非法参数错误及配置能力默认关闭检查；原始管道另按 `2024-11-05` 完成握手。必须先读取 initialize 回复再发 initialized 通知和后续请求，不能把握手与全部调用一次性 `communicate()` 后马上 EOF。
- 八个名称均带 `springboot_` 前缀，按字母序返回；分别验证 input/output Schema 和四项风险注解。八次 `tools/call` 必须触达该工具对应的 fixture HTTP 端点，结构化结果与兼容文本副本相等，每帧不超过 16,384 UTF-8 字节。
- 移除宿主及注册表的缺处理器 `CAPABILITY_DISABLED` 占位。`build_server` 启动时要求处理器集合与契约精确相等，缺项、多项均失败；新增三个回归。配置诊断的 `CAPABILITY_DISABLED` 是真实处理器按默认关闭策略返回的安全拒绝，保留该行为。
- 仓库的英文 README 为 `README.md`，中文版为 `README.zh-CN.md`，不存在 `README.en.md`。客户端配置均运行常驻 `spring-runtime-mcp`，两份文档明确区分一次性 replay；没有将 replay 配成 MCP 服务。

## 只读、安全默认、有界输出

| 承诺 | 实现与验证 |
| --- | --- |
| 只读 | 连接器在打开连接前拒绝非 GET、重定向开关及未知逻辑端点；路径来自固定表，shutdown/loggers/heapdump/logfile 不在其中。startup 始终 GET。本轮八工具 HTTP 记录全部为固定路径 GET；安全回归另覆盖写方法与危险路径拒绝。 |
| 目标限制 | 当前实现仅允许 IPv4 回环或 `::1`（含安全处理的映射地址）；登记主机名的全部 DNS 地址先校验，再固定实际连接地址并核对 peer。没有开放非回环 IP 白名单能力。 |
| 重定向、代理、TLS | `http.client` 不使用环境代理，也不跟随 3xx；gate 将其转为固定错误；HTTPS 使用默认验证上下文及目标主机名。已有离线/自建回环安全回归验证这些边界。 |
| 配置默认关闭 | 不登记选择器时，官方 SDK 两模式调用均返回能力关闭；独立配置 CLI 集成测试只访问自身临时 HTTP fixture，确认授权后到达 env/configprops。移除该测试原本对固定 18081 端口的未知服务探测。 |
| 双层脱敏 | 自建 fixture 向 env/configprops 提供未掩码 password/secret/token/私钥头/JDBC 凭据，并使用与 Bearer 不同的合成秘密，检查 stdout/stderr 均不泄漏；已有安全测试另验证异常信封、出口拒绝与递归字段投影。没有输出完整配置值树。 |
| 有界与可追溯 | 全量离线测试覆盖 50 项分页、巨型 OpenAPI 引用/图预算、16 KiB 整帧和游标；安装包 replay 对 stripe-missing/factory-method 的借用样本明确断言 `coverage.gaps` 含 `FIXTURE_SUBSTITUTED`。该标记作为来源缺口保留，不据此捏造运行根因。 |

## 净室打包与资源

`pre_release_check.py` 的净室阶段现在逐字节比对 wheel 中的 `schemas/tools-contract.json`、`py.typed` 与源码内全部 replay JSON。任何漏打或内容不一致均失败；继续拒绝测试目录和缓存混入 wheel。

wheel 安装到新建临时 venv，用该环境的 `python -I` 从仓库外执行 `scripts/check_stdio_install.py`；宿主及 replay 的工作目录也为临时目录。检查器通过安装包的 `importlib.resources` 读取合成响应，仅启动自己拥有的随机回环端口 HTTP fixture。协议发现不触发目标读取，全部正常调用经生产宿主、reader、连接器及真实处理器执行。

replay 改用 `importlib.resources` 定位包内数据，保留原有目录 fd、`O_NOFOLLOW`、常规文件与读取上限检查；不依赖仓库 `tests/fixtures`。安装后七个公开场景均验证单行 JSON-RPC、非错误结果、结构化/文本副本一致，借用场景保留来源标记。

## 实际验证与修复过程

- `uv run --no-sync python scripts/pre_release_check.py --allow-dirty`：最终退出 0，六阶段完成；全量 **925 passed**，无 skip/xfail；mypy 53 个源文件、Ruff、wheel 净室协议与 replay 通过。唯一警告是明确允许的未提交工作树。
- `uv run --no-sync python scripts/validate_tool_contract.py`：八工具隔离 input/output Schema、144+ 合成断言通过。
- 首轮完整门禁没有通过：合成 PEM 头缺少 fake 标识被凭据扫描拦截，已明确标注为合成向量，未修改扫描规则；source catalog 的 ping 用例偶发在 EOF 前没有取得回复。后者改为读取实际回复后关闭输入，仍要求精确的一条成功响应、空 stderr 和退出码 0，没有弱化安全断言。
- 补充 configprops 独立秘密向量、配置 CLI 测试改为自建 fixture 后，定向复验 `test_cli_config_wiring.py`、`test_stdio_host_process.py`、`test_handler_registration.py`：**20 passed / 14.54 秒**；另跑 `check_clean_room_build`：wheel 资源比对、安装后完整协议检查和七场景 replay 再次通过。最终 Ruff lint/format 与 `git diff --check` 通过。

## 限制

- 结论仅覆盖当前锁定环境、合成数据及自建回环服务，不代表真实 Boot 版本矩阵、所有客户端、生产集群或长期稳定性。
- 本轮没有新增依赖漏洞审计；通用脚本仍可能跳过未安装的 pip-audit，动态版本只显示 dynamic。此前独立漏洞审计结果见[初轮报告](final-delivery-audit-2026-10-23.md)，不能将本轮脚本的 PASS 当作新一次完整 CVE 检查。
- 净室协议检查针对 wheel；本轮生成 sdist，但未再次安装 sdist。此前 sdist 安装证据保留在初轮报告。
- 支持普通 wheel 安装后的文件系统资源；自定义 zipimport 加载器若不暴露文件系统路径，replay 会安全拒绝。未新增 Windows 平台验收。
- 工作树尚未提交，版本仍为 0.2.0；本报告不表示已创建发布标签或获准部署/发布。
