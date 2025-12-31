# Paper Trading Architektur

## Übersicht

Das Paper Trading System ermöglicht risikofreies Testen von Handelsstrategien mit realistischer Marktdatensimulation. Es bildet die Brücke zwischen Backtesting und Live-Trading.

## Trading Modi

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING MODE HIERARCHY                    │
├─────────────────────────────────────────────────────────────┤
│  PAPER (Default)  →  STAGED (72h Validation)  →  LIVE      │
│       ↓                      ↓                      ↓       │
│  MockExecutor          ShadowExecutor        LiveExecutor   │
│  Redis Streams         Dual-Write            Real Orders    │
│  Full Simulation       Compare Mode          Production     │
└─────────────────────────────────────────────────────────────┘
```

### Mode Enum (`src/core/execution.py`)
```python
class TradingMode(Enum):
    PAPER = "paper"      # Vollständige Simulation
    STAGED = "staged"    # Shadow-Trading mit Live-Vergleich
    LIVE = "live"        # Echte Aufträge
```

## Kernkomponenten

### 1. MockExecutor (`src/execution/mock_executor.py`)

Simuliert Order-Ausführung mit realistischen Marktbedingungen:

```
┌──────────────────────────────────────────────────────────┐
│                     MockExecutor                          │
├──────────────────────────────────────────────────────────┤
│  Input: Order                                             │
│    ↓                                                      │
│  [Latency Simulation] ─── config.latency_ms (50-200ms)   │
│    ↓                                                      │
│  [Slippage Model] ─────── slippage_bps (0-10 bps)        │
│    ↓                                                      │
│  [Fill Probability] ───── fill_rate (0.95-1.0)           │
│    ↓                                                      │
│  Output: ExecutionResult                                  │
└──────────────────────────────────────────────────────────┘
```

**Konfiguration:**
```python
@dataclass
class MockExecutorConfig:
    latency_ms: int = 100        # Simulierte Netzwerklatenz
    slippage_bps: float = 5.0    # Basis Points Slippage
    fill_rate: float = 0.98      # 98% Fill-Rate
    partial_fills: bool = True   # Teilausführungen erlauben
```

### 2. PaperTradingEngine (`src/execution/paper_trading.py`)

Zentrale Engine für Positions- und P&L-Management:

```
┌─────────────────────────────────────────────────────────────┐
│                   PaperTradingEngine                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Orders     │    │  Positions   │    │    P&L       │  │
│  │   Manager    │───▶│   Tracker    │───▶│  Calculator  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                    │          │
│         └───────────────────┴────────────────────┘          │
│                            │                                 │
│                     ┌──────▼──────┐                         │
│                     │   Redis     │                         │
│                     │   Streams   │                         │
│                     └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Event Sourcing via Redis Streams

Alle Trading-Events werden in Redis Streams persistiert:

```
Stream: paper:events:{session_id}
├── ORDER_PLACED      {order_id, symbol, side, qty, price, ts}
├── ORDER_FILLED      {order_id, fill_price, fill_qty, ts}
├── ORDER_CANCELLED   {order_id, reason, ts}
├── POSITION_OPENED   {position_id, symbol, side, entry_price, ts}
├── POSITION_CLOSED   {position_id, exit_price, pnl, ts}
└── PNL_UPDATE        {session_id, realized, unrealized, ts}
```

### Deterministic Replay

```python
async def replay_session(session_id: str, speed: float = 1.0):
    """Replay einer Paper Trading Session für Analyse."""
    events = await redis.xrange(f"paper:events:{session_id}")
    for event in events:
        await process_event(event, speed_multiplier=speed)
```

## Position Management

### FIFO-basierte Durchschnittsberechnung

```
┌─────────────────────────────────────────────────────────────┐
│                 Position State Machine                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐     BUY      ┌──────────┐     SELL          │
│   │  FLAT    │─────────────▶│   LONG   │───────────────┐   │
│   └──────────┘              └──────────┘               │   │
│        ▲                         │                     │   │
│        │                    SELL (partial)             │   │
│        │                         │                     │   │
│        │    ┌────────────────────▼───────────────┐    │   │
│        │    │  Update: avg_price, qty, pnl       │    │   │
│        │    └────────────────────────────────────┘    │   │
│        │                                              │   │
│        └──────────────────────────────────────────────┘   │
│                        CLOSE (full)                        │
└─────────────────────────────────────────────────────────────┘
```

### P&L Berechnung

```python
@dataclass
class PnLState:
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")

    @property
    def total_pnl(self) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl

def calculate_pnl(position: Position, current_price: Decimal) -> PnLState:
    """
    Realized: Geschlossene Trades
    Unrealized: Offene Positionen zu Mark-to-Market
    """
    unrealized = (current_price - position.avg_entry) * position.quantity
    if position.side == Side.SHORT:
        unrealized = -unrealized
    return PnLState(realized_pnl=position.realized, unrealized_pnl=unrealized)
```

## 72-Stunden Validierungsframework

Bevor Strategien von PAPER → STAGED wechseln:

```
┌─────────────────────────────────────────────────────────────┐
│              72-HOUR VALIDATION GATES                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Gate 1: Profitability                                       │
│  ├── Win Rate ≥ 55%                                         │
│  ├── Profit Factor ≥ 1.2                                    │
│  └── Sharpe Ratio ≥ 1.0                                     │
│                                                              │
│  Gate 2: Risk Management                                     │
│  ├── Max Drawdown ≤ 10%                                     │
│  ├── No single loss > 2% of capital                         │
│  └── Position sizing within limits                          │
│                                                              │
│  Gate 3: Execution Quality                                   │
│  ├── Slippage within 10 bps avg                             │
│  ├── Fill rate ≥ 95%                                        │
│  └── Latency p99 < 500ms                                    │
│                                                              │
│  Gate 4: Stability                                           │
│  ├── No crashes / exceptions                                 │
│  ├── Circuit breaker not triggered                          │
│  └── Consistent behavior across market conditions           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Sequenzdiagramm: Order Flow

```
┌────────┐     ┌──────────┐     ┌────────────┐     ┌───────┐
│Strategy│     │ PT Engine│     │MockExecutor│     │ Redis │
└───┬────┘     └────┬─────┘     └─────┬──────┘     └───┬───┘
    │               │                 │                │
    │ place_order() │                 │                │
    │──────────────▶│                 │                │
    │               │ validate()      │                │
    │               │────────┐        │                │
    │               │◀───────┘        │                │
    │               │                 │                │
    │               │ execute()       │                │
    │               │────────────────▶│                │
    │               │                 │ simulate_fill()│
    │               │                 │────────┐       │
    │               │                 │◀───────┘       │
    │               │                 │                │
    │               │ ExecutionResult │                │
    │               │◀────────────────│                │
    │               │                 │                │
    │               │ XADD ORDER_FILLED               │
    │               │─────────────────────────────────▶│
    │               │                 │                │
    │               │ update_position()               │
    │               │────────┐        │                │
    │               │◀───────┘        │                │
    │               │                 │                │
    │ OrderResult   │                 │                │
    │◀──────────────│                 │                │
    │               │                 │                │
```

## Test-Gap-Analyse

### Vorhandene Tests
- `tests/unit/test_mock_executor.py` - MockExecutor Unit Tests
- `tests/unit/test_paper_trading.py` - Engine Unit Tests
- `tests/integration/test_paper_flow.py` - Integration Tests

### Fehlende Tests (P0)
| Test | Priorität | Issue |
|------|-----------|-------|
| E2E Paper Trading Happy Path | P0 | #94 |
| Stress Test (1000+ Orders/min) | P1 | #93 |
| Deterministic Replay Validation | P1 | - |
| 72h Gate Validation | P0 | #94 |
| Circuit Breaker Integration | P0 | #94 |

### Fehlende Tests (P1)
| Test | Priorität | Issue |
|------|-----------|-------|
| Partial Fill Scenarios | P1 | - |
| Position Netting Edge Cases | P1 | - |
| Redis Stream Recovery | P1 | #95 |
| Multi-Symbol Concurrent Trading | P1 | - |

## Konfiguration

### Environment Variables
```bash
TRADING_MODE=paper              # paper|staged|live
PAPER_INITIAL_BALANCE=10000     # Starting capital
PAPER_LATENCY_MS=100            # Simulated latency
PAPER_SLIPPAGE_BPS=5            # Slippage in basis points
PAPER_FILL_RATE=0.98            # Fill probability
```

### Redis Keys
```
paper:sessions:{session_id}         # Session metadata
paper:positions:{session_id}        # Active positions
paper:orders:{session_id}           # Order history
paper:events:{session_id}           # Event stream
paper:pnl:{session_id}              # P&L snapshots
```

## Metriken (Prometheus)

```python
# Definiert in src/core/metrics.py
paper_orders_total = Counter("paper_orders_total", "Total paper orders", ["side", "status"])
paper_pnl_gauge = Gauge("paper_pnl_realized", "Realized P&L")
paper_position_count = Gauge("paper_positions_open", "Open positions")
paper_execution_latency = Histogram("paper_execution_seconds", "Execution latency")
```

## Referenzen

- Issue #91: Paper Trading Epic
- Issue #92: Research Analysis (dieses Dokument)
- Issue #94: E2E Paper Trading Tests
- `src/execution/mock_executor.py`
- `src/execution/paper_trading.py`
- `src/core/execution.py`
