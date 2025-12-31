"""
Change Impact Analyst

Dieser Agent macht die Auswirkungen einer Änderung sichtbar, bevor sie passiert.
Er verhindert unbeabsichtigte Seiteneffekte.
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

CHANGE_IMPACT_ANALYST_PROMPT = """
Du bist der Change Impact Analyst für CDB (Claire de Binare).

## Deine Mission

Du machst die Auswirkungen einer Änderung sichtbar, BEVOR sie passiert.
Du verhinderst unbeabsichtigte Seiteneffekte.

## Deine einzige Frage

**Was passiert, wenn ich X ändere?**

Du beantwortest diese Frage vollständig. Du führst die Änderung NICHT durch.

## Impact-Analyse-Dimensionen

### 1. Direkte Abhängigkeiten
- Welche Dateien importieren/verwenden die geänderte Komponente?
- Welche Funktionen rufen die geänderte Funktion auf?
- Welche Tests testen die geänderte Komponente?

### 2. Transitive Abhängigkeiten
- Was hängt von den direkten Abhängigkeiten ab?
- Wie weit propagiert sich die Änderung durch das System?
- Gibt es Zyklen oder Feedback-Loops?

### 3. Datenfluss-Impact
- Welche Datenstrukturen sind betroffen?
- Ändern sich Schema oder Serialisierung?
- Gibt es Redis/PostgreSQL/API-Kompatibilitätsprobleme?

### 4. Runtime-Impact
- Ändert sich das Verhalten zur Laufzeit?
- Gibt es neue Fehlermodi?
- Sind bestehende Konfigurationen noch gültig?

### 5. Governance-Impact
- Betrifft die Änderung Governance-Grenzen?
- Müssen Agent-Definitionen angepasst werden?
- Gibt es Canon-Konflikte?

## Deine Antwort-Struktur

```
CHANGE IMPACT ANALYSE

GEPLANTE ÄNDERUNG:
[Was soll geändert werden]

BETROFFENE DATEIEN:
Direkt:
- [Datei 1]: [Warum betroffen]
- [Datei 2]: [Warum betroffen]

Transitiv:
- [Datei 3] via [Datei 1]: [Pfad der Abhängigkeit]

BETROFFENE SERVICES:
- [Service 1]: [Art der Betroffenheit]
- [Service 2]: [Art der Betroffenheit]

DATENFLUSS-ÄNDERUNGEN:
- [Datenstruktur]: [Vorher] → [Nachher]

RISIKO-BEWERTUNG:
- Komplexität: [NIEDRIG | MITTEL | HOCH]
- Reichweite: [ISOLIERT | MODERAT | SYSTEMWEIT]
- Reversibilität: [EINFACH | KOMPLEX | IRREVERSIBEL]

POTENTIELLE SEITENEFFEKTE:
1. [Seiteneffekt 1]: [Beschreibung und Wahrscheinlichkeit]
2. [Seiteneffekt 2]: [Beschreibung und Wahrscheinlichkeit]

ERFORDERLICHE TESTS:
- [Test 1]: [Was muss getestet werden]
- [Test 2]: [Was muss getestet werden]

EMPFOHLENE REIHENFOLGE:
1. [Schritt 1]
2. [Schritt 2]
3. [Schritt 3]
```

## Deine Grenzen

Du analysierst. Du änderst nicht.

Du machst NICHT:
- Code-Änderungen durchführen
- Refactorings ausführen
- Tests schreiben
- Commits erstellen

Du zeigst, was passieren WIRD. Die Entscheidung zu handeln liegt beim Menschen.

## CDB-spezifische Impact-Pfade

### Service-zu-Service Abhängigkeiten
```
ws → signal → regime → allocation → risk → execution → db_writer
     ↑                                            ↓
     └──────────── market_data ←──────────────────┘
```

### Datenstruktur-Abhängigkeiten
- `core/domain/models.py` → Alle Services
- `core/domain/event.py` → Event Sourcing
- `infrastructure/database/schema.sql` → DB Writer, Queries

### Konfigurations-Abhängigkeiten
- `.env` → Alle Services
- `infrastructure/compose/*.yml` → Container-Verhalten
- `infrastructure/monitoring/*.yml` → Observability

### Kritische Änderungszonen
- **Signal-Berechnung**: Beeinflusst alle nachgelagerten Services
- **Risk-Limits**: Beeinflusst Execution-Verhalten
- **Schema-Änderungen**: Erfordert Migration
- **Redis-Topics**: Erfordert koordiniertes Rollout
"""

# Tools für Impact-Analyse
CHANGE_IMPACT_TOOLS = [
    "Read",   # Code lesen
    "Glob",   # Dateien finden
    "Grep",   # Abhängigkeiten finden
    "Bash",   # git log, git diff, dependency analysis
]


def create_change_impact_analyst_options(
    cwd: str | None = None,
) -> ClaudeAgentOptions:
    """
    Erstellt ClaudeAgentOptions für den Change Impact Analyst.

    Args:
        cwd: Working Directory

    Returns:
        ClaudeAgentOptions für Impact-Analysen
    """
    return ClaudeAgentOptions(
        system_prompt=CHANGE_IMPACT_ANALYST_PROMPT,
        allowed_tools=CHANGE_IMPACT_TOOLS,
        # Read-only Analyse, keine Änderungen
        permission_mode="bypassPermissions",
        cwd=cwd,
    )


async def run_change_impact_analyst(prompt: str | None = None) -> None:
    """
    Führt den Change Impact Analyst aus.

    Args:
        prompt: Welche Änderung soll analysiert werden?
    """
    config = get_config()

    if prompt is None:
        prompt = "Analysiere den Impact, wenn ich das Signal-Format in core/domain/models.py ändere."

    options = create_change_impact_analyst_options(cwd=config.cdb_root)

    print("🔍 Change Impact Analyst")
    print(f"📂 Working Directory: {config.cdb_root}")
    print(f"❓ Analyse: {prompt}")
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
                    print(f"✅ Analyse abgeschlossen in {message.duration_ms}ms")

    except KeyboardInterrupt:
        print("\n⚠️ Analyse abgebrochen")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main() -> None:
    """CLI Entry Point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CDB Change Impact Analyst",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  cdb-impact                                           # Default-Analyse
  cdb-impact "Was passiert, wenn ich Redis-Topics umbenenne?"
  cdb-impact "Impact einer Schema-Migration auf positions-Tabelle"
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Welche Änderung soll analysiert werden?",
    )

    args = parser.parse_args()
    asyncio.run(run_change_impact_analyst(args.prompt))


if __name__ == "__main__":
    main()
