# 本地构建证据

`scripts/build_evidence.py` 是本地 Python 接口，不新增 MCP 工具或采集端点。操作者显式登记项目目录、要对照的源码文件与本地产物路径；工具不扫描项目、不执行构建、不读取网络或运行进程信息。只登记获准读取、适合计算摘要的文件，不要登记凭据或日志。

```python
from pathlib import Path
from scripts.build_evidence import capture_snapshot, compare_snapshots

project = Path('/path/to/project')
sources = [Path('pom.xml'), Path('src/main/java/example/App.java')]
artifact = Path('target/app.jar')
before = capture_snapshot(project, sources, artifact, build_exit_code=0)
# 修改源码或执行构建后，再读取同一登记范围；退出码由调用者提供。
after = capture_snapshot(project, sources, artifact, build_exit_code=0)
comparison = compare_snapshots(before, after)
```

接口返回已登记文件的 SHA-256 聚合、产物 SHA-256、调用者报告的构建退出码与比较结果；调用者可在本地自行保存返回对象。源码聚合包含登记的相对路径与内容摘要；因此应使用同一组路径比较快照。结果不包含文件内容或绝对路径。空源码列表、重复登记、文件缺失、读取失败、读取期间元数据变化、非常规文件、符号链接与项目目录上跳路径均返回未知摘要；比较任一侧未知时，对应 changed 为 null。此实现依赖平台支持 `O_NOFOLLOW`，并拒绝跟随项目根目录本身及登记路径中的符号链接。文件逐个读取而非原子项目快照；应在文件稳定时采集。

构建的 `outcome` 只表示调用者提供的退出码，`artifactProducedByBuild` 始终为 `unknown`。即使退出码为零，或新旧产物摘要不同，也不能据此证明某个产物由指定源码生成；失败构建后旧文件仍可能存在。两个本地产物摘要不同只证明读取到的字节不同。

`runtimeIdentity.state` 始终为 `notCollected`，运行态比较为 `unknown`。本地 jar 摘要、调用者声明的源码版本或启动命令都不证明正在运行的进程加载了该 jar。MCP 的路由或漂移观察可作为独立运行态事实；它们与本地摘要并列，不变成已观测的运行构建身份。

隔离演示脚本 `scripts/check_injected_build_faults.py` 在临时副本中依次记录源码修改但未重建、成功重建但旧进程仍存活两种情况，并分别核对只读 MCP 路由。它将启动使用的 jar 复制到独立路径，避免在 JVM 运行中覆盖其文件。该验收依赖 Maven 离线缓存、Java 和 Linux `/proc`，并使用新建回环实例；输出路径必须不存在：

```bash
uv run --no-sync python scripts/check_injected_build_faults.py --output /tmp/build-evidence-check.json
```
