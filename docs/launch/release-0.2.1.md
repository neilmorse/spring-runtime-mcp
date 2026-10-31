# 0.2.1 Alpha — 2026-10-31

[PyPI 0.2.1](https://pypi.org/project/spring-runtime-mcp/0.2.1/) 与
[GitHub Release](https://github.com/neilmorse/spring-runtime-mcp/releases/tag/v0.2.1) 已公开。
标签指向 `2d8567ba9ae10ac143a24d4ec443909a9e8997cb`。

本版仅将 Registry 所有权标记与仓库所有者对齐为 `neilmorse`，更新项目链接及版本元数据。
诊断实现、八工具 Schema、运行依赖、认证、只读/脱敏/目标/资源边界与 0.2.0 一致。
0.2.0 的标签和文件保留，未覆盖已有版本。

## 安装与范围

需要 Python 3.11+ 与 uv，命令显式使用官方 PyPI：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.1 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.1 --base-url http://127.0.0.1:18081
```

第二条命令是 STDIO 宿主。先按[目标配置指南](../target-app-setup.md)准备本地只读实例。
仍限定回环、固定端点、可选 Bearer 环境绑定；配置诊断默认关闭，完整工具回包最多 16 KiB。
缺少证据返回 partial/unknown。Windows/macOS、完整 Boot/Java/客户端及生产集群矩阵未验证。

## 验证

- 干净提交的本地完整门禁退出 0：1100 passed / 45.96 秒，类型、Ruff、契约及联网漏洞审计通过。
- [无发布验证 CI](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41178052393)
  与[正式发布流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41193348826) 均通过。
- wheel/sdist 分别完成隔离安装、SDK 两模式、八工具回环 HTTP 和七 replay；本地、验证 CI、正式发布及公开 PyPI 摘要一致。
- 公开 PyPI 安装在仓库外全新 Python 3.12.15 环境完成，未使用缓存、本地包或锁文件约束。
  版本、两协议模式、八工具、Schema/注解、结构化/文本一致、脱敏/预算、七 replay 和退出均通过。
- 两产物中的 111 个生产代码/资源文件与发布提交一致。

| 文件 | SHA256 |
| --- | --- |
| `spring_runtime_mcp-0.2.1-py3-none-any.whl` | `953c0ed29b9d53351b366c76e5071fab8d1bd0b0780fd9bf0bcb418ef606c0c1` |
| `spring_runtime_mcp-0.2.1.tar.gz` | `7c109a4911a25db55aea857ffd728342687d8e5829a21a22b3609a240a589be8` |

## Registry 与目录

已登记 `io.github.neilmorse/spring-runtime-mcp` 0.2.1，公开 API 已独立回读确认：
[Registry 条目](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp)。
[发布工作流](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41193724668)
使用短时 GitHub OIDC，未复用个人访问令牌。PyPI 环境人工审批与禁止管理员绕过均保留，
仅新增 `v0.2.1` 标签授权。详情见[命名空间迁移记录](registry-plan.md)。

[awesome-mcp-servers PR #18153](https://github.com/punkpeye/awesome-mcp-servers/pull/18153)
已补真实 Glama 徽章并恢复审核，等待上游维护者处理。Glama 条目已公开，
发现八个工具并显示 TDQS A（3.9/5.0）；详见 [Glama 投稿记录](glama/README.md)。
其他目录与跨平台社区帖子未发送，已准备[公告文案](announcement.md)。
