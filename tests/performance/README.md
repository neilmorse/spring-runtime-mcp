# Performance Tests

This directory measures synthetic replay tool calls, snapshot operations and output serialization. Prepare the locked development environment with `uv sync --dev --locked` (add `--offline` once cached). It does not run a Spring Boot process. Timing reference values below are warning thresholds, not measured hardware baselines.

## Running Benchmarks

```bash
# Run all performance tests
uv run --no-sync python -m pytest tests/performance/ -v

# Run specific benchmark
uv run --no-sync python -m pytest tests/performance/test_benchmark_tools.py::TestToolCallPerformance -v

# Run with detailed output
uv run --no-sync python -m pytest tests/performance/ -v -s
```

## Benchmark Categories

### 1. Tool Call Latency
- **Simple calls**: Health check without details (~50ms p50)
- **Complex calls**: orderController and its resolved dependencies (200ms warning reference)

### 2. Snapshot Performance
- **Serialization**: Storing 50-item snapshot (~10ms p50)
- **Deserialization**: Retrieving paged snapshot (~5ms p50)

### 3. Bean Graph Traversal
- **Depth 1-4**: The fixture chain orderController → orderService → orderRepository → dataSource → connectionFactory, checked at depths 1–4
- **Baseline**: Depth 3 ~100ms p50

### 4. Response Processing
- **Output serialization**: Synthetic envelope with 30 records that fits the 16 KiB frame budget (50ms warning reference). This does not benchmark the 8 MiB upstream HTTP read limit.

## Baselines

Current baselines (subject to adjustment based on CI hardware):

| Operation | p50 Baseline |
|-----------|-------------|
| Simple tool call | 50ms |
| Complex tool call | 200ms |
| Snapshot serialize | 10ms |
| Snapshot deserialize | 5ms |
| Bean graph depth 3 | 100ms |
| Output serialization (within 16 KiB) | 50ms |

## Warnings

Tests emit warnings (⚠️) when p50 latency exceeds 2x baseline, but do not fail.

This allows monitoring performance degradation without blocking CI.

## CI Integration

To run performance tests in CI:

```yaml
# .github/workflows/test.yml
- name: Run performance benchmarks
  run: uv run --no-sync python -m pytest tests/performance/ -v
```

## Interpreting Results

- **p50 (median)**: Typical latency
- **p95**: 95% of requests complete within this time
- **p99**: 99% of requests complete within this time

Tool calls must return ok/partial without errors. Bean samples must contain the selected orderController and its expected resolved chain; these assertions run after the timed operation. With 10 samples, the reported empirical p95/p99 are both the sample maximum, not a production tail-latency guarantee.

## Database Health Composition Replay

```bash
uv run --no-sync python -m pytest -q -s tests/integration/test_health_composition_replay.py
```

The replay uses the Boot 3.4 fixture with an explicit association between the `db` health component and the `application` Context's `dataSource` Bean. The replay adds that Bean to the child Context, where its `connectionFactory` dependency resolves to the parent. Both paths call the same registered handlers and use the response serializer with server metadata and both content copies.

One Linux run with Python 3.12.15 measured 20 samples per path.

| Path | JSON-RPC response frames | Fixture reads | Total response bytes | Median processing time |
| --- | ---: | ---: | ---: | ---: |
| Separate health and Bean results | 2 | 2 | 5,084 | 8.61 ms |
| Combined replay candidate | 1 | 2 | 3,415 | 7.98 ms |

The candidate used 32.8% fewer response bytes and fit within the 16,384-byte frame cap. It includes the health observation, the selected Bean and its wiring, and separate evidence sources and coverage. Timing covers local handler processing and frame serialization. The single candidate frame is produced inside the test, so these measurements quantify frame size and local processing cost. MCP client round-trip latency, upstream HTTP latency, and model token counts are outside the measurement.

Healthy and hidden-detail components and unknown associations use one fixture read. A denied or timed-out Bean read yields a partial candidate with the original health observation and unavailable Bean evidence.

## Local Boot Health Supplement Acceptance

A separate loopback acceptance used Spring Boot 3.4.8 and JDK 21 with a test-only database health indicator and a registered `application/dataSource` Bean depending on `connectionFactory`. A local STDIO client compared standalone health and direct-dependency Bean calls with an opt-in health call over the same fault. Tomcat access logs verified the GET counts. Frames included both MCP content representations.

| DOWN workflow | MCP calls | Upstream GETs | Response bytes | Median local round trip |
| --- | ---: | ---: | ---: | ---: |
| Health and Bean separately | 2 | 2 | 5,094 | 101.72 ms |
| Health with Bean evidence | 1 | 2 | 3,574 | 35.94 ms |

The comparison used 20 pairs in one local session. Timing includes local STDIO and HTTP and excludes model time. The separate UP run produced `notApplicable` and one health GET. These observations apply to the isolated application and local client setup.

## Future Enhancements

- [ ] Add memory profiling
- [ ] Track baseline trends over time
- [ ] Add comparison with previous runs
- [ ] Export results to monitoring system
