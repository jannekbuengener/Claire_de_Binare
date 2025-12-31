# CDB Agent SDK - Data Flow & Observability Engineer

Ein Claude Agent SDK Agent, der die objektive Datenrealität von CDB (Claire de Binare) sichtbar macht, ohne zu interpretieren oder zu entscheiden.

## Rolle

Der **Data Flow & Observability Engineer** ist verantwortlich für:

- **Datenflüsse** (Redis Streams, Topics, Pipelines)
- **Telemetrie** (Prometheus, Metriken, Labels)
- **Beobachtbarkeit** (Grafana als Sichtfenster)
- **Kausalität** (Was kommt woher? Warum existiert diese Zahl?)

### Governance-Grenzen

Der Agent darf **Wahrheit sichtbar machen**, aber **niemals erzeugen**:

- Grafana zeigt → entscheidet nicht
- Redis transportiert → bewertet nicht
- Pipelines verbinden → interpretieren nicht

## Installation

```bash
cd cdb_agent_sdk
uv sync
```

## Verwendung

### CLI

```bash
# Default: Datenflüsse prüfen
uv run cdb-agent

# Spezifische Abfrage
uv run cdb-agent "Zeige Redis Stream Statistiken"

# Event Logs analysieren
uv run cdb-agent "Analysiere die letzten Event Logs"
```

### Python API

```python
import asyncio
from cdb_agent_sdk import main

# Mit Default-Prompt
asyncio.run(main())

# Mit spezifischem Prompt
asyncio.run(main("Erkläre den Datenfluss von Market Data zu Signals"))
```

### Programmatisch mit Options

```python
import asyncio
from claude_agent_sdk import query
from cdb_agent_sdk import create_agent_options

async def analyze():
    options = create_agent_options(
        cwd="/path/to/cdb",
        allowed_tools=["Read", "Grep", "Glob"],
    )

    async for message in query(
        prompt="Zeige alle Redis Stream Konfigurationen",
        options=options
    ):
        print(message)

asyncio.run(analyze())
```

## Datenquellen

Der Agent hat Zugriff auf:

| Quelle | Beschreibung |
|--------|--------------|
| Redis Streams | `stream.signals`, `stream.orders`, `stream.fills`, etc. |
| Redis Pub/Sub | `market_data`, `signals`, `orders`, `alerts` |
| Prometheus | Metriken von allen CDB Services |
| PostgreSQL | `signals`, `orders`, `trades`, `positions` |
| Event Logs | `logs/events/events_YYYYMMDD.jsonl` |

## Datenontologie

Der Agent erzwingt die CDB Datenontologie:

| Typ | Bedeutung |
|-----|-----------|
| **Event** | Etwas ist passiert |
| **State** | Etwas ist jetzt so |
| **Metric** | Etwas wurde gezählt/gemessen |
| **Log** | Etwas wurde beobachtet |

**Kein Datentyp darf sich als ein anderer verkleiden.**

## Konfiguration

Umgebungsvariablen (optional):

```bash
# .env
GRAFANA_URL=http://localhost:3000
REDIS_HOST=localhost
REDIS_PORT=6379
POSTGRES_HOST=localhost
USE_MCP_DOCKER=1
```

## Authentifizierung

Keine API-Key-Konfiguration erforderlich. Der Agent nutzt die bestehende Claude Code Max Plan Authentifizierung.

## Entwicklung

```bash
# Tests ausführen
uv run pytest

# Type checking
uv run mypy src/
```

## Lizenz

Teil des CDB (Claire de Binare) Projekts.
