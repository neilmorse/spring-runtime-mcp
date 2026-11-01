# Shop 真实项目隔离验收

本目录提供 Boot **3.5.16 / Java 21 / MVC / JWT / 临时 PostgreSQL 16** 固定源码副本的显式验收配方。[保存的摘要](verification.json)只对应其记录的提交和配置，不代表当前 TDD 业务工作区完成或兼容矩阵通过。执行需要单独授权。

## 隔离与鉴权

- `actuator-profile.patch` 只在显式 Maven profile `runtime-diagnostics` 下引入 Boot BOM 管理的 Actuator；复现时仅向临时副本应用；保持业务安全链，原工作区修改不属于本配方。
- `application-runtime-diagnostics.properties` 是外置 overlay。`DiagnosticsLauncher.java` 使用真实 `ShopApplication` 和项目已有 Testcontainers 测试依赖，先创建临时 PostgreSQL，再启动副本；数据库只绑定回环。独立业务/管理端口均绑定 `127.0.0.1`，实际验收由启动器将管理端口也设为随机端口。
- 只暴露 health、beans、conditions、mappings、flyway、startup，设置全局 `read-only`，env/configprops 关闭。`BufferingApplicationStartup` 在启动前设置，MCP 仅 GET startup。
- Python 启动脚本移除既有应用/JVM覆盖变量，临时生成 JWT 密钥与令牌，仅放入子进程环境。现有 JWT 过滤器认证令牌；MCP 通过 `--token-env` 绑定凭据。没有放开匿名权限，也不调用登录或其他业务接口。
- 原始响应和框架日志不写入报告、fixture 或 transcript；保存的仅为通过契约、出口秘密检查和回包预算检查的状态摘要。默认 pytest 不运行本脚本，也不需要 Docker/JDK。

## 验收内容与限制

检查工具发现、匿名读取拒绝、获权 Bean/条件读取、MVC 路由元数据、隐藏健康详情、Flyway、GET startup 及漂移结果。每项检查以当前调用的 Schema、coverage 和安全预算为依据，缺源码目录、未建模条件或图/深度限制时保留 partial/unknown。

该配方不覆盖 OpenAPI、配置值诊断、WebFlux、其他 Boot 版本、第三方桌面客户端或完整 TLS/SNI 矩阵；不执行原项目完整业务测试，也不发布部署。正常结束及强制中断后均需核对临时资源清理。

## 复现

这是会启动新实例和临时容器的显式验收，需要相应授权。要求 Java 21、Maven、Docker、可用的 `postgres:16-alpine` 与项目测试依赖。先在 MCP 仓库执行 `uv sync --dev --locked`。以下命令创建已提交源码副本，保留原工作区业务改动：

```bash
MCP_REVIEW_ROOT=/path/to/spring-runtime-mcp
TDD_REVIEW_SOURCE=/path/to/TDD
TDD_REVIEW_REVISION=b7c54641df80ad9502ee1e3cc95a21d494cdd75d
TDD_REVIEW_DIR=$(mktemp -d /tmp/spring-runtime-tdd-XXXXXXXX)
git -C "$TDD_REVIEW_SOURCE" archive "$TDD_REVIEW_REVISION" | tar -x -C "$TDD_REVIEW_DIR"
git -C "$TDD_REVIEW_DIR" apply "$MCP_REVIEW_ROOT/examples/tdd-runtime/actuator-profile.patch"
mvn -f "$TDD_REVIEW_DIR/pom.xml" -Pruntime-diagnostics -DskipTests test-compile dependency:build-classpath \
  -Dmdep.includeScope=test -Dmdep.outputFile="$TDD_REVIEW_DIR/classpath.txt"
uv run --project "$MCP_REVIEW_ROOT" --no-sync python "$MCP_REVIEW_ROOT/scripts/check_tdd_runtime.py" \
  --project "$TDD_REVIEW_DIR" --classpath-file "$TDD_REVIEW_DIR/classpath.txt" \
  --source-revision "$TDD_REVIEW_REVISION"
docker ps -a --filter label=spring-runtime-mcp.validation=tdd --format '{{.ID}} {{.Status}}'
rm -r -- "$TDD_REVIEW_DIR"
```

启动器正常结束或收到终止信号时关闭 Spring 上下文及容器；强制杀死 JVM 后应单独检查上述标签。报告不包含环境令牌、数据库连接串或原始响应。
