# Multi-LLM Discussion Pipeline

**Ein mehrstufiges KI-Diskussionssystem für technische Wissenssynthese und Entscheidungsfindung**

## 🎯 Überblick

Dieses System orchestriert Diskussionen zwischen mehreren spezialisierten KI-Agenten (Gemini, GitHub Copilot, Claude), um:

- **Komplexes Wissen** aus Research-Dokumenten zu synthetisieren
- **Kritische Bewertungen** aus verschiedenen Perspektiven zu erzeugen
- **Konflikte und Widersprüche** explizit sichtbar zu machen
- **Reife Themen** in umsetzbare GitHub Issues zu überführen

## 🏗️ Architektur

```
┌─────────────────┐
│ Knowledge Base  │ Markdown Research Files
│  (Proposals)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini Agent   │ Research Synthesis & Fact Extraction
│                 │ → Identifies theoretical frameworks
│                 │ → Extracts evidence and gaps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Copilot Agent   │ Technical Architecture Analysis
│                 │ → Implementation feasibility
│                 │ → CRITICAL: Challenges Gemini's claims
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Claude Agent   │ Meta-Synthesis & Strategic Evaluation
│                 │ → Resolves conflicts between agents
│                 │ → Gap analysis (what both missed)
│                 │ → Gate recommendation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Human Gate     │ Decision Point (Optional Intervention)
│                 │ → PROCEED → GitHub Issue
│                 │ → REVISE → Additional analysis
│                 │ → REJECT → Archive with rationale
└─────────────────┘
```

## 🚀 Schnellstart

### Installation

```bash
# Dependencies installieren
pip install -r requirements.txt

# Umgebungsvariablen setzen
export ANTHROPIC_API_KEY="your_claude_api_key"
export GOOGLE_API_KEY="your_gemini_api_key"
export GITHUB_TOKEN="your_github_token"  # Optional: für Copilot
```

### Erste Diskussion starten

```bash
# 1. Proposal-Datei erstellen
cat > discussions/proposals/PROPOSAL_001_bsde_vs_control.md <<EOF
# BSDE vs. Stochastic Control

## Problem
Wir müssen entscheiden, welches mathematische Framework für unser
Risiko-Modellierungssystem verwendet werden soll...

[Weitere Details...]
EOF

# 2. Pipeline ausführen
python scripts/run_discussion.py discussions/proposals/PROPOSAL_001_bsde_vs_control.md

# 3. Ergebnisse reviewen
ls discussions/threads/THREAD_*/
```

### Beispiel-Output

```
🚀 Starting discussion pipeline...
============================================================
🤖 Running gemini (Step 1/3)
🤖 Running copilot (Step 2/3)
🤖 Running claude (Step 3/3)
✅ Pipeline completed

============================================================
📊 Validating discussion quality...
   Disagreements found: 2
   Outputs analyzed: 3
   Echo chamber score: 0.35

✅ Pipeline completed successfully!
   Results: discussions/threads/THREAD_1734437234/DIGEST.md
```

## 📂 Verzeichnisstruktur

```
discussions/
├── proposals/           # Input: Diskussionsvorlagen (.md)
├── threads/            # Output: Aktive Diskussionen
│   └── THREAD_*/
│       ├── manifest.json           # Pipeline-Metadaten
│       ├── 01_gemini_output.md     # Gemini's Analyse
│       ├── 02_copilot_output.md    # Copilot's Bewertung
│       ├── 03_claude_output.md     # Claude's Synthese
│       └── DIGEST.md               # Zusammenfassung
├── gates/              # Human decision points
└── issues/             # Final GitHub-ready issues

scripts/
├── orchestrator.py     # Pipeline-Logik
├── agents/
│   ├── gemini_agent.py
│   ├── copilot_agent.py
│   └── claude_agent.py
└── run_discussion.py   # CLI Entry Point

config/
└── pipeline_rules.yaml # Pipeline-Konfiguration
```

## 🎮 Verwendung

### Basis-Kommando

```bash
python scripts/run_discussion.py <proposal_file> [optionen]
```

### Optionen

```bash
# Komplexität setzen (beeinflusst Pipeline-Auswahl)
python scripts/run_discussion.py proposal.md --complexity high

# Custom Pipeline
python scripts/run_discussion.py proposal.md --pipeline gemini claude

# Mit Tags (für Pipeline-Selektion)
python scripts/run_discussion.py proposal.md --tags mathematical_modeling architecture
```

### Pipeline-Presets

| Preset | Agents | Wann verwenden? |
|--------|--------|-----------------|
| `quick` | Claude | Einfache Themen, Dokumentation |
| `standard` | Gemini → Claude | Mittlere Komplexität |
| `technical` | Copilot → Claude | Architektur-Entscheidungen |
| `deep` | Gemini → Copilot → Claude | Hohe Komplexität, Research |

## 🧠 Agent-Spezialisierungen

### Gemini (Research Analyst)
- **Rolle**: Faktenextraktion, Literatur-Synthese
- **Output**: Theoretische Frameworks, Evidence Base, Open Questions
- **Strength**: Umfassende Research-Perspektive

### Copilot (Technical Architect)
- **Rolle**: Implementation Feasibility, Code-Level Reasoning
- **Output**: Architektur-Implikationen, Performance-Analysen, **Kritik an Gemini**
- **Strength**: Praktische Umsetzbarkeit

### Claude (Meta-Synthesizer)
- **Rolle**: Konfliktauflösung, Strategic Framing
- **Output**: Agent Alignment Analysis, Blind Spot Detection, Gate Recommendation
- **Strength**: Ganzheitliche Bewertung

## 🔍 Qualitätsmetriken

Das System misst automatisch:

- **Disagreement Count**: Anzahl expliziter Widersprüche zwischen Agents
- **Echo Chamber Score**: 0.0 (gut) bis 1.0 (schlecht) – misst Diversität
- **Confidence Scores**: Per Agent und Claim

**Warnung**: Wenn `echo_chamber_score > 0.7` → Agents könnten sich nicht kritisch genug engagieren

## 🚦 Human Gates

Die Pipeline pausiert automatisch bei:

1. **Niedrigen Confidence Scores** (< 0.5)
2. **Vielen Disagreements** (> 2)
3. **Strategischen Keywords** ("breaking change", "migration required")
4. **Expliziten Flags** (`HUMAN_REVIEW_REQUIRED`)

Gate-Review-Datei wird erstellt in: `discussions/gates/GATE_<thread_id>.md`

## 🛠️ Konfiguration

Siehe `config/pipeline_rules.yaml` für:

- Pipeline-Presets
- Gate-Trigger
- Agent-Parameter
- Quality-Thresholds

## 📊 Beispiel: Agent-Diskurs

### Gemini's Claim
> "BSDE solvers scale linearly with dimension"

### Copilot's Response
```markdown
## 🔴 Disagreement with Gemini

**My Position:** Disagree. Empirical benchmarks show quadratic scaling above d=50.

**Evidence:**
- Benchmark: `benchmarks/bsde_scaling.json`
- Counter-example: Curse of dimensionality in deep BSDE methods

**Resolution Needed:**
@human: Run scaling test with d ∈ {10, 50, 100, 500}
```

### Claude's Synthesis
```markdown
## Conflict Resolution

**Adjudication:** Copilot is correct. Gemini's theoretical analysis overlooked
discretization overhead. However, Gemini's point holds for continuous-time limit.

**Confidence:** 0.75
```

## 🔬 Erweiterte Features

### Adaptive Pipeline
Wenn während der Diskussion Lücken entdeckt werden, kann die Pipeline dynamisch erweitert werden:

```python
# In orchestrator.py
def should_extend(self, thread_dir: Path) -> Optional[AgentType]:
    # Wenn viele offene Fragen → zusätzlicher Research-Pass
    if content.count("## Open Questions") > 5:
        return AgentType.GEMINI
```

### Asynchrone Human-Intervention
Pipeline läuft autonom, kann aber spezifische Fragen stellen:

```markdown
# HUMAN_INPUT_REQUEST.md
## Question
Do we have representative path-dependent problems where BSDE's
theoretical advantage justifies the computational cost?

## Your Answer
[Schreibe hier und speichere Datei → Pipeline setzt fort]
```

## 📝 Nächste Schritte

Nach Pipeline-Abschluss:

1. **Review**: `DIGEST.md` und finale Synthese
2. **Gate Decision**: PROCEED / REVISE / REJECT
3. **Issue Creation**: Wenn approved → GitHub Issue generieren

## 🤝 Beitragen

Weitere Agent-Implementierungen erwünscht:

- `DeepSeek` für Code-Review
- `Perplexity` für Fact-Checking
- Custom Domain-Expert Agents

## 📄 Lizenz

[MIT License]

## 🔗 Weiterführende Links

- Design Document (TBD)
- Agent Protocol Specification (TBD)
- Evaluation Metrics (TBD)

---

**Entwickelt für:** Claire de Binare Docs Knowledge Pipeline
**Status:** Prototype / MVP
**Letztes Update:** 2025-12-17
