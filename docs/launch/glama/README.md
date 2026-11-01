# Glama 源码容器构建指南

[Dockerfile](Dockerfile) 从当前仓库源码构建 `spring-runtime-mcp`，使用固定摘要的 Python 3.12 slim 基础镜像和官方 PyPI，以 UID 10001 的非 root 用户启动真实 STDIO 宿主。

在仓库根目录执行：

```bash
docker build -t spring-runtime-mcp-glama:local -f docs/launch/glama/Dockerfile .
docker run --rm --network none spring-runtime-mcp-glama:local --version
```

构建需要下载基础镜像及包依赖；上述运行命令只检查入口版本。Dockerfile 复制 pyproject.toml、README、LICENSE 和 src，不包含人类历史库、fixture 替身、目标凭据或端口暴露配置。工具发现本身不读取目标。

实际协议验证需要客户端通过容器 stdin/stdout 执行 initialize、tools/list 和 tools/call。使用测试自建回环 fixture 时需明确网络命名空间；容器的 127.0.0.1 不等于开发者宿主机。真实应用接入仍需单独授权，沿用固定路径、回环、鉴权、TLS、脱敏与预算守卫。

目录远端沙箱无法直接诊断开发者机器上的回环应用。日常诊断按[首次接入指南](../../first-query.md)在获权应用所在环境运行本地 CLI。

Dockerfile、依赖或工具元数据改变后，分别检查本地构建、实际远端构建及工具发现。Glama 的实际配置、收录和评分由远端状态决定；本指南不声明当前评分或兼容性结果。[Glama 投稿说明](https://glama.ai/mcp/faq#how-do-i-submit-an-mcp-server)。
