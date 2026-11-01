# 当前验证、构建与发布流程

流程依据 [pyproject.toml](../../pyproject.toml)、[共享 CI](../../.github/workflows/checks.yml) 与发布工作流。文档说明命令及门禁，不代表这些操作已在当前工作树执行。真实实例验收、推送标签和公开发布须取得对应授权。

## 本地离线验证

首次使用锁定开发环境：

```bash
uv sync --dev --locked
```

开发工具与依赖缓存完整后，同步加 `--offline`。默认检查不连接生产或真实 Spring Boot，只允许合成数据和测试自建回环 fixture：

```bash
uv run --no-sync python -m pytest -q
uv run --no-sync python -m mypy src/spring_runtime_mcp
uv run --no-sync python scripts/validate_tool_contract.py
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
```

Python 改动运行 pytest、Ruff lint/format；src 类型相关改动加 mypy；Schema 或契约校验脚本改动加契约检查。纯文档检查措辞、路径、锚点与链接。打包配置/资源路径改动加构建及产物资源检查。按改动类型完成要求后停止扩大验证；具体规则见 [AGENTS.md](../../AGENTS.md)。

## 构建与本地发行检查

```bash
uv build
```

wheel 必须包含 `spring_runtime_mcp/schemas/tools-contract.json`、`py.typed` 和 replay 资源。sdist 包含现行源码、测试、脚本和文档；`.human/` 明确排除于 wheel/sdist，人类资料仍由 Git 保留。

开发自检入口：

```bash
uv run --no-sync python scripts/pre_release_check.py --allow-dirty
```

该脚本检查工作树、安全扫描、版本、离线测试与静态检查，并构建 wheel/sdist，分别进行净室安装、资源/版本比对、两种 SDK 模式、自建回环 HTTP 工具调用和离线 replay。它可能需要包索引/缓存来安装验证环境，但不连接真实诊断目标。

`--audit` 另启联网依赖漏洞审计；当前完整发布门禁使用 `--audit --output-dir dist`。失败退出 1；跳过审计/构建、允许脏工作树或接受跳过测试等不完整检查退出 2。只有完整成功门禁才可作为正式发布依据。

## PyPI 发布

[候选验证](../../.github/workflows/release-check.yml) 对 `codex/release-*` 分支或手动触发运行完整门禁。[正式发布](../../.github/workflows/release.yml) 由 `v*` 标签触发，共享 CI 验证 Python 3.11–3.14，检查标签、包版本与 `server.json` 版本一致，上传已验证产物。

发布 job 在 GitHub `pypi` environment 中使用 OIDC 上传 PyPI；审批与保护规则由维护者在远端核对，不能仅凭仓库 YAML 断言当前配置。推送、审批和发布都需要本次发行的明确授权，不能由运行本地门禁推导。

授权发行时核对唯一版本源、`server.json`、安装示例、CHANGELOG 和候选产物摘要；旧标签和已发布产物保持不可变。公开包安装验证要使用仓库外全新环境并注明索引、平台、Python/SDK 版本与证据范围，不能用源码运行代替公开包安装。

## MCP Registry 与源码容器

[Registry 工作流](../../.github/workflows/publish-registry.yml) 是 master 上手动触发的固定发行任务，校验仓库身份、精确标签/提交、版本及 PyPI 所有权标记。它下载固定版本且校验摘要的官方 publisher，使用 GitHub OIDC 发布，再回读精确条目。版本和提交以工作流中的实际常量为准，不当作可接收任意版本输入的通用发布器。

后续发行须先审阅工作流固定版本/提交及对应包验收，再取得 Registry 发布授权。README 的 `mcp-name` 标记与 `server.json` 名称保持一致；不要重复发布已有版本或借仓库跳转推断命名空间所有权。

Glama 的源码构建配方见[容器指南](glama/README.md)。远端收录、评分和 PR 状态需要按次独立核实，不从本地构建成功推导。
