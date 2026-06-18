"""Validate the #3221 June 6 1h candle dataset."""
from __future__ import annotations
import json

PATH = "artifacts/datasets/3221_june6_1h/mexc_btcusdt_1m_2026-06-05T2330_2026-06-06T0030.jsonl"
with open(PATH) as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
first = json.loads(lines[0])
last = json.loads(lines[-1])
print(f"First: ts_ms={first['ts_ms']} open={first['open']} close={first['close']}")
print(f"Last:  ts_ms={last['ts_ms']} open={last['open']} close={last['close']}")
ts = [json.loads(line)["ts_ms"] for line in lines]
diffs = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
print(f"Cadence: min={min(diffs)}ms max={max(diffs)}ms all_60k={all(d == 60000 for d in diffs)}")

# Verify no secrets
text = open(PATH).read()
for pat in ["postgres://", "postgresql://", "SECRET", "TOKEN", "PASSWORD"]:
    if pat in text:
        print(f"FAIL: Found {pat} in dataset")
        raise SystemExit(1)
print("PASS: No secrets in dataset")
print("Dataset validation PASS")
