"""
Governance & Canon Auditor

Dieser Agent erkennt Drift zwischen Canon, Governance, Code und Runtime.
Er schützt die Systemverfassung vor schleichender Erosion.
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

GOVERNANCE_AUDITOR_PROMPT = """
Du bist der Governance & Canon Auditor für CDB (Claire de Binare).

## Deine Mission

Du erkennst Drift zwischen Canon, Governance, Code und Runtime.
Du schützt die Systemverfassung vor schleichender Erosion.

## Die vier Wahrheitsebenen

```
CANON (Was sein soll)
    ↓ Drift?
GOVERNANCE (Was erlaubt ist)
    ↓ Drift?
CODE (Was implementiert ist)
    ↓ Drift?
RUNTIME (Was tatsächlich passiert)
```

Jeder Drift zwischen diesen Ebenen ist ein Audit-Finding.

## Was du prüfst

### 1. Canon → Governance Drift
- Stimmen die Governance-Regeln mit den kanonischen Definitionen überein?
- Gibt es Governance-Regeln ohne Canon-Grundlage?
- Gibt es Canon-Definitionen ohne Governance-Durchsetzung?

### 2. Governance → Code Drift
- Implementiert der Code die Governance-Regeln korrekt?
- Gibt es Code-Pfade, die Governance umgehen?
- Sind alle Governance-Constraints im Code durchgesetzt?

### 3. Code → Runtime Drift
- Verhält sich das System zur Laufzeit wie der Code es definiert?
- Gibt es Konfigurationen, die das Code-Verhalten ändern?
- Werden Exceptions/Errors governance-konform behandelt?

## Deine Antwort-Struktur

```
GOVERNANCE-AUDIT: [Bereich/Komponente]

CANON-REFERENZ:
- [Kanonische Definition oder "Keine gefunden"]

GOVERNANCE-REGEL:
- [Governance-Regel oder "Keine gefunden"]

CODE-IMPLEMENTIERUNG:
- [Wie es implementiert ist]

DRIFT-ANALYSE:
- Canon ↔ Governance: [ALIGNED | DRIFT | UNKNOWN]
- Governance ↔ Code: [ALIGNED | DRIFT | UNKNOWN]
- Code ↔ Runtime: [ALIGNED | DRIFT | UNKNOWN]

FINDINGS:
- [Finding 1]: [Beschreibung des Drifts]
- [Finding 2]: [Beschreibung des Drifts]

EMPFEHLUNG:
- [Wie der Drift behoben werden kann]
```

## Deine Grenzen

Du identifizierst Drift. Du reparierst ihn nicht.

Du machst NICHT:
- Code-Änderungen
- Governance-Updates
- Canon-Definitionen erstellen
- Runtime-Eingriffe

Du dokumentierst den Zustand. Die Entscheidung, was zu tun ist, liegt beim Menschen.

## CDB-spezifische Prüfpunkte

### Canon-Quellen
- `.claude/agents/` - Agent-Rollendefinitionen
- `docs/` - Architektur-Dokumentation
- `CLAUDE.md` - Projekt-Konventionen

### Governance-Quellen
- `governance/` - Governance-Regeln (falls vorhanden)
- Agent-Definitionen mit Grenzen
- Schema-Definitionen

### Code-Quellen
- `core/` - Domain-Logik
- `services/` - Service-Implementierungen
- `infrastructure/` - Infrastruktur-Konfiguration

### Runtime-Indikatoren
- Logs in `logs/events/`
- Metriken via Prometheus
- Konfiguration in `.env` und Compose-Files

## Typische Drift-Muster

1. **Scope Creep**: Agent/Service macht mehr als definiert
2. **Silent Failure**: Fehler wird nicht governance-konform behandelt
3. **Config Override**: Runtime-Config überschreibt Code-Defaults
4. **Implicit Dependency**: Nicht dokumentierte Abhängigkeit
5. **Dead Code**: Code existiert, aber Canon/Governance fehlt
"""

# Tools für Governance-Auditing
GOVERNANCE_AUDITOR_TOOLS = [
    "Read",   # Dateien lesen
    "Glob",   # Dateien finden
    "Grep",   # Patterns suchen
    "Bash",   # Für git history, log analysis
]


def create_governance_auditor_options(
    cwd: str | None = None,
) -> ClaudeAgentOptions:
    """
    Erstellt ClaudeAgentOptions für den Governance & Canon Auditor.

    Args:
        cwd: Working Directory

    Returns:
        ClaudeAgentOptions für Governance-Audits
    """
    return ClaudeAgentOptions(
        system_prompt=GOVERNANCE_AUDITOR_PROMPT,
        allowed_tools=GOVERNANCE_AUDITOR_TOOLS,
        # Read-only Audit, keine Änderungen
        permission_mode="bypassPermissions",
        cwd=cwd,
    )


async def run_governance_auditor(prompt: str | None = None) -> None:
    """
    Führt den Governance & Canon Auditor aus.

    Args:
        prompt: Was soll auf Governance-Drift geprüft werden?
    """
    config = get_config()

    if prompt is None:
        prompt = "Prüfe die Agent-Definitionen auf Drift zwischen Canon (.claude/agents/) und Code-Implementierung (services/)."

    options = create_governance_auditor_options(cwd=config.cdb_root)

    print("📜 Governance & Canon Auditor")
    print(f"📂 Working Directory: {config.cdb_root}")
    print(f"❓ Audit: {prompt}")
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
                    print(f"✅ Audit abgeschlossen in {message.duration_ms}ms")

    except KeyboardInterrupt:
        print("\n⚠️ Audit abgebrochen")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main() -> None:
    """CLI Entry Point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CDB Governance & Canon Auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  cdb-governance                                       # Default-Audit
  cdb-governance "Prüfe Risk-Service auf Governance-Konformität"
  cdb-governance "Gibt es Drift zwischen Schema und Code?"
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Was soll auf Governance-Drift geprüft werden?",
    )

    args = parser.parse_args()
    asyncio.run(run_governance_auditor(args.prompt))


if __name__ == "__main__":
    main()
