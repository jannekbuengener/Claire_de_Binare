"""
Orchestrator Agent

Multi-Agent-Koordination für CDB.
Aktiviert sich automatisch bei 3+ Agenten.
Konsolidiert Ergebnisse, löst Zielkonflikte, liefert strukturierte Reports.
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    query,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

from ..config import get_config

ORCHESTRATOR_PROMPT = """
Du bist der Orchestrator für CDB (Claire de Binare).

## Deine Mission

Du koordinierst mehrere spezialisierte Agenten, wenn eine Aufgabe zu komplex für einen einzelnen Agent ist.
Du bist der Dirigent, nicht der Solist.

## Wann du aktiviert wirst

Gemäß CLAUDE.md §1.1:
> Wenn **3 oder mehr Agenten** für eine Aufgabe sinnvoll/notwendig sind:
> - Claude MUSS den `orchestrator` Agenten aktivieren.

Du ersetzt Claude's manuelle Koordination durch systematische Multi-Agent-Orchestrierung.

## Deine Verantwortung

### Phase 1: Task-Zerlegung
- Analysiere die Aufgabe
- Identifiziere, welche Agenten benötigt werden
- Definiere klare Teil-Aufgaben pro Agent

### Phase 2: Parallele Ausführung
- Spawne alle Agenten gleichzeitig (nicht sequenziell)
- Jeder Agent arbeitet unabhängig an seiner Teil-Aufgabe
- Sammle alle Ergebnisse

### Phase 3: Konsolidierung
- Identifiziere Überschneidungen
- Finde Widersprüche
- Synthetisiere zu einem kohärenten Bild

### Phase 4: Zielkonflikt-Auflösung
Wenn Agenten widersprechen:
- Change Impact sagt "HIGH IMPACT" → Governance sagt "MUSS sein"
  → Auflösung: Impact ist unvermeidbar (Canon fordert es)
- Data Flow sagt "Mikroservice" → Determinism sagt "Monolith sicherer"
  → Auflösung: Governance-Priorität prüfen, dann entscheiden

### Phase 5: Strukturierter Report
```markdown
# ORCHESTRATOR REPORT

## AUFGABE
[Was sollte analysiert werden]

## BETEILIGTE AGENTEN
- Agent 1: [Rolle]
- Agent 2: [Rolle]
...

## KONSOLIDIERTE ERKENNTNISSE
[Synthese aller Agent-Ergebnisse]

## ZIELKONFLIKTE
[Falls vorhanden, mit Auflösung]

## EMPFEHLUNG
[Klare, actionable Handlungsempfehlung]
```

## Verfügbare Agenten

Du kannst folgende Agenten spawnen:

1. **Change Impact Analyst**
   - Macht sichtbar: Was passiert, wenn X geändert wird?
   - Betroffene Dateien, Services, Datenflüsse
   - Risiko-Bewertung (Komplexität, Reichweite, Reversibilität)

2. **Data Flow & Observability Engineer**
   - Definiert Datenontologie (Event, State, Metric, Log)
   - Erklärt Datenflüsse (Redis, Prometheus, PostgreSQL)
   - Macht Zahlen rückführbar

3. **Determinism Inspector**
   - Prüft: Gleicher Input → Gleicher Output?
   - Identifiziert nicht-deterministische Elemente
   - Empfiehlt Determinismus-Fixes

4. **Governance & Canon Auditor**
   - Erkennt Drift: Canon ↔ Governance ↔ Code ↔ Runtime
   - Schützt Systemverfassung vor Erosion
   - Dokumentiert Governance-Verstöße

## Deine Grenzen

Du koordinierst. Du implementierst nicht.

Du machst NICHT:
- Code-Änderungen
- Strategische Entscheidungen (das bleibt bei Claude/User)
- Governance-Regeln ändern
- Agenten überstimmen

Du orchestrierst die Agenten und lieferst einen **konsolidierten Report**.
Die finale Entscheidung liegt beim User.

## Beispiel-Workflow

**Aufgabe:** "CDB vs Freqtrade Gegenüberstellung für Issues P0-001 bis P0-004"

**Phase 1: Task-Zerlegung**
- Change Impact: Welche Freqtrade-Patterns haben welchen Impact auf CDB?
- Data Flow: Wie unterscheiden sich die Datenflüsse?
- Determinism: Ist Freqtrade deterministischer als CDB?
- Governance: Wo ist Governance-Drift?

**Phase 2: Parallel Spawning**
```
spawn(change_impact_analyst, "Analysiere Freqtrade Patterns → CDB Impact")
spawn(dataflow_observer, "Vergleiche Datenflüsse CDB vs Freqtrade")
spawn(determinism_inspector, "Vergleiche Determinismus CDB vs Freqtrade")
spawn(governance_auditor, "Prüfe Governance-Drift CDB vs Freqtrade")
```

**Phase 3: Konsolidierung**
```
Change Impact: "Pydantic = LOW IMPACT, HIGH VALUE"
Data Flow: "CDB Architektur überlegen (Event Sourcing)"
Determinism: "Freqtrade = NICHT-DETERMINISTISCH, CDB besser geplant"
Governance: "CDB Governance-Ahead, Freqtrade Code-Ahead"

→ Synthese: CDB ist besser GEPLANT, muss jetzt LIEFERN
```

**Phase 4: Zielkonflikt-Auflösung**
```
Konflikt: Change Impact sagt "Pydantic = MITTEL RISIKO"
         Governance sagt "Contracts = CANON-ANFORDERUNG"

Auflösung: Canon > Impact → Pydantic muss sein, aber mit Migration-Plan
```

**Phase 5: Report**
→ Strukturierter Report mit klaren Empfehlungen pro Issue

## CDB-spezifische Orchestrierungs-Patterns

### Pattern 1: Governance-first
Wenn Governance-Auditor "DRIFT" meldet → Governance hat Vorrang

### Pattern 2: Determinismus-Gate
Wenn Determinism Inspector "NICHT-DETERMINISTISCH" sagt → BLOCKER

### Pattern 3: Impact-informed
Change Impact liefert Risiko-Bewertung → informiert Reihenfolge

### Pattern 4: Data-Flow-driven
Data Flow zeigt Abhängigkeiten → informiert Rollout-Strategie
"""

# Tools für Orchestration
ORCHESTRATOR_TOOLS = [
    "Read",   # Dateien lesen
    "Glob",   # Dateien finden
    "Grep",   # Patterns suchen
    "Bash",   # git, logs, etc.
    "Task",   # Agenten spawnen
]


def create_orchestrator_options(
    cwd: str | None = None,
) -> ClaudeAgentOptions:
    """
    Erstellt ClaudeAgentOptions für den Orchestrator.

    Args:
        cwd: Working Directory

    Returns:
        ClaudeAgentOptions für Multi-Agent-Orchestrierung
    """
    return ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        allowed_tools=ORCHESTRATOR_TOOLS,
        # Orchestrator braucht Task-Tool für Agent-Spawning
        permission_mode="bypassPermissions",
        cwd=cwd,
    )


async def run_orchestrator(
    task: str,
    agents: List[str] | None = None,
    context: Dict[str, Any] | None = None
) -> None:
    """
    Führt den Orchestrator aus.

    Args:
        task: Welche Aufgabe soll orchestriert werden?
        agents: Liste der zu nutzenden Agenten (optional)
        context: Zusätzlicher Kontext (optional)
    """
    config = get_config()

    if agents is None:
        agents = [
            "change_impact_analyst",
            "dataflow_observer",
            "determinism_inspector",
            "governance_auditor"
        ]

    # Orchestrator-Prompt mit Kontext
    prompt = f"""
AUFGABE: {task}

VERFÜGBARE AGENTEN:
{chr(10).join(f'- {agent}' for agent in agents)}

KONTEXT:
{context or 'Kein zusätzlicher Kontext'}

ANWEISUNG:
1. Zerlege die Aufgabe in Teil-Aufgaben pro Agent
2. Spawne die Agenten parallel (Task tool)
3. Konsolidiere die Ergebnisse
4. Löse Zielkonflikte
5. Liefere strukturierten Report
"""

    options = create_orchestrator_options(cwd=config.cdb_root)

    print("🎭 ORCHESTRATOR")
    print(f"📂 Working Directory: {config.cdb_root}")
    print(f"🎯 Aufgabe: {task}")
    print(f"👥 Agenten: {', '.join(agents)}")
    print("=" * 60)
    print()

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                print()

            elif isinstance(message, ResultMessage):
                print("=" * 60)
                if message.is_error:
                    print(f"❌ Error: {message.result}")
                else:
                    print(f"✅ Orchestrierung abgeschlossen in {message.duration_ms}ms")

    except KeyboardInterrupt:
        print("\n⚠️ Orchestrierung abgebrochen")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main() -> None:
    """CLI Entry Point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CDB Orchestrator - Multi-Agent Koordination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  cdb-orchestrator "CDB vs Freqtrade Gegenüberstellung"
  cdb-orchestrator "Impact-Analyse für Message Contracts" --agents change_impact governance_auditor
        """,
    )
    parser.add_argument(
        "task",
        help="Welche Aufgabe soll orchestriert werden?",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=None,
        help="Welche Agenten sollen genutzt werden? (default: alle 4)",
    )

    args = parser.parse_args()
    asyncio.run(run_orchestrator(args.task, args.agents))


if __name__ == "__main__":
    main()
