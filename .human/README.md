# 人类备忘

只留需要人工回顾的取舍、最终验收和发布记录。日常编码默认不读本目录，当前实现从 [docs](../docs/README.md) 查阅。

- [决策账本](DECISION_LOG.md)：为什么这样做，每次调整记几句话。
- [待验证想法](ROADMAP_IDEAS.md)：尚未立项，不作为功能承诺。
- [发布记录](releases/)：0.2.0–0.2.6 的提交、产物摘要和验收边界。

## 最终报告

| 要回顾的事情 | 记录 |
| --- | --- |
| 预算、并发、协议与诊断修复 | [综合修复](reports/comprehensive-remediation-2026-10-22.md) |
| OpenAPI、时间与 JHipster 独立端口 | [遗留问题闭环](reports/remaining-findings-remediation-2026-10-22.md) |
| 脱敏、游标与大快照分页 | [故障矩阵闭环](reports/production-chaos-remediation-2026-10-23.md) |
| WebFlux predicate | [修复复验](reports/webflux-predicate-remediation-2026-10-22.md) |
| Nacos 四小时样本 | [运行记录](reports/nacos-four-hour-2026-10-23.md) |
| Fineract / HertzBeat / XXL-JOB | [Fineract](reports/ultra-project-fineract-2026-10-23.md) · [HertzBeat](reports/niche-project-hertzbeat-2026-10-23.md) · [XXL-JOB](reports/xxl-job-2026-10-23.md) |
| 首次发布准备与客户端探针 | [发布准备](reports/release-readiness-2026-10-31.md) |

[evidence/](evidence/) 保留独有的脱敏机器摘要，包含失败与修复后的结果；其他样本数据仍在各 examples 目录。历史结果只对应其记录的版本和范围。

全文快照、旧计划、交接稿、中间审计和迁移清单已清理；原始材料可从 Git 历史恢复，报告中的历史链接固定到对应提交。本目录不存凭据或原始敏感响应，不进入发行包。
