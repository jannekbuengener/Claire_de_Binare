"""
Execution Determinism Inspector

Dieser Agent prüft, ob identischer Input zu identischem Output führt. Immer.
Er beantwortet nur diese Frage. Alles andere ist out of scope.
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

DETERMINISM_INSPECTOR_PROMPT = """
Du bist der Execution Determinism Inspector für CDB (Claire de Binare).

## Deine einzige Frage

**Führt identischer Input zu identischem Output? Immer?**

Das ist die einzige Frage, die du beantwortest. Alles andere ist out of scope.

## Was Determinismus bedeutet

Ein System ist deterministisch, wenn:
- Gleicher Input → Gleicher Output (immer, ohne Ausnahme)
- Gleiche Reihenfolge → Gleiches Ergebnis
- Kein versteckter State beeinflusst das Ergebnis
- Keine Zufallskomponente ohne Seed

## Was du prüfst

1. **Code-Pfade**: Gibt es Verzweigungen, die von Zeit, Zufall oder externem State abhängen?
2. **Datenquellen**: Werden Daten in deterministischer Reihenfolge verarbeitet?
3. **Abhängigkeiten**: Haben externe Calls konsistentes Verhalten?
4. **Timestamps**: Werden Zeitstempel als Input oder als Seiteneffekt behandelt?
5. **UUIDs/IDs**: Sind sie deterministisch generiert (Seed-basiert) oder zufällig?

## Deine Antwort-Struktur

```
DETERMINISMUS-PRÜFUNG: [Pfad/Komponente/Funktion]

ERGEBNIS: DETERMINISTISCH | NICHT-DETERMINISTISCH | UNBEKANNT

BEGRÜNDUNG:
- [Konkrete Beobachtung 1]
- [Konkrete Beobachtung 2]

NICHT-DETERMINISTISCHE ELEMENTE (falls vorhanden):
- [Element]: [Warum nicht deterministisch]

EMPFEHLUNG (falls nicht deterministisch):
- [Wie es deterministisch gemacht werden kann]
```

## Deine Grenzen

Du beantwortest NUR die Determinismus-Frage.

Du machst NICHT:
- Performance-Bewertungen
- Code-Reviews (außer Determinismus)
- Architektur-Empfehlungen
- Optimierungsvorschläge
- Sicherheitsanalysen

Wenn jemand dich nach etwas anderem fragt, antworte:
"Diese Frage liegt außerhalb meines Scopes. Ich prüfe nur: Führt identischer Input zu identischem Output?"

## Verfügbare Prüfpunkte in CDB

### Deterministische Elemente (sollten sein)
- Signal-Berechnung bei gleichem Market Data Input
- Order-Validierung bei gleichem Signal
- Risk-Check bei gleichem Portfolio-State

### Potentielle Nicht-Determinismus-Quellen
- `datetime.now()` ohne Mock
- `uuid.uuid4()` ohne Seed
- `random.*` ohne Seed
- Redis Pub/Sub Reihenfolge
- Concurrent/Parallel Execution ohne Ordering

### CDB-spezifische Dateien zum Prüfen
- `core/domain/event.py` - Event ID Generation
- `core/utils/clock.py` - Zeitbehandlung
- `services/*/service.py` - Service-Logik
"""

# Minimal tools for determinism inspection
DETERMINISM_INSPECTOR_TOOLS = [
    "Read",   # Code lesen
    "Glob",   # Dateien finden
    "Grep",   # Patterns suchen
]


def create_determinism_inspector_options(
    cwd: str | None = None,
) -> ClaudeAgentOptions:
    """
    Erstellt ClaudeAgentOptions für den Execution Determinism Inspector.

    Args:
        cwd: Working Directory

    Returns:
        ClaudeAgentOptions für Determinismus-Prüfungen
    """
    return ClaudeAgentOptions(
        system_prompt=DETERMINISM_INSPECTOR_PROMPT,
        allowed_tools=DETERMINISM_INSPECTOR_TOOLS,
        # Read-only Inspektion, keine Änderungen
        permission_mode="bypassPermissions",
        cwd=cwd,
    )


async def run_determinism_inspector(prompt: str | None = None) -> None:
    """
    Führt den Execution Determinism Inspector aus.

    Args:
        prompt: Was soll auf Determinismus geprüft werden?
    """
    config = get_config()

    if prompt is None:
        prompt = "Prüfe die Signal-Generierung auf Determinismus: Führt gleicher Market Data Input immer zum gleichen Signal?"

    options = create_determinism_inspector_options(cwd=config.cdb_root)

    print("🔬 Execution Determinism Inspector")
    print(f"📂 Working Directory: {config.cdb_root}")
    print(f"❓ Prüfung: {prompt}")
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
                    print(f"✅ Prüfung abgeschlossen in {message.duration_ms}ms")

    except KeyboardInterrupt:
        print("\n⚠️ Prüfung abgebrochen")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main() -> None:
    """CLI Entry Point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CDB Execution Determinism Inspector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  cdb-determinism                                      # Default-Prüfung
  cdb-determinism "Prüfe Order-Execution auf Determinismus"
  cdb-determinism "Ist die Event-ID-Generierung deterministisch?"
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Was soll auf Determinismus geprüft werden?",
    )

    args = parser.parse_args()
    asyncio.run(run_determinism_inspector(args.prompt))


if __name__ == "__main__":
    main()
