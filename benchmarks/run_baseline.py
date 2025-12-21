"""Generate an offline performance baseline report for the core pipeline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.pipeline_benchmark import BenchmarkConfig, run_benchmark


TARGETS = {
    "p95_ms": 5.0,
    "p99_ms": 10.0,
    "throughput_eps": 5000.0,
    "startup_s": 1.0,
    "memory_peak_mb": 128.0,
}


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except OSError:
        return "unknown"
    return "unknown"


def _render_markdown(report: dict, targets: dict) -> str:
    metrics = report["metrics"]
    config = report["config"]
    meta = report["meta"]
    return "\n".join(
        [
            "# Performance Baseline",
            "",
            "## Snapshot",
            f"- Timestamp (UTC): {meta['timestamp_utc']}",
            f"- Commit: {meta['commit']}",
            f"- Platform: {meta['platform']}",
            f"- CPU count: {meta['cpu_count']}",
            f"- Python: {meta['python']}",
            "",
            "## Benchmark Config",
            f"- Iterations: {config['iterations']}",
            f"- Warmup: {config['warmup']}",
            f"- Seed: {config['seed']}",
            f"- Threshold pct: {config['threshold_pct']}",
            f"- Min volume: {config['min_volume']}",
            f"- Allocation pct: {config['allocation_pct']}",
            f"- Test balance: {config['test_balance']}",
            f"- Max position pct: {config['max_position_pct']}",
            f"- Max exposure pct: {config['max_exposure_pct']}",
            "",
            "## Results",
            f"- p50 latency: {metrics['p50_ms']:.4f} ms",
            f"- p95 latency: {metrics['p95_ms']:.4f} ms",
            f"- p99 latency: {metrics['p99_ms']:.4f} ms",
            f"- throughput: {metrics['throughput_eps']:.2f} events/s",
            f"- cpu time: {metrics['cpu_time_s']:.4f} s",
            f"- wall time: {metrics['wall_time_s']:.4f} s",
            f"- startup time: {metrics['startup_s']:.4f} s",
            f"- memory peak: {metrics['memory_peak_kb'] / 1024.0:.2f} MB",
            "",
            "## Targets",
            f"- p95 latency <= {targets['p95_ms']} ms",
            f"- p99 latency <= {targets['p99_ms']} ms",
            f"- throughput >= {targets['throughput_eps']} events/s",
            f"- startup <= {targets['startup_s']} s",
            f"- memory peak <= {targets['memory_peak_mb']} MB",
            "",
            "## Notes",
            "- Offline, deterministic benchmark (no external services).",
            "- Values vary by hardware; compare runs on the same host.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate core pipeline performance baseline."
    )
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--output-dir", type=str, default="docs/performance")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a smaller, fast baseline (for CI smoke checks).",
    )
    args = parser.parse_args()

    if args.quick:
        config = BenchmarkConfig(iterations=200, warmup=20)
    else:
        config = BenchmarkConfig(iterations=args.iterations, warmup=args.warmup)

    report = run_benchmark(config)
    report["targets"] = TARGETS
    report["meta"]["commit"] = _git_commit()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "baseline.json"
    md_path = output_dir / "BASELINE.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report, TARGETS), encoding="utf-8")

    print(f"Wrote baseline report to {md_path} and {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
