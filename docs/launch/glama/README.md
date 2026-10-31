# Glama 源码投稿与协议内省

2026-10-31 已使用 GitHub 登录 Glama，提交 `neilmorse/spring-runtime-mcp` 的 Runs from source 审核表单；
操作者确认收到审核邮件。人工审核尚未通过，公开服务器条目和 Dockerfile 管理入口尚未生成。
这不是“已收录”或“质量检查已通过”的声明。

## Dockerfile

[Dockerfile](Dockerfile) 使用官方 Python 3.12 slim 的固定镜像摘要，从仓库源码构建安装包，
以非 root 用户运行真实 `spring-runtime-mcp` STDIO 宿主。没有 fixture 替身、目标凭据、端口暴露、
真实诊断目标或外部业务接口配置。依赖通过官方 PyPI 安装，工具发现不触发目标读取。

```bash
docker build -t spring-runtime-mcp-glama:0.2.1 -f docs/launch/glama/Dockerfile .
docker run --rm --network none spring-runtime-mcp-glama:0.2.1 --version
```

Glama 人工审核通过后，在该条目的 Admin / Dockerfile 中使用此内容并运行其构建/质量检查。
目录中的远端沙箱无法访问开发者机器的回环应用；实际诊断请按主 README 在应用所在环境运行本地 CLI。
不会为了云端演示放行远程目标或提供虚假健康结果。

## 本地验证

源码快照为 `1d8f3fe6d80e7441188273f1f484ce6f83a7c7a2`，Linux x86_64，容器 Python 3.12.16，UID 10001。

- Docker 源码构建成功，入口版本 0.2.1；Schema 与 py.typed 资源存在。
- `--network none` 下的 SDK legacy / 2026-07-28 两模式工具发现、非法参数与配置默认关闭检查通过。
- 完整安装入口检查通过两种 SDK 模式、原始管道握手、八工具路由/Schema/注解/脱敏/16 KiB 与七个 replay。
  其中 HTTP 部分仅使用检查器自行启动的随机回环 fixture；容器临时使用 host 网络访问该 fixture，未连接其他服务。
- 首轮完整检查在 replay 启动时因临时包装目录缺少相邻 Python 启动器失败；补齐测试包装后重跑通过，未修改产品代码或测试断言。
- wheel/sdist 离线构建通过，已确认 wheel 包含 tools-contract.json 与 py.typed。
- 测试容器均已退出，无持续运行的目标、数据库或 MCP 容器。

这些是本地有限样本，不能替代 Glama 的远端构建、人工审核、安全检查或评分。

## 后续收录

1. 等待审核通过及管理链接；不要重复提交同一仓库。
2. 在 Glama 配置 Dockerfile，检查源码构建、initialize、tools/list 和八工具描述符。
3. 核实 Glama 自己的检查和评分，记录实际结果，不把本地验收替代远端评分。
4. 公开条目存在且检查通过后，为 awesome-mcp-servers 的 PR #18153 添加真实 Glama 徽章，再恢复其审核状态。

投稿描述：

> Read-only local Spring Boot runtime diagnostics: beans/conditions, routes, health, migrations, startup, config origin, OpenAPI and drift. Registered loopback targets, sanitized 16 KiB results, and partial/unknown when evidence is missing.

[Glama 官方投稿说明](https://glama.ai/mcp/faq#how-do-i-submit-an-mcp-server)、
[源码构建与内省流程](https://glama.ai/mcp/methodology)。
