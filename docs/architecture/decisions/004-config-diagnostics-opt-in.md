# ADR 004: 配置诊断默认关闭

**状态**：已接受

**日期**：2024-11

---

## Context（上下文）

配置诊断工具 `springboot_inspect_config` 可以查询：
- 配置属性来源（`/actuator/env`）
- 绑定的配置类（`/actuator/configprops`）
- 属性有效值（可选，需显式授权）

关键风险：
1. **敏感信息泄露**：配置可能包含密码、密钥、令牌
2. **上游数据量大**：`env` 和 `configprops` 返回完整配置树
3. **隐私边界不清**：操作者可能无意暴露内部配置
4. **脱敏不完美**：复杂配置结构可能绕过脱敏规则

现有措施：
- 双层脱敏管道
- 值默认隐藏（`includeValues: false`）
- 输出字段投影

但仍需额外防护层。

## Decision（决策）

配置诊断功能 **默认关闭**，需要通过 CLI 参数显式启用：

### 1. 三种登记方式

```bash
# 方式 1：注册前缀（需要多次 --config-prefix）
--config-prefix spring.datasource \
--config-prefix app.feature

# 方式 2：注册单个属性（需要多次 --config-property）
--config-property server.port \
--config-property server.ssl.enabled

# 方式 3：注册 profiles（布尔开关）
--config-profiles
```

### 2. 值输出需额外授权

```bash
# 允许经脱敏的值输出
--config-allow-values
```

### 3. 工具查询与策略取交集

- 工具参数：`prefix: "spring.datasource"`
- CLI 登记：`--config-prefix spring --config-prefix app`
- 实际查询：`spring.datasource`（在登记范围内）

### 4. 未启用时返回错误

```json
{
  "status": "unavailable",
  "errors": [{
    "code": "CAPABILITY_DISABLED",
    "message": "Configuration diagnostics require opt-in",
    "remediation": {
      "action": "configureCapability",
      "configKeys": ["--config-prefix", "--config-property"]
    }
  }]
}
```

## Consequences（后果）

### 正面影响

1. **安全默认**
   - 未授权时无法访问配置
   - 避免无意泄露敏感信息

2. **显式授权**
   - 操作者明确知道允许查询的范围
   - 登记范围形成审计记录

3. **渐进授权**
   - 先授权前缀/属性（不含值）
   - 再授权值输出（`--config-allow-values`）

4. **防御纵深**
   - CLI 授权 + 脱敏管道 + 字段投影
   - 多层防护降低泄露风险

### 负面影响

1. **额外配置步骤**
   - 首次使用需要重启 CLI
   - 增加接入复杂度

2. **范围管理**
   - 操作者需要提前知道要查询的前缀
   - 动态扩展范围需要重启

3. **文档负担**
   - 需要明确说明启用方法
   - README 强调默认关闭

### 缓解措施

1. **清晰错误提示**
   - `CAPABILITY_DISABLED` 包含启用方法
   - 配方提供具体 CLI 参数示例

2. **文档前置**
   - README 在 "Boundaries" 章节说明
   - 工具 Schema 文档强调前置条件

3. **常见前缀建议**
   - 文档提供常见前缀列表（`spring`、`server`、`management`）
   - 演示示例包含配置诊断场景

## 替代方案

### 方案 A：默认开启，但值隐藏

- **优点**：接入简单，无需额外配置
- **缺点**：仍可能泄露属性名称和来源，范围不受控

### 方案 B：不提供配置诊断

- **优点**：最安全
- **缺点**：无法排查配置覆盖问题，功能不完整

### 方案 C：只读 `/actuator/env/{property}`

- **优点**：按需查询，减少数据量
- **缺点**：仍需授权机制，增加 API 复杂度

### 决策理由

选择默认关闭是因为：
- **安全优先**：配置是最敏感的运行时数据
- **显式好于隐式**：操作者明确授权，不会无意暴露
- **审计友好**：CLI 参数形成可审计的授权记录
- **渐进开放**：先授权前缀，再授权值

## 相关决策

- [ADR 005: 仅连接回环地址](005-loopback-only-targets.md) - 另一层安全边界

## 实现细节

- CLI 参数解析：`src/spring_runtime_mcp/cli.py`
- 策略定义：`src/spring_runtime_mcp/policy/configuration.py`
- 能力检查：`src/spring_runtime_mcp/tools/support.py` (`read_checked`)
- 投影逻辑：`src/spring_runtime_mcp/adapters/config.py`

### 策略结构

```python
@dataclass
class ConfigReadPolicy:
    prefixes: frozenset[str]
    properties: frozenset[str]
    allow_values: bool
    profiles: bool
```

### 检查逻辑

```python
if endpoint_id in {"env", "configprops"} and services.config_policy is None:
    raise EndpointReadError("CAPABILITY_DISABLED", endpoint_id)
```

## 典型用例

### 用例 1：排查数据源配置

```bash
# 启动时授权
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-prefix spring.datasource
```

```json
// 查询
{
  "prefix": "spring.datasource",
  "includeValues": false
}
```

### 用例 2：检查单个属性来源

```bash
# 启动时授权
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-property server.port
```

```json
// 查询
{
  "propertyKeyPattern": "server.port"
}
```

### 用例 3：查询配置值（高风险）

```bash
# 启动时授权（需要 --config-allow-values）
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-prefix app.feature \
  --config-allow-values
```

```json
// 查询
{
  "prefix": "app.feature",
  "includeValues": true  // 仅当 --config-allow-values 时有效
}
```

## 用户反馈

监控以下指标评估决策影响：
- `CAPABILITY_DISABLED` 错误频率
- 配置诊断使用率
- 用户反馈（接入复杂度）
- 安全事件（配置泄露）
