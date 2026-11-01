# 0.2.0 Alpha — 2026-10-31

Spring Runtime MCP 0.2.0 Alpha 已发布到 [PyPI](https://pypi.org/project/spring-runtime-mcp/0.2.0/)。
发布标签为 [`v0.2.0`](https://github.com/neilmorse/spring-runtime-mcp/tree/v0.2.0)，对应提交
`2394b29a84a5fcd8210d3934eee1a94e1d3fc0ac`。发布后的文档同步不改变该标签或已上传的产物。

## 安装

需要 Python 3.11+ 与 uv。首次运行从公开包索引安装依赖：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.0 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.0 --base-url http://127.0.0.1:18081
```

第二条命令为 STDIO MCP 宿主；先按[目标配置指南](../../docs/target-app-setup.md)准备本地回环实例，
再由客户端启动并完成 initialize、tools/list 和一次只读调用。工具发现不证明目标已经授权。

## 范围

八个工具覆盖 Bean/条件、路由、健康、迁移、启动、配置来源、OpenAPI 和运行态漂移。
限定登记回环目标、固定逻辑端点、STDIO、可选 Bearer 环境绑定；配置诊断默认关闭。
只读 GET、禁止重定向/环境代理、验证 TLS、双层脱敏和 16 KiB 完整工具回包预算保持。
证据缺失返回 partial/unknown。

非回环目标、Basic/自定义头、自定义管理基路径、OpenAPI 路径回退尚未实现。
Windows/macOS、完整 Boot/Java/Web 栈矩阵及其他实际客户端交互仍未验收。
Codex CLI 只有一次自建 fixture 健康调用的实际客户端冒烟证据，不能外推全部客户端场景。

## 验证与产物

[正式发布流水线](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41176181251)
通过 Python 3.11–3.14 的各 1100 项离线测试、类型/格式/契约检查和完整发布门禁。
本地干净提交完整门禁退出 0；wheel/sdist 分别在隔离环境完成两种 SDK 模式、八工具
自建回环 HTTP 调用及七个 replay 场景。

公开 PyPI 文件摘要与本地、验证型 CI 及正式 Release 同批产物一致：

| 文件 | SHA256 |
| --- | --- |
| `spring_runtime_mcp-0.2.0-py3-none-any.whl` | `5c1cada7be8c233cae7a8956fa2bc1e2f7bb3554bc0f6ead1fda9bdbef8380e0` |
| `spring_runtime_mcp-0.2.0.tar.gz` | `19e78b902790c8a8a83846cacb8e353585e705f7e16abcbf53abc75f3d4505cd` |

公开 PyPI 安装在仓库外新建 Python 3.12.15 环境完成，不使用 uv 缓存、本地 wheel 或锁文件约束；
版本、SDK 两模式、八工具回环调用、协议与脱敏、16 KiB 和七 replay 均通过。
后续独立验收再次通过相同公开安装链路，111 个生产代码/资源文件与发布提交一致。
这不代表未来所有传递依赖组合均已验证。

## 发布后的事项

默认分支文档、目录投稿和公告与 PyPI 产物分别维护。
MCP Registry 的命名空间迁移尚未完成：0.2.0 包描述仍为 `io.github.Kaelenx/...`，
当前仓库所有者为 `neilmorse`，详见[Registry 方案](https://github.com/neilmorse/spring-runtime-mcp/blob/b547f770d5852db05d142e04b131c7ac497ad2f3/docs/launch/registry-plan.md)。不得声称已进入 Registry。

历史修复、样本与失败记录保留在[发布准备报告](../reports/release-readiness-2026-10-31.md)
和 [CHANGELOG](../../CHANGELOG.md)，其中“未发布”是对应历史阶段的状态。
