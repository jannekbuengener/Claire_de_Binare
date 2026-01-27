# Chaos Drill Assertions (Template)

Fill in concrete thresholds based on CDB design constraints.

## Inputs
- Scenario: {flipflop|highvol_noise|whipsaw}
- Seed: {int}
- Duration: {minutes}
- System config: commit hash + config references

## Assertions (Pass/Fail)

1) Exposure reduction in chaos window
- Metric/source: {prometheus|endpoint|db}
- Check: exposure <= {threshold} within {seconds} after volatility/regime trigger
- Fail if: exposure stays above threshold for longer than allowed

2) Overtrading guard
- Metric/source: orders_sent_total (or equivalent)
- Check: orders_per_minute <= {threshold}
- Fail if: threshold exceeded for >= {N} consecutive minutes

3) Drawdown / circuit breaker
- Metric/source: drawdown_pct, circuit_breaker_active
- Check: drawdown_pct <= {max} OR circuit_breaker_active becomes true before max is breached
- Fail if: drawdown exceeds max without breaker/stop

4) Defensive state transitions
- Source: logs + state endpoint
- Check: system enters {HOLD|REDUCE} state in response to chaos triggers
- Fail if: system remains in aggressive state or increases allocation

## Output format
- assertions_result.json
  - assertions: list with {id, name, pass, observed, threshold, evidence_links}
  - overall_pass: bool
