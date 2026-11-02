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

## Future Enhancements

- [ ] Add memory profiling
- [ ] Track baseline trends over time
- [ ] Add comparison with previous runs
- [ ] Export results to monitoring system
