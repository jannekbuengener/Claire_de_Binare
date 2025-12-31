# Allocation Service

Deterministische Allokationsentscheidungen basierend auf Regime- und Performance-Signalen.

## Streams
- Input: `stream.regime_signals`, `stream.fills`, `stream.bot_shutdown`
- Output: `stream.allocation_decisions`

## Pflicht-ENV
- `ALLOCATION_RULES_JSON`
- `ALLOCATION_REGIME_MIN_STABLE_SECONDS`

## Fixed Params (Spec)
- Lookback: 30 Trades **und** 7 Tage
- EMA Alpha: 0.3
- Cooldown: 72h
