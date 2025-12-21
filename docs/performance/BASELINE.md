# Performance Baseline

## Snapshot
- Timestamp (UTC): 2025-12-21T19:41:56.277670+00:00
- Commit: 1baba80d2dab5563ea006e2199e0e815efc0937d
- Platform: Windows-11-10.0.26220-SP0
- CPU count: 12
- Python: 3.12.10

## Benchmark Config
- Iterations: 200
- Warmup: 20
- Seed: 42
- Threshold pct: 2.0
- Min volume: 100000.0
- Allocation pct: 0.25
- Test balance: 10000.0
- Max position pct: 0.1
- Max exposure pct: 0.3

## Results
- p50 latency: 0.0006 ms
- p95 latency: 0.0208 ms
- p99 latency: 0.0274 ms
- throughput: 186150.41 events/s
- cpu time: 0.0000 s
- wall time: 0.0011 s
- startup time: 0.0007 s
- memory peak: 0.01 MB

## Targets
- p95 latency <= 5.0 ms
- p99 latency <= 10.0 ms
- throughput >= 5000.0 events/s
- startup <= 1.0 s
- memory peak <= 128.0 MB

## Notes
- Offline, deterministic benchmark (no external services).
- Values vary by hardware; compare runs on the same host.