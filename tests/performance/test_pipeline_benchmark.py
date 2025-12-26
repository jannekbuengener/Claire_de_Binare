import pytest

from benchmarks.pipeline_benchmark import BenchmarkConfig, run_benchmark


@pytest.mark.unit
def test_pipeline_benchmark_smoke():
    config = BenchmarkConfig(iterations=50, warmup=10, seed=1)
    report = run_benchmark(config)

    metrics = report["metrics"]

    assert metrics["p50_ms"] >= 0.0
    assert metrics["p95_ms"] >= metrics["p50_ms"]
    assert metrics["p99_ms"] >= metrics["p95_ms"]
    assert metrics["throughput_eps"] > 0.0
    assert metrics["wall_time_s"] > 0.0
