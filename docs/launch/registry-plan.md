# MCP Registry：命名空间迁移记录

2026-10-31 已完成：`io.github.neilmorse/spring-runtime-mcp` 0.2.1 已发布，
[公开 API](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.neilmorse%2Fspring-runtime-mcp) 已独立回读。
版本和产物验证见[发布记录](release-0.2.1.md)。

## 原因与已实施修正

0.2.0 的公开 PyPI README 使用 `io.github.Kaelenx/spring-runtime-mcp`，当前仓库所有者和 gh 身份为 `neilmorse`，
且没有旧命名空间授权证据。官方要求 GitHub 本人/组织授权与 PyPI 的 `mcp-name` 标记匹配，
见 [CLI 认证](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/cli/commands.md#github-interactive)与
[PyPI 所有权规则](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx#pypi-packages)。

操作者明确批准后，发布 0.2.1 元数据补丁：版本源、Registry 名称和包版本、README 标记与项目链接同步。
动态项目的 uv.lock 条目不固化项目版本；`uv lock --offline` 校验通过，依赖锁文件未变。
未修改诊断算法、公开工具 Schema、运行依赖、安全守卫或预算，也未覆盖 0.2.0 的标签/产物。

[参考补丁](registry-0.2.1.patch)和[元数据示例](server-0.2.1.json)保留为准备阶段记录；
对应修改已经实施，不要在当前版本再次应用该补丁。

## 身份、权限与发布

- GitHub 插件对本仓库只读且身份不同；写入使用本机已获授权的仓库所有者身份。
- PyPI 环境保留 neilmorse 人工审批和禁止管理员绕过；标签范围为 `v0.2.0` 与 `v0.2.1`，未开放通配规则。
- Registry 使用[手动工作流](../../.github/workflows/publish-registry.yml)，不将个人 GitHub 访问令牌交给 Registry。
- 工作流仅允许本仓库 master 手动触发，无输入；固定检出 `v0.2.1` 并检查精确提交 SHA、版本、名称及公开 PyPI 标记。
- 官方 mcp-publisher 固定 v1.8.7 且校验下载摘要；只有发布 job 具有 `id-token: write`，身份令牌为短时 OIDC。
- [实际运行](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41193724668) 的验证、身份认证、提交及精确条目回读全部通过。

后续版本需要审阅更新工作流中固定的版本/提交、完成对应包验收并取得发布授权。
不要重复发布已有 Registry 版本或挪动旧标签。GitHub 仓库跳转不能替代命名空间所有权验证。

## 目录状态

[Glama 条目](https://glama.ai/mcp/servers/neilmorse/spring-runtime-mcp) 已公开并完成首次发布，
成功发现全部八个工具，工具定义评分 TDQS A（3.9/5.0）。
[awesome-mcp-servers PR #18153](https://github.com/punkpeye/awesome-mcp-servers/pull/18153)
已加入真实评分徽章并恢复审核，等待上游维护者处理，尚未宣称已合并。
源码构建、本地有限样本与远端状态见 [Glama 投稿记录](glama/README.md)。
