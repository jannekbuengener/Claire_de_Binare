"""
Data Flow & Observability Engineer

Dieser Agent ist der Architekt der objektiven Datenrealität.
Er bestimmt, wie Ereignisse, Zustände und Metriken fließen und sichtbar werden,
ohne deren Bedeutung zu interpretieren oder Entscheidungen zu beeinflussen.
"""

import asyncio
import sys

from claude_agent_sdk import (
    ClaudeAgentOptions,
    query,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

from ..config import get_config

DATAFLOW_OBSERVER_PROMPT = """
Du bist der Data Flow & Observability Engineer für CDB (Claire de Binare).

## Deine Kernaufgabe (unumstößlich)

Du definierst und erzwingst die Datenontologie von CDB:

- **Event** = etwas ist passiert
- **State** = etwas ist jetzt so
- **Metric** = etwas wurde gezählt/gemessen
- **Log** = etwas wurde beobachtet

**Kein Datentyp darf sich als ein anderer verkleiden.**

## Deine Verantwortung

Du bist verantwortlich für:

- **Datenflüsse** (Redis Streams, Topics, Pipelines)
- **Telemetrie** (Prometheus, Metriken, Labels)
- **Beobachtbarkeit** (Grafana als Sichtfenster, nicht als Denkmaschine)
- **Kausalität** (Was kommt woher? Warum existiert diese Zahl?)

Du bist NICHT verantwortlich für:
- Entscheidungen
- Bewertungen
- Prognosen
- Optimierungen

Das ist kein Mangel – das ist Design.

## Deine wichtigste Grenze (Governance-Wahrheit)

Du darfst Wahrheit sichtbar machen, aber niemals erzeugen.

- Grafana zeigt → entscheidet nicht
- Redis transportiert → bewertet nicht
- Pipelines verbinden → interpretieren nicht

Sobald diese Grenze fällt, ist CDB keine deterministische Maschine mehr.

## Verfügbare Datenquellen

### Redis Streams (Event Sourcing)
- `stream.signals` - Trading Signals vom Signal Engine
- `stream.regime_signals` - ADX/ATR-basierte Regime-Signale
- `stream.allocation_decisions` - Position-Allocations
- `stream.orders` - Order-Events
- `stream.fills` - Execution Results
- `stream.bot_shutdown` - Emergency Stop Events

### Redis Pub/Sub Channels
- `market_data` - WebSocket → Signal Engine
- `signals` - Signal Engine → Risk Manager
- `orders` - Risk Manager → Execution
- `order_results` - Execution → DB Writer
- `portfolio_snapshots` - Portfolio State
- `alerts` - System Alerts

### Prometheus Targets (15s Scrape)
- `cdb_execution:8003/metrics` - Order Execution
- `cdb_core:8001/metrics` - Signal Engine
- `cdb_risk:8002/metrics` - Risk Manager
- `cdb_ws:8000/metrics` - WebSocket Handler

### PostgreSQL Tables
- `signals` - Generated trading signals
- `orders` - Validated orders
- `trades` - Executed trades
- `positions` - Current positions
- `portfolio_snapshots` - Equity curve history

### Event Logs
- `logs/events/events_YYYYMMDD.jsonl` - Structured event logs

## Dein Ziel

Jede Zahl ist erklärbar.
Jeder Graph ist rückführbar.
Jeder Zustand ist rekonstruierbar (Replay).

Du verhinderst den Zustand: "Die Zahl stimmt wahrscheinlich, aber wir wissen nicht mehr warum."
"""

# Tools für Data Flow & Observability
DATAFLOW_OBSERVER_TOOLS = [
    "Read",      # Dateien lesen
    "Glob",      # Dateien finden
    "Grep",      # In Dateien suchen
    "Bash",      # Commands ausführen (read-only empfohlen)
    "WebFetch",  # URLs abrufen
]

# MCP servers available for observability
DEFAULT_MCP_SERVERS = {
    "MCP_DOCKER": {
        "type": "stdio",
        "command": "docker",
        "args": ["mcp", "gateway", "run"]
    }
}


def create_dataflow_observer_options(
    cwd: str | None = None,
    mcp_servers: dict | None = None,
) -> ClaudeAgentOptions:
    """
    Erstellt ClaudeAgentOptions für den Data Flow & Observability Engineer.

    Args:
        cwd: Working Directory
        mcp_servers: MCP Server Konfiguration (default: DEFAULT_MCP_SERVERS)

    Returns:
        ClaudeAgentOptions für Observability-Aufgaben
    """
    return ClaudeAgentOptions(
        system_prompt=DATAFLOW_OBSERVER_PROMPT,
        allowed_tools=DATAFLOW_OBSERVER_TOOLS,
        mcp_servers=mcp_servers or DEFAULT_MCP_SERVERS,
        permission_mode="bypassPermissions",
        cwd=cwd,
    )


async def run_dataflow_observer(prompt: str | None = None) -> None:
    """
    Führt den Data Flow & Observability Engineer aus.

    Args:
        prompt: Was soll beobachtet/analysiert werden?
    """
    config = get_config()

    if prompt is None:
        prompt = "Was ist der aktuelle Zustand der Datenflüsse? Zeige mir die aktiven Redis Streams und ihre Consumer Groups."

    options = create_dataflow_observer_options(cwd=config.cdb_root)

    print("📊 Data Flow & Observability Engineer")
    print(f"📂 Working Directory: {config.cdb_root}")
    print(f"❓ Abfrage: {prompt}")
    print("-" * 60)

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                print()

            elif isinstance(message, ResultMessage):
                print("-" * 60)
                if message.is_error:
                    print(f"❌ Error: {message.result}")
                else:
                    print(f"✅ Abfrage abgeschlossen in {message.duration_ms}ms")

    except KeyboardInterrupt:
        print("\n⚠️ Abfrage abgebrochen")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main() -> None:
    """CLI Entry Point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CDB Data Flow & Observability Engineer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  cdb-dataflow                                         # Default-Abfrage
  cdb-dataflow "Zeige mir alle aktiven Redis Streams"
  cdb-dataflow "Woher kommt der Wert in der Position für BTC?"
  cdb-dataflow "Erkläre den Datenfluss von Market Data zu Order"
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Was soll beobachtet/analysiert werden?",
    )

    args = parser.parse_args()
    asyncio.run(run_dataflow_observer(args.prompt))


if __name__ == "__main__":
    main()
