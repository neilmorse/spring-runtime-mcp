# Agent 工作规则

本项目将登记 Spring Boot 回环实例的 Actuator/OpenAPI 数据转换为八个只读 MCP 工具。
按 [文档导航](docs/README.md) 读取相关章节；范围见 [SPEC](SPEC.md)，字段以工具 Schema 为准，勿全量预读。
代码行为变化时同步相关现状文档；文档只写已实现行为和限制，历史原因与未来想法不进入现行说明。
`.human/`、`CHANGELOG.md` 默认禁止读取或检索，用户明确指定时才按范围访问；ignore 不构成访问控制。
跨阶段任务才使用 `.agent/PLANS.md`；execplan 仅按当前任务引用读取，旧记录不延续授权或待办。

## 实现与安全
Python 使用四空格、类型注解和 snake_case，公共 JSON 使用 camelCase；遵循现有模块职责，保留用户改动。
适配器签名各异，修改前核对实际输入输出；接口与错误传递见 [实现约定](docs/architecture/implementation-conventions.md)。
缺失证据沿 gaps/Fact 传至信封层，使用 null、unknown/partial；禁止用空字符串、默认值或空结果伪造确定结论。
新增错误码在 `diagnostics.py` 预定义并匹配 `[A-Z][A-Z0-9_]{0,63}`；生产环境变量只在 `cli.py` 读取。
私有辅助函数加 `_`，类型守卫内联，不新增独立 `type_guards.py`。
修改 Bean/条件/漂移/OpenAPI 时，逐项核对 [图、三值条件与引用规则](docs/architecture/cross-version-normalization.md)，完整可见关联先于分页。
目标与端点只能来自登记配置；只读 GET，禁止写请求、重定向、环境代理、任意 URL/路径/头透传和远程引用；禁止绕过鉴权、TLS/peer、脱敏及预算。
外部响应经双层脱敏；禁止泄露凭据、原始 env/configprops 值树、异常栈或远端指令；禁读 heapdump/原始 logfile，配置诊断默认关闭。
stdout 仅输出 JSON-RPC，脱敏日志写 stderr；八工具按名称排序并保留四项风险注解，maxResults 默认/上限 50，完整双副本回包上限 16,384 字节。
保留 totalMatched、truncated、coverage、nextAction 及未知证据语义；网络与输出细节见 [安全架构](docs/architecture/security-and-sanitization.md)。
核心保护区（均在 `src/spring_runtime_mcp/`）：`models/`、`policy/sanitization.py`、`diagnostics.py`、`transport/actuator_http.py`、`transport/response_gate.py`、`server.py`。
核心分支修改须已有特征测试或明确授权；模块覆盖率低于 80% 或关键 except/raise/边界分支未覆盖时，先补特征测试。
新增 catch-all 先说明原因并确认；保留既有协议/工具固定错误转换及连接器清理后重抛路径。
未授权的公开 Schema、运行依赖、目标/IP 范围、暴露/采集配置、重启或发布变更，先准备具体补丁与影响再确认；同范围授权不重复询问。

## 验证与交付
使用 uv.lock 锁定环境；首次 `uv sync --dev --locked`，缓存齐全后加 `--offline`。默认测试仅用合成数据和自建回环 fixture；真实实例另行授权。
按 [验证流程](docs/launch/README.md) 选检查：Python 跑 pytest、Ruff lint/format；src 类型改动加 mypy；Schema/校验脚本加契约检查；打包/资源改动加构建与 wheel 资源检查。
纯文档只查措辞、路径和链接；检查通过即收口。禁止弱化安全测试或虚报检查、兼容性及根因；不擅自提交、推送或发布。
完成已授权编辑、验证与必要修复后交付行为变化、实际检查和剩余限制；阻塞仅暂停对应分支，继续可独立工作。
