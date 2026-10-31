# MCP Registry：命名空间与后续补丁方案

核对日期：2026-10-31。当前尚未提交 Registry，0.2.0 的 PyPI 发布不依赖 Registry。

## 已确认事实

- 本机 gh 的 GitHub 身份和仓库所有者均为 `neilmorse`；该身份的组织列表为空。
- 公开 PyPI 0.2.0 的包描述包含 `mcp-name: io.github.Kaelenx/spring-runtime-mcp`。
- 根 `server.json` 的 name 与该已发布标记一致，保留为 0.2.0 的历史发布元数据。
- GitHub `/users/Kaelenx` 查询返回 404；没有当前账号拥有旧命名空间的证据。
- GitHub 插件身份与本机 gh 不同，且对本仓库只有读取权限，不用于发布。

官方规则要求 GitHub 登录授权其本人/组织的命名空间，并要求 PyPI 包 README 中的
`mcp-name` 与 server.json 的 name 完全一致。参见
[CLI 认证说明](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/cli/commands.md#github-interactive)和
[PyPI 所有权验证](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx#pypi-packages)。
因此，仅将根 server.json 改为 `io.github.neilmorse/...` 会与公开 0.2.0 包描述冲突；
GitHub 仓库 URL 跳转也不构成旧 Registry 命名空间授权。

## 建议方案：0.2.1 元数据补丁

候选 JSON 为 [server-0.2.1.json](server-0.2.1.json)，仅供下次发布审阅，不表示该版本已存在。
可审阅改动如下；本轮不执行新版本发布或更改既有标签：

1. 源码版本与锁文件项目版本从 0.2.0 升为 0.2.1，成熟度继续 Alpha。
2. README 的所有权标记改为 `io.github.neilmorse/spring-runtime-mcp`。
3. 根 server.json 使用候选名称、仓库 URL、包版本和服务版本；pyproject 的项目 URL 同步为当前所有者。
4. 工具 Schema、生产诊断算法、认证、目标边界与预算保持现状；安装示例固定到新版本。
5. 更新 CHANGELOG，干净提交上执行完整发布门禁及无发布 CI，记录新 SHA 和产物摘要。
6. 发布前检查 GitHub pypi 环境规则。当前规则仅允许 `v0.2.0`，新增版本标签授权需单独批准；不能关闭保护或管理员绕过。
7. 新版本 PyPI 发布和公开安装验收完成后，核对公开包标记，再以正确 GitHub 身份登录 Registry 并提交候选元数据。

准备好的[补丁](registry-0.2.1.patch)覆盖版本源、README 标记、项目 URL 和 server.json。
经批准后用 `git apply --unidiff-zero docs/launch/registry-0.2.1.patch` 应用，
再运行 `uv lock --offline` 更新项目版本，复核文档示例并补充 CHANGELOG，再运行全部检查。
补丁不包含账户权限修改、凭据、发布命令执行或网络守卫变更。

不得覆盖 0.2.0 的标签或重新上传同版本包。若操作者能提供旧命名空间的独立授权证据，
可另行核查保留旧名称的方案；当前不假定该授权存在。

## 校验与投稿状态

本轮会校验现有与候选 server.json 的官方 Schema/CLI 规则；本地校验不验证登录权限或 PyPI 包所有权。
候选版本在 PyPI 不存在时不可执行 publish。CLI 身份认证可能需要操作者完成 GitHub 登录。

目录和公告可以引用已发布的 PyPI 包及 GitHub 仓库，无需声称 Registry 已收录。
