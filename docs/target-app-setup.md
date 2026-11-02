# 被诊断 Spring Boot 应用配置指南

本指南只配置被诊断应用的标准观测能力，不安装自定义 Agent，不把业务方法改成 MCP 工具。当前宿主可只读连接登记的回环 origin，支持 `--token-env` 绑定现有 Bearer 凭据；Basic、自定义管理基路径和远程目标尚未交付。首次安装、凭据转发和查询见[首次接入指南](first-query.md)，客户端模板见[配置指南](client-configuration.md)。目标依赖、暴露与重启仍须应用维护者明确授权。

## 1. 先确认版本和现有授权

目标应用需要已有 `spring-boot-starter-actuator`；依赖版本由自身 Spring Boot BOM 管理。Flyway、Liquibase 和 springdoc 均只在应用本来需要时使用，不为诊断安装业务 MCP Starter、数据库工具或字节码 Agent。

| Boot 版本 | 只读上限 | env/configprops 值保护 | 本指南策略 |
| --- | --- | --- | --- |
| 3.4+ / 4.x | 支持 `management.endpoints.access.max-permitted` | `show-values: never` | 使用下一节模板；配置诊断默认关闭 |
| 3.0–3.3 | 无上述全局访问上限 | `show-values: never` | 删除不支持的 access 配置，必须使用现有安全层限制 GET |
| 2.7 | 无上述全局访问上限 | 使用旧版 keys-to-sanitize，不把 show-values 当成有效防线 | 使用独立旧版模板，默认禁用 env/configprops，并限制 HTTP 方法 |

版本依据：[Boot 3.4 访问控制](https://docs.spring.io/spring-boot/3.4/reference/actuator/endpoints.html#actuator.endpoints.access)、[Boot 3.3 端点机制](https://docs.spring.io/spring-boot/3.3/reference/actuator/endpoints.html)、[Boot 3.0 值屏蔽](https://docs.spring.io/spring-boot/docs/3.0.13/reference/html/actuator.html#actuator.endpoints.sanitization)。旧版属性见 [2.7 env API](https://docs.spring.io/spring-boot/docs/2.7.18/api/org/springframework/boot/actuate/autoconfigure/env/EnvironmentEndpointProperties.html)与 [configprops API](https://docs.spring.io/spring-boot/docs/2.7.18/api/org/springframework/boot/actuate/autoconfigure/context/properties/ConfigurationPropertiesReportEndpointProperties.html)。

仅设 include 不等于授权；仅设 read-only 也不等于所有 GET 安全，heapdump/logfile 仍须排除。现有 Spring Security、TLS、鉴权和业务安全链继续有效，不通过 `permitAll`、关闭 CSRF 或 `show-values=always` 绕过故障。

## 2. Boot 3.4+/4.x：application-local-mcp.yml

将下面完整内容保存到**目标应用**的 `src/main/resources/application-local-mcp.yml`。业务端口使用示例值 8080，独立管理端口使用 18081；如应用原有业务端口不同，保留实际值，管理端口必须与其不同且未被占用。

```yaml
server:
  port: 8080
management:
  server:
    port: 18081
    address: 127.0.0.1
  endpoints:
    access:
      max-permitted: read-only
    web:
      base-path: /actuator
      exposure:
        include: health,beans,conditions,mappings,flyway,liquibase,startup,info,configprops,env
        exclude: shutdown,heapdump,logfile,sessions,loggers,caches,quartz
    jmx:
      exposure:
        exclude: "*"
  endpoint:
    env:
      access: none
      show-values: never
    configprops:
      access: none
      show-values: never
    health:
      show-details: never
```

`management.server.address` 的独立绑定依赖独立管理端口；只写 address 而与业务共用端口，不能据此宣称管理端点已隔离。[管理监听地址说明](https://docs.spring.io/spring-boot/3.4/reference/actuator/monitoring.html)。不要把地址改成 `0.0.0.0`，也不要为容器/远程开发自动开放端口。127.0.0.1 属于目标进程所在网络命名空间，不自动指向开发者宿主机。

include 是诊断能力的明确列表，exclude 额外拒绝危险读取。`env/configprops` 虽在候选列表中，仍因 `access: none` 不可用；这与本项目默认关闭配置诊断一致。日常只检查 Bean/路由时可继续把 include 精简成 `health,beans,conditions,mappings`。启用某个端点前先确认需要和授权；Flyway/Liquibase 未安装时不会凭配置生成迁移数据。

仅在需要配置来源诊断且获得授权后，把 env/configprops 各自的 `access: none` 改为 `access: read-only`，保持两处 `show-values: never`。不要粘贴整份原始 env/configprops 响应；`origin`、自定义详情和资源字段仍可能携带敏感内容，MCP 读取执行独立脱敏和登记范围投影。

## 3. 旧版本：不要依赖被忽略的属性

### Boot 3.0–3.3

沿用上一节的端口、exposure、show-values 和 health 设置，但删除 `management.endpoints.access` 及两个端点的 `access` 属性。用 `management.endpoint.env.enabled: false` 和 `management.endpoint.configprops.enabled: false` 保持配置诊断默认关闭；显式启用时仍保留 show-values=never。旧版本必须另用安全层拒绝写方法，不能用 enabled/exposure 替代方法授权。

旧版接入沿用应用已有的 Bearer 认证。由维护者在实际处理 Actuator 请求的安全链中合并规则：只允许获权诊断角色读取所需固定路径的 GET，其他方法及未批准路径拒绝。优先从 `health`、`beans`、`conditions`、`mappings` 的最小集合开始；需要健康组时另行批准 `/actuator/health/liveness` 和 `/actuator/health/readiness`。

必须同时核对链的匹配范围、顺序、Bearer 验证器及角色映射。独立高优先级链不会自动继承其他链的认证配置；仅添加 `httpBasic()` 无法让 MCP 的 Bearer 获得认证。MVC 使用现有 `SecurityFilterChain`，WebFlux 使用现有 `SecurityWebFilterChain`，保留业务路径的原有保护。具体认证机制取决于应用已有实现，不能用一段通用新建链代码代替合并审查。[Spring Boot 安全链说明](https://docs.spring.io/spring-boot/3.3/reference/actuator/endpoints.html#actuator.endpoints.security)。

如果管理入口只支持 Basic，当前 MCP 不能直接接入；维护者确认并配置可用 Bearer 入口后，再按[首次接入指南](first-query.md)转发命名环境变量并完成一次实际工具查询。

### Boot 2.7

用下面完整模板替代第 2 节，不混入 3.4 的 access 或 3.x 的 show-values 属性。`keys-to-sanitize: [".*"]` 对旧版所有属性键采取保守屏蔽，但不构成任意 origin/异常文本都安全的保证；env/configprops 因此仍默认关闭且不在 exposure 中。

```yaml
server:
  port: 8080
management:
  server:
    port: 18081
    address: 127.0.0.1
  endpoints:
    web:
      base-path: /actuator
      exposure:
        include: health,beans,conditions,mappings,flyway,liquibase,startup,info
        exclude: shutdown,heapdump,logfile,sessions,loggers,caches,quartz,env,configprops
    jmx:
      exposure:
        exclude: "*"
  endpoint:
    env:
      enabled: false
      keys-to-sanitize: [".*"]
    configprops:
      enabled: false
      keys-to-sanitize: [".*"]
    health:
      show-details: never
```

Boot 2.7/Spring Security 5.7 同样需要在现有 Bearer 认证链中合并固定路径 GET 与角色授权；使用该版本支持的 API，保留业务链与认证提供器。默认关闭 env/configprops，避免将旧版值保护误作新版本属性已生效。[Boot 2.7 安全说明](https://docs.spring.io/spring-boot/docs/2.7.18/reference/html/actuator.html#actuator.endpoints.security)。

不要在未配置方法级拒绝规则的旧版应用中开放 startup。若需要 env/configprops，必须先单独审查现有安全策略、取消对应 enabled/exclude 禁令并保持全键屏蔽；这不应成为默认本地启动配置。

## 4. 开启非破坏性启动快照

在应用入口文件导入以下两个标准类。`Application` 在本例中表示目标应用自己的 `@SpringBootApplication` 主类；如果实际主类叫 `OrdersApplication`，下方第一行使用 `OrdersApplication.class`。

```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
```

在现有 `main(String[] args)` 内，用以下 **3 行**替换直接的 `SpringApplication.run(...)`：

```java
SpringApplication application = new SpringApplication(Application.class);
application.setApplicationStartup(new BufferingApplicationStartup(2048));
application.run(args);
```

这是原生启动采集配置，不修改业务逻辑、不安装第三方 Agent；设置必须先于 run。2048 是缓冲容量，不是耗时阈值。采集需要从新一次启动开始；提出改入口或重启建议不等于 Agent 获准自动执行。[官方启动采集说明](https://docs.spring.io/spring-boot/3.4/reference/features/spring-application.html#features.spring-application.application-startup)。

只读取 `GET /actuator/startup` 快照。`POST /actuator/startup` 会读取并排空缓冲区，不用于采集、恢复或排障验证。容量不足、未采集或被其他消费者排空的数据不能补回；空时间线不能证明没有瓶颈。[Startup Web API](https://docs.spring.io/spring-boot/3.4/api/rest/actuator/startup.html)。

## 5. 激活与人工核验

在**被诊断应用仓库**启动已有 Maven Wrapper 项目时，可使用下面的命令；本 MCP 仓库没有该 wrapper，不在这里执行。若应用依赖其他开发 Profile，按其原有启动方式同时启用 local-mcp，并确认最终生效配置。

```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=local-mcp
```

MCP 接入以已有 Bearer 和实际工具查询为验收依据，凭据转发见[首次接入指南](first-query.md)。以下 Basic 命令仅供维护者核验已经支持 Basic 的管理入口；即使返回成功，也不证明 MCP 可以认证，不应为运行这些命令新增 Basic。

下面命令使用示例诊断用户名 `mcp-reader`；先确保你的应用已有该用户且具有获权诊断角色，否则改用实际已授权账号。curl 会提示输入密码，不把密码放入命令、URL、配置或聊天。命令只输出 HTTP 状态，不保存诊断 JSON，也不跟随重定向。

```bash
curl --noproxy '*' --connect-timeout 2 --max-time 5 --user mcp-reader --request GET --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:18081/actuator/health
curl --noproxy '*' --connect-timeout 2 --max-time 5 --user mcp-reader --request GET --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:18081/actuator/startup
```

这些命令假设示例管理端口使用本地 HTTP；已有 HTTPS 的实例继续使用其真实 HTTPS 地址和受信证书，不能使用 `-k`。Bearer-only 应用应沿用现有受保护凭据流程，不为测试降级成 Basic 或把 token 粘到 shell 历史。宿主通过 `--token-env` 独立绑定既有 Bearer 凭据，不接受客户端 MCP Token 透传。

| 观察 | 下一步 |
| --- | --- |
| 连接拒绝/超时 | 核查 Profile、监听地址、18081 是否启动及当前网络命名空间，不扩大绑定范围 |
| 401/403 | 检查已有凭据、角色和诊断链顺序，不改为 permitAll |
| 301/302 或 `/login` | 检查现有认证入口；不 `curl -L`、不把 HTML 当 JSON |
| 404 | 区分未启用、未暴露、被 access=none 移除、路径/端口错误和缺少对应原生能力 |
| health 200/503 但只有 status | 详情当前不可见；保留未知，按需申请 when-authorized 详情，不默认 always |
| startup 404/空 events | 核对 exposure、版本方法守卫、原生采集器和新启动；不要 POST 补救 |
| env/configprops 不可用 | 默认关闭是预期行为；只为明确的配置诊断启用，并保持目标与本地两层脱敏 |

核对启动日志和实际监听，确保管理端口只在 127.0.0.1；环境变量、命令行参数或其他 Profile 可以覆盖 YAML，不能仅凭文件内容断言监听安全。info 和自定义 Health 内容也应保持最少信息，目标端掩码不能替代本地二次脱敏。

## 6. OpenAPI 与诊断结束后的收敛

已有 springdoc 的应用默认可在业务端口提供 `/v3/api-docs`。当前连接器只读取登记 origin 的固定 `/actuator/openapi`；自定义 `springdoc.api-docs.path` 不会自动回退，管理端口的 `/actuator/openapi` 是否可用必须由维护者按安装版本确认；本指南不自动启用新文档路径、不切换端口、不启用 springdoc 的 MCP 业务工具。

上述 Actuator access 规则不自动保护业务端口上的 springdoc 路径，文档仍受应用现有安全规则约束。OpenAPI `servers`、远程 `$ref` 或 description 不能扩展诊断目标。当前已有 `springboot_search_openapi`；仅有业务端口的 `/v3/api-docs` 不代表固定管理端点可用，人工访问成功也不等于 MCP 检索已通过。

诊断结束后停用 local-mcp Profile 或收窄 exposure，撤销临时授权；变更与重启由应用维护者决定。保留脱敏结构化结论，不归档原始 env、configprops、健康异常栈、日志或内存转储。
