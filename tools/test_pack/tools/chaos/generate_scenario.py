# tools/chaos/generate_scenario.py
# Purpose: generate deterministic market-ish scenario streams (JSONL), used as input for chaos drills.
#
# Output format: one JSON object per line (JSONL)
# Fields: ts, price, regime_hint, seed, step

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.utils.seed import SeedManager


@dataclass(frozen=True)
class Tick:
    ts: str
    price: float
    regime_hint: str
    seed: int
    step: int


def gen_regime(mode: str, step: int) -> str:
    if mode == "flipflop":
        return "TREND" if (step % 2 == 0) else "RANGE"
    if mode == "highvol_noise":
        return "NOISE"
    if mode == "whipsaw":
        return "TREND" if (step % 20 < 10) else "RANGE"
    raise ValueError(f"Unknown mode: {mode}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate deterministic chaos scenario (JSONL)")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--minutes", type=int, default=180, help="Scenario length in minutes")
    ap.add_argument("--mode", choices=["flipflop", "highvol_noise", "whipsaw"], required=True)
    ap.add_argument("--start-utc", default="2026-01-03T12:00:00Z",
                    help="Start timestamp (UTC), ISO format like 2026-01-03T12:00:00Z")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = SeedManager(args.seed)
    start = args.start_utc.replace("Z", "+00:00")
    t = datetime.fromisoformat(start).astimezone(timezone.utc)

    price = 100.0
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for i in range(args.minutes):
            regime = gen_regime(args.mode, i)

            if regime == "NOISE":
                shock = rng.random_uniform(-2.5, 2.5)
            elif regime == "TREND":
                shock = rng.random_uniform(-1.2, 1.2)
            else:  # RANGE
                shock = rng.random_uniform(-0.8, 0.8)

            price = max(1.0, price + shock)
            tick = Tick(
                ts=t.isoformat().replace("+00:00", "Z"),
                price=round(price, 6),
                regime_hint=regime,
                seed=args.seed,
                step=i,
            )
            f.write(json.dumps(tick.__dict__) + "\n")
            t += timedelta(minutes=1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
