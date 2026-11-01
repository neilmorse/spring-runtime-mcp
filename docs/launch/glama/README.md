# Glama 源码投稿与协议内省

2026-10-31 已完成审核并公开[服务器条目](https://glama.ai/mcp/servers/neilmorse/spring-runtime-mcp)。
Glama 首次发布记录为 0.1.0，首次核查时 PyPI 包版本为 0.2.1；当前项目发布见 [0.2.4 记录](../release-0.2.4.md)，两处发布记录分别维护。
公开页成功发现全部八个工具，显示工具定义评分 TDQS **A（3.9/5.0）**。
此评分不是完整生产兼容性或安全保证。

真实评分徽章已加入 [awesome-mcp-servers PR #18153](https://github.com/punkpeye/awesome-mcp-servers/pull/18153)，
该 PR 已恢复为待维护者审核状态；提交目录 PR 不等于已经合并收录。
邮件中的 Boost 为可选付费推广，本次收录没有购买该服务。

## Dockerfile

[Dockerfile](Dockerfile) 使用官方 Python 3.12 slim 的固定镜像摘要，从仓库源码构建安装包，
以非 root 用户运行真实 `spring-runtime-mcp` STDIO 宿主。没有 fixture 替身、目标凭据、端口暴露、
真实诊断目标或外部业务接口配置。依赖通过官方 PyPI 安装，工具发现不触发目标读取。

```bash
docker build -t spring-runtime-mcp-glama:0.2.1 -f docs/launch/glama/Dockerfile .
docker run --rm --network none spring-runtime-mcp-glama:0.2.1 --version
```

Glama 已完成首次发布及工具内省；后续如需重建，可在条目的 Admin / Dockerfile 中使用此配方。
这里记录的是独立验证过的本地源码构建；Glama 实际构建配置以其 Admin 记录为准。
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

## 后续维护

1. 保留已公开条目与实际评分的记录；评分变化时重新核查具体条目，不用本地测试冒充远端评分。
2. Dockerfile、依赖或工具元数据变化后检查 Glama 的实际构建与内省结果。
3. 目录 PR 已补真实徽章并恢复审核，等待上游维护者处理；不要重复提交相同服务器。
4. 保持只读、回环、脱敏与预算守卫；工具定义评分不能成为扩大权限的依据。

投稿描述：

> Read-only local Spring Boot runtime diagnostics: beans/conditions, routes, health, migrations, startup, config origin, OpenAPI and drift. Registered loopback targets, sanitized 16 KiB results, and partial/unknown when evidence is missing.

[Glama 官方投稿说明](https://glama.ai/mcp/faq#how-do-i-submit-an-mcp-server)、
[源码构建与内省流程](https://glama.ai/mcp/methodology)。
