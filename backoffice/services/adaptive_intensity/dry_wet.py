"""
Dry/Wet score calculation for adaptive risk parameters.

Derives a risk-intensity score (0=DRY, 100=WET) from the last N trades and
publishes derived parameters to Redis for the Risk Manager to consume via the
existing dynamic params key.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, List, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None
    RealDictCursor = None


DEFAULT_WINDOW = int(os.getenv("ADAPTIVE_LOOKBACK_TRADES", "300"))


@dataclass
class Trade:
    pnl: float
    timestamp: float


@dataclass
class ScoreWeights:
    winrate: float = float(os.getenv("ADAPTIVE_WINRATE_WEIGHT", "0.4"))
    profit_factor: float = float(os.getenv("ADAPTIVE_PF_WEIGHT", "0.4"))
    drawdown: float = float(os.getenv("ADAPTIVE_DD_WEIGHT", "0.2"))


@dataclass
class ParamBounds:
    threshold_min: float = float(os.getenv("ADAPTIVE_THRESHOLD_MIN", "2.0"))
    threshold_max: float = float(os.getenv("ADAPTIVE_THRESHOLD_MAX", "0.8"))
    exposure_min: float = float(os.getenv("ADAPTIVE_EXPOSURE_MIN", "0.40"))
    exposure_max: float = float(os.getenv("ADAPTIVE_EXPOSURE_MAX", "0.80"))
    position_min: float = float(os.getenv("ADAPTIVE_POSITION_MIN", "0.08"))
    position_max: float = float(os.getenv("ADAPTIVE_POSITION_MAX", "0.12"))


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def _max_drawdown(pnls: List[float]) -> float:
    """Return max drawdown as positive fraction of peak equity."""
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
    if peak == 0:
        return 0.0
    return max_dd / peak


def compute_kpis(trades: Iterable[Trade]) -> Tuple[float, float, float, int]:
    """Compute winrate, profit factor, max drawdown, and count from trades."""
    trades_list = list(trades)
    n = len(trades_list)
    if n == 0:
        return 0.0, 0.0, 0.0, 0

    wins = [t for t in trades_list if t.pnl > 0]
    losses = [t for t in trades_list if t.pnl < 0]

    winrate = len(wins) / n
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))

    if gross_loss == 0:
        profit_factor = gross_profit if gross_profit > 0 else 0.0
    else:
        profit_factor = gross_profit / gross_loss

    drawdown = _max_drawdown([t.pnl for t in trades_list])
    return winrate, profit_factor, drawdown, n


def compute_score(winrate: float, profit_factor: float, drawdown: float, weights: ScoreWeights) -> float:
    """Return score 0..100 from KPIs."""
    # Normalize KPIs into 0..1 bands
    win_norm = clamp((winrate - 0.45) / 0.15)  # target band ~45-60%
    pf_norm = clamp((profit_factor - 1.0) / 0.6)  # target band ~1.0-1.6
    dd_norm = clamp(1 - drawdown / 0.10)  # penalize drawdown above 10%

    weighted = (
        win_norm * weights.winrate
        + pf_norm * weights.profit_factor
        + dd_norm * weights.drawdown
    )
    weight_sum = weights.winrate + weights.profit_factor + weights.drawdown
    if weight_sum == 0:
        return 0.0
    score = 100.0 * weighted / weight_sum
    return clamp(score, 0.0, 100.0)


def interpolate(min_value: float, max_value: float, score: float) -> float:
    """Linear interpolation of score (0..100) into [min_value, max_value]."""
    t = clamp(score / 100.0, 0.0, 1.0)
    return min_value + (max_value - min_value) * t


def derive_parameters(score: float, bounds: ParamBounds) -> dict:
    """Map score to risk parameters."""
    return {
        "signal_threshold_pct": interpolate(bounds.threshold_min, bounds.threshold_max, score),
        "max_exposure_pct": interpolate(bounds.exposure_min, bounds.exposure_max, score),
        "max_position_pct": interpolate(bounds.position_min, bounds.position_max, score),
        "dry_wet_score": score,
    }


def fetch_trades_from_db(limit: int = DEFAULT_WINDOW) -> List[Trade]:
    """Fetch latest trades from Postgres. Returns empty list if psycopg2 missing."""
    if psycopg2 is None:
        return []
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "cdb_postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "claire_de_binare"),
            user=os.getenv("POSTGRES_USER", "claire_user"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        )
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT coalesce(pnl, 0) AS pnl,
                       extract(epoch from timestamp) AS ts
                FROM trades
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [Trade(pnl=float(r["pnl"]), timestamp=float(r["ts"])) for r in rows]
    finally:
        if conn:
            conn.close()


def publish_params_to_redis(redis_client, params: dict, ttl_seconds: int = 120) -> None:
    """Publish derived params to the adaptive_intensity key (consumed by Risk Manager)."""
    body = json.dumps(params)
    redis_client.setex("adaptive_intensity:current_params", ttl_seconds, body)


def compute_and_publish(redis_client, limit: int = DEFAULT_WINDOW) -> dict:
    """Fetch trades, compute score, derive params, publish to Redis, and return params."""
    trades = fetch_trades_from_db(limit=limit)
    winrate, profit_factor, drawdown, n = compute_kpis(trades)
    weights = ScoreWeights()
    score = compute_score(winrate, profit_factor, drawdown, weights)
    params = derive_parameters(score, ParamBounds())
    params["window_trades"] = n
    params["winrate"] = winrate
    params["profit_factor"] = profit_factor
    params["max_drawdown"] = drawdown
    publish_params_to_redis(redis_client, params)
    return params
