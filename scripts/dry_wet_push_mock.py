"""
Push a mock Dry/Wet score and derived parameters to Redis for fast end-to-end testing.

Usage:
    python scripts/dry_wet_push_mock.py --score 80

Effect:
    - Derives parameters via the same mapping used by dry_wet.py
    - Writes to Redis key `adaptive_intensity:current_params` with short TTL
    - Optional: publishes an update event on `adaptive_intensity:updates`
"""

from __future__ import annotations

import argparse
import json
import os

import redis

from backoffice.services.adaptive_intensity.dry_wet import ParamBounds, derive_parameters


def main():
    parser = argparse.ArgumentParser(description="Push mock Dry/Wet params to Redis")
    parser.add_argument("--score", type=float, default=80.0, help="Dry/Wet score 0..100 (default: 80)")
    parser.add_argument("--ttl", type=int, default=300, help="TTL seconds (default: 300)")
    parser.add_argument("--publish", action="store_true", help="Also publish to adaptive_intensity:updates")
    args = parser.parse_args()

    # Clamp score
    score = max(0.0, min(args.score, 100.0))

    # Derive params
    params = derive_parameters(score, ParamBounds())
    params.update(
        {
            "dry_wet_score": score,
            "winrate": 0.7,  # mock values for visibility
            "profit_factor": 1.5,
            "max_drawdown": 0.05,
            "window_trades": 300,
        }
    )

    # Redis connection
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        db=0,
        decode_responses=True,
    )
    redis_client.ping()

    body = json.dumps(params)
    redis_client.setex("adaptive_intensity:current_params", args.ttl, body)

    if args.publish:
        redis_client.publish("adaptive_intensity:updates", body)

    print(f"Pushed mock Dry/Wet params with score={score} to Redis (TTL={args.ttl}s)")
    print(body)


if __name__ == "__main__":
    main()
