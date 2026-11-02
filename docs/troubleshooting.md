# 故障排查手册

本手册按错误码分类提供排查步骤和解决方案。所有错误码定义见 [diagnostics.py](../src/spring_runtime_mcp/diagnostics.py)，配方细节见[工具调用策略](contracts/tool-calling-policy.md)。

## 目录

- [参数与查询错误](#参数与查询错误)
- [目标与授权错误](#目标与授权错误)
- [端点访问错误](#端点访问错误)
- [网络与超时错误](#网络与超时错误)
- [数据与预算错误](#数据与预算错误)
- [游标与分页错误](#游标与分页错误)
- [安全与脱敏错误](#安全与脱敏错误)

---

## 参数与查询错误

### INVALID_ARGUMENT

**含义**：参数不符合工具契约

**常见原因**：
- 缺少必需参数
- 参数类型错误
- 参数超出范围或长度限制
- 筛选条件冲突（如 `schemaName` 与 `operationId` 同时提供）

**排查步骤**：
1. 检查工具 Schema 定义：`src/spring_runtime_mcp/schemas/tools-contract.json`
2. 确认必需参数已提供
3. 验证参数类型和范围（如 `maxResults` 为 1-50，`maxDepth` 为 0-16）
4. 对 OpenAPI 操作查询，至少提供 pathPattern 或 operationId；schemaName 与操作查询互斥。路由工具允许只按 httpMethod 查询。

**错误示例（springboot_search_openapi）**：

```json
{
  "httpMethod": "GET"
}
```

**正确示例（springboot_search_openapi）**：

```json
{
  "pathPattern": "/api/users",
  "httpMethod": "GET"
}
```

**相关文档**：
- [工具调用策略](contracts/tool-calling-policy.md)
- [各工具 Schema 说明](contracts/tools-schema/)

---

## 目标与授权错误

### TARGET_NOT_REGISTERED

**含义**：目标未登记

**常见原因**：
- CLI 启动时未指定 `--base-url`
- `targetId` 参数与 CLI 登记的目标不匹配

**排查步骤**：
1. 检查 CLI 启动命令是否包含 `--base-url`
2. 确认 `targetId` 参数（默认 "local"）与 CLI 配置一致
3. 检查环境变量 `SPRING_RUNTIME_BASE_URL` 和 `SPRING_RUNTIME_TARGET_ID`

**解决方案**：
```bash
# 启动时指定 base-url
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081
```

**相关文档**：
- [首次接入](first-query.md)
- [目标配置](target-app-setup.md)

---

### CAPABILITY_DISABLED

**含义**：能力未启用（通常指配置诊断）

**常见原因**：
- 调用 `springboot_inspect_config` 但未通过 CLI 参数启用配置诊断
- 未登记任何配置前缀、属性或 profiles

**排查步骤**：
1. 检查 CLI 启动命令是否包含配置诊断参数
2. 确认登记的范围覆盖查询的属性

**解决方案**：
```bash
# 启用配置诊断（需要多次 --config-prefix）
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-prefix spring.datasource \
  --config-prefix app

# 或使用 --config-property
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-property server.port

# 允许值输出（可选）
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-prefix spring.datasource \
  --config-allow-values
```

**相关文档**：
- [配置诊断工具](contracts/tools-schema/springboot_inspect_config.md)
- [CLI 参数说明](first-query.md)

---

### ENDPOINT_UNAUTHORIZED

**含义**：端点未授权（401/403）

**常见原因**：
- 目标应用需要 Bearer 认证但未提供
- 提供的令牌无效或已过期
- 端点启用了额外的访问控制

**排查步骤**：
1. 检查目标应用的 `management.security` 配置
2. 确认 CLI 启动时是否指定 `--token-env`
3. 验证环境变量中的令牌有效性

**解决方案**：
```bash
# 设置 Bearer 令牌
export MY_TOKEN="your-bearer-token"
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --token-env MY_TOKEN
```

**目标应用配置**：
```yaml
# application.yml - 最小暴露原则
management:
  endpoints:
    web:
      exposure:
        include: beans,conditions,mappings,health,startup  # 按需添加
  endpoint:
    health:
      show-details: when-authorized
      show-components: when-authorized
```

**注意**：
- 不要使用 `include: "*"`，会暴露 heapdump、env、configprops 等敏感端点
- `show-details: always` 会暴露健康详情给所有人，应使用 `when-authorized`
- 401/403 通常是 Bearer 令牌问题，应先检查 `--token-env` 配置

**相关文档**：
- [目标配置](target-app-setup.md)
- [安全架构](architecture/security-and-sanitization.md)

---

## 端点访问错误

### ENDPOINT_NOT_EXPOSED

**含义**：端点未暴露（404）

**常见原因**：
- 目标应用未暴露所需端点
- `management.endpoints.web.exposure.include` 配置不包含该端点

**排查步骤**：
1. 检查目标应用的 `management.endpoints.web.exposure.include` 配置
2. 确认端点名称正确（如 `beans`、`conditions`、`mappings`）
3. 验证端点访问路径（默认 `/actuator/{endpoint}`）

**解决方案**：
```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: beans,conditions,mappings,health,startup,flyway,liquibase,env,configprops,openapi
      base-path: /actuator  # 确认基路径
```

**按工具检查**：
- `springboot_inspect_beans` → 需要 `beans`（可选 `conditions`）
- `springboot_verify_mappings` → 需要 `mappings`
- `springboot_diagnose_health` → 需要 `health`
- `springboot_check_migrations` → 需要 `flyway` 和/或 `liquibase`
- `springboot_analyze_startup` → 需要 `startup`
- `springboot_inspect_config` → 需要 `env`、`configprops`
- `springboot_search_openapi` → 需要 `openapi`

**相关文档**：
- [目标配置](target-app-setup.md)
- [各工具端点需求](contracts/tools-schema/)

---

### STARTUP_DATA_UNAVAILABLE

**含义**：启动数据不可用（startup 端点 404）

**常见原因**：
- Spring Boot 未配置启动事件采集
- `spring-boot-starter-actuator` 版本过低（< 2.7）
- startup 端点未暴露

**排查步骤**：
1. 检查 Spring Boot 版本（需要 2.7+）
2. 确认 `spring-boot-starter-actuator` 依赖
3. 检查 `management.endpoint.startup.enabled` 配置
4. 验证 `management.endpoints.web.exposure.include` 包含 `startup`

**解决方案**：
```yaml
# application.yml
management:
  endpoint:
    startup:
      enabled: true  # 启用 startup 端点
  endpoints:
    web:
      exposure:
        include: startup

spring:
  application:
    name: my-app
```

```java
// 主类中配置启动事件采集器
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(Application.class);
        // 配置 BufferingApplicationStartup（最多 2000 个事件）
        app.setApplicationStartup(new BufferingApplicationStartup(2000));
        app.run(args);
    }
}
```

**注意**：startup 端点只在应用启动时采集数据，重启后才有新数据。

**相关文档**：
- [启动瓶颈诊断](contracts/tools-schema/springboot_analyze_startup.md)
- [目标配置](target-app-setup.md)

---

### REDIRECT_BLOCKED

**含义**：重定向被阻止（3xx）

**常见原因**：
- 目标应用配置了 HTTPS 重定向
- 管理端口与业务端口不同，配置了跳转
- 基路径配置错误导致重定向

**排查步骤**：
1. 确认目标应用监听地址和端口
2. 检查是否有 HTTPS 强制重定向
3. 验证管理端点基路径

**解决方案**：
```bash
# 使用正确的协议和端口
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081  # HTTP
# 或
uvx spring-runtime-mcp --base-url https://127.0.0.1:18443  # HTTPS
```

**相关文档**：
- [安全架构](architecture/security-and-sanitization.md)

---

## 网络与超时错误

### TARGET_TIMEOUT

**含义**：目标超时

**常见原因**：
- 目标应用负载过高，响应慢
- 网络延迟
- 查询范围过大（如 `maxResults: 50` 且匹配大量数据）
- 依赖图遍历深度过大（如 `maxDepth: 16`）

**排查步骤**：
1. 检查目标应用 CPU/内存负载
2. 测试网络连接延迟（`ping`、`curl`）
3. 检查查询参数（`maxResults`、`maxDepth`、筛选条件）
4. 查看 CLI 超时配置（默认 5 秒，上限 60 秒）

**解决方案**：

**方案 1：优化查询参数**
```json
// springboot_analyze_startup：减少结果数量
{
  "maxResults": 10,  // 从 50 减少到 10
  "minDurationMs": 100  // 增加筛选阈值
}

// springboot_inspect_beans：减少遍历深度
{
  "packagePrefix": "com.example",
  "maxDepth": 2  // 从 4 减少到 2
}
```

**方案 2：核对超时发生的层级**

CLI `--timeout` 配置 reader timeout，默认 5 秒，允许大于 0 且不超过 60 秒。Services 单次读取另外强制最多 5 秒；工具总时限固定 15 秒，包含排队、多端点读取、分析和输出检查，不由 CLI 调整。

若此前主动将 reader timeout 调得更短，可以恢复默认 5 秒。对本来就超过 5 秒的端点，增大 CLI 参数不能延长 Services 的读取等待；应由维护者检查目标响应和负载。工具筛选和 maxResults 在本地应用，不会减少固定端点返回的原始数据量。

**方案 3：精化筛选条件**
```json
// springboot_inspect_beans：使用更精确的筛选
{
  "packagePrefix": "com.example.service",  // 缩小范围
  "beanNamePattern": "*Repository"  // 精确模式
}
```

**相关文档**：
- [工具调用策略](contracts/tool-calling-policy.md) - 15 秒总时限
- [系统概览](architecture/system-overview.md) - 读取槽和预算

---

### TARGET_CONNECTION_REFUSED

**含义**：连接被拒绝

**常见原因**：
- 目标应用未启动
- 端口号错误
- 地址不是回环地址（127.0.0.1 或 ::1）

**排查步骤**：
1. 确认目标应用正在运行
2. 验证端口号正确
3. 测试连接：`curl http://127.0.0.1:18081/actuator/health`
4. 检查防火墙规则

**解决方案**：
```bash
# 检查应用是否运行
ps aux | grep java
netstat -tuln | grep 18081

# 检查端点可访问性
curl -v http://127.0.0.1:18081/actuator/health
```

**相关文档**：
- [目标配置](target-app-setup.md)
- [安全架构](architecture/security-and-sanitization.md) - 回环地址限制

---

### TARGET_CONNECTION_FAILED

**含义**：连接失败

**常见原因**：
- 网络故障
- HTTPS 证书验证失败
- DNS 解析失败

**排查步骤**：
1. 检查网络连接
2. 对于 HTTPS，验证证书有效性
3. 检查 DNS 解析（如果使用域名）

**解决方案**：
```bash
# 测试 HTTPS 连接
curl -v https://127.0.0.1:18443/actuator/health

# 检查证书
openssl s_client -connect 127.0.0.1:18443 -showcerts
```

**相关文档**：
- [安全架构](architecture/security-and-sanitization.md) - TLS 验证

---

## 数据与预算错误

### RESPONSE_TOO_LARGE

**含义**：响应过大

**常见原因**：
- 单条记录过大（如 OpenAPI 文档巨大）
- 匹配记录过多且无法有效分页
- 完整 JSON-RPC 响应超过 16,384 字节

**排查步骤**：
1. 检查查询范围是否过大
2. 确认是否需要所有字段（如 `includeDetails: false`）
3. 查看 `maxResults` 是否可以进一步减少

**解决方案**：
```json
// springboot_inspect_beans：减少结果数量
{
  "maxResults": 5,  // 从 50 减少到 5
  "packagePrefix": "com.example.core"  // 精确范围
}

// springboot_verify_mappings：精确查询单个路由
{
  "pathPattern": "/api/users/{id}",
  "httpMethod": "GET"
}
```

**注意**：通用分页会收缩本页记录数，Bean 工具还可裁剪关联；不是所有工具都采用减半策略。仍无法满足完整帧预算时返回固定错误。

**相关文档**：
- [工具调用策略](contracts/tool-calling-policy.md) - 16 KiB 响应上限
- [实现约定](architecture/implementation-conventions.md) - 分页机制

---

### UNEXPECTED_CONTENT_TYPE

**含义**：不支持的媒体类型

**常见原因**：
- 端点返回非 JSON 内容
- 管理端点基路径配置错误，访问到业务端点
- 端点被代理或网关修改

**排查步骤**：
1. 直接访问端点查看响应头：`curl -I http://127.0.0.1:18081/actuator/beans`
2. 确认 `Content-Type` 为 `application/json` 或 `application/vnd.spring-boot.actuator.v3+json`
3. 检查管理端点基路径配置

**解决方案**：
```yaml
# application.yml
management:
  endpoints:
    web:
      base-path: /actuator  # 确认基路径
```

**相关文档**：
- [安全架构](architecture/security-and-sanitization.md) - 响应门禁

---

## 游标与分页错误

### CURSOR_EXPIRED

**含义**：游标过期（60 秒 TTL）

**常见原因**：
- 首次查询与续页查询间隔超过 60 秒
- 服务端进程重启导致快照丢失

**排查步骤**：
1. 检查首次查询到续页查询的时间间隔
2. 确认服务端进程未重启

**解决方案**：
```json
// 游标过期后，重新发起首次查询（不含 cursor）
{
  "targetId": "local",
  "maxResults": 20
  // 不传 cursor
}
```

**注意**：
- 快照有 60 秒绝对 TTL，续页不延长期限
- 进程重启后所有快照丢失

**相关文档**：
- [系统概览](architecture/system-overview.md) - 快照管理
- [公共信封结构](contracts/tools-schema/common-envelope.md) - 分页机制

---

### CURSOR_QUERY_MISMATCH

**含义**：游标与查询不匹配

**常见原因**：
- 续页时修改了查询参数（除 `cursor` 外）
- 使用了错误的游标

**排查步骤**：
1. 比对首次查询和续页查询的参数
2. 确认只增加了 `cursor` 参数，其他参数保持不变

**解决方案**：
```json
// 首次查询
{
  "targetId": "local",
  "packagePrefix": "com.example",
  "maxResults": 20
}

// 续页查询（只增加 cursor）
{
  "targetId": "local",
  "packagePrefix": "com.example",  // 保持不变
  "maxResults": 20,  // 保持不变
  "cursor": "eyJ0YXJnZXRJZCI6ImxvY2FsIiwib2Zmc2V0IjoyMH0..."
}
```

**相关文档**：
- [公共信封结构](contracts/tools-schema/common-envelope.md) - 续页机制

---

## 安全与脱敏错误

### UNSAFE_OUTPUT

**含义**：输出不安全

**常见原因**：
- 响应包含未经脱敏的敏感信息
- 脱敏管道检测到禁止输出的内容

**排查步骤**：
1. 这是服务端安全机制触发，用户无法直接解决
2. 检查查询是否涉及敏感配置（如密码、令牌）
3. 确认是否启用了 `--config-allow-values`

**解决方案**：
- 避免查询包含密码、密钥的配置属性
- 使用更精确的筛选避免匹配敏感属性

**相关文档**：
- [安全架构](architecture/security-and-sanitization.md) - 脱敏管道

---

### SANITIZATION_FAILED

**含义**：脱敏失败

**常见原因**：
- 脱敏管道遇到无法处理的数据结构
- 内部错误

**排查步骤**：
1. 这是服务端内部错误，用户无法直接解决
2. 尝试精化查询范围
3. 如持续出现，报告问题

**解决方案**：
- 使用更精确的筛选条件
- 减少 `maxResults`

**相关文档**：
- [安全架构](architecture/security-and-sanitization.md)

---

## 快速参考

### 按工具常见错误

| 工具 | 常见错误 | 解决方案 |
|------|---------|---------|
| `springboot_inspect_beans` | `ENDPOINT_NOT_EXPOSED` | 暴露 `beans` 端点 |
| `springboot_verify_mappings` | `ENDPOINT_NOT_EXPOSED` | 暴露 `mappings` 端点 |
| `springboot_diagnose_health` | `ENDPOINT_UNAUTHORIZED` | 核对既有 Bearer、安全链顺序及角色，不修改详情可见性来绕过鉴权 |
| `springboot_analyze_startup` | `STARTUP_DATA_UNAVAILABLE` | 启用 startup 端点并重启应用 |
| `springboot_check_migrations` | `ENDPOINT_NOT_EXPOSED` | 暴露 `flyway`/`liquibase` 端点 |
| `springboot_inspect_config` | `CAPABILITY_DISABLED` | 使用 `--config-prefix` 启用 |
| `springboot_search_openapi` | `INVALID_ARGUMENT` | `httpMethod` 必须配合 `pathPattern` 或 `operationId` |
| `springboot_detect_drift` | `INVALID_ARGUMENT` | 至少提供一个预期维度 |

### 按 HTTP 状态码

| HTTP 状态 | 错误码 | 说明 |
|----------|-------|------|
| 401/403 | `ENDPOINT_UNAUTHORIZED` | 需要授权或令牌无效 |
| 404 | `ENDPOINT_NOT_EXPOSED` | 端点未暴露 |
| 404 (startup) | `STARTUP_DATA_UNAVAILABLE` | 启动采集未配置 |
| 3xx | `REDIRECT_BLOCKED` | 不跟随重定向 |
| 5xx | `ENDPOINT_UNAVAILABLE` | 服务端错误 |
| 超时 | `TARGET_TIMEOUT` | 连接或响应超时 |
| 连接失败 | `TARGET_CONNECTION_REFUSED` / `TARGET_CONNECTION_FAILED` | 网络问题 |

---

## 相关文档

- [工具调用策略](contracts/tool-calling-policy.md) - 完整错误码列表和配方
- [各工具 Schema 说明](contracts/tools-schema/) - 按工具的详细错误处理
- [安全架构](architecture/security-and-sanitization.md) - 安全边界和预算
- [目标配置](target-app-setup.md) - 目标应用配置指南
- [首次接入](first-query.md) - CLI 使用指南
