---
title: Performance Baselines
status: draft
date: 2025-12-19
---
# Performance Baselines

## Latency Targets
- Market Data -> Signal: <100ms target, <500ms max
- Signal -> Risk Approval: <50ms target, <200ms max
- Order -> Execution: <100ms target, <500ms max
- End-to-End: <300ms target, <1000ms max

## Throughput Targets
- Market Data Events/sec: 100 target, 50 min
- Signals/sec: 50 target, 20 min
- Orders/sec: 20 target, 10 min

## Measurement Notes
- Run in a controlled staging environment.
- Capture 95th percentile latency for each hop.
- Record baseline configs (hardware, container resources, test data volume).

## Outputs
- Baseline report with measured values
- Deviations and root cause notes if thresholds fail
