# 当前任务：忽略 examples 并提交、推送、发布 0.2.11 Alpha（2026-11-02）

用户明确要求将 examples 加入 .gitignore 后重新提交、推送和发布。停止跟踪 examples 并保留本地文件，显式排除源码发行包，修正现行说明及发行元数据。历史资料访问限于本次发行条目和完整门禁凭据扫描。

- [x] 核对 Git 跟踪、打包与文档依赖，准备 0.2.11。
- [ ] 干净源码完整门禁，核对本地 examples 未改变且产物不包含 examples。
- [ ] 候选 PR 和 Python 3.11–3.14 检查，合并并推送精确标签。
- [ ] PyPI、GitHub Alpha Release 和 MCP Registry 发布与公开包验证。
- [ ] 发布验证记录、合并及工作区收尾。

不连接真实 Spring Boot；保留已发布版本与现有环境保护，不改运行依赖或公开 Schema。
