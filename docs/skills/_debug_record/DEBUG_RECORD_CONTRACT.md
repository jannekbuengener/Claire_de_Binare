# CDB Debug-Record Contract (v1)

Status: kanonischer, docs-only Contract fuer die CDB Debug-Skill-Familie.
Scope: read-only Debugging-Artefakt. KEINE Datenbank, KEIN MCP-Write, KEIN Runtime-State.

Dieser Ordner (`docs/skills/_debug_record/`) ist bewusst ein Unterstrich-Ordner
(wie `docs/skills/_templates/`) und enthaelt **kein** `SKILL.md`. Der
Skill-Surface-Mirror-Guard (`tools/validate_skill_surface_mirror.py`) prueft nur
`docs/skills/*/SKILL.md`; dieser Contract erzeugt also keinen Mirror-Zwang.

## 1. Zweck

Der Debug-Record ist die gemeinsame, maschinen-lesbare Sprache der CDB
Debug-Skill-Familie. Er erlaubt jedem Debug-Skill, **einzeln** zu starten
(frischer Record) und - falls schon ein Vorbefund existiert - denselben Record
weiterzureichen, ohne dass ein Skill zwingend voraussetzt, dass ein anderer
vorher lief.

Der Record ist bewusst minimal. Er ist ein eingebetteter Markdown-/YAML-Block
in einem Session-Log, PR-Body, Issue-Kommentar oder Analyse-Report - **kein**
neues Speichersystem.

Prinzipien:

- **Standalone first:** jeder Skill fuellt nur die Felder, die er belegen kann.
- **In-Artefakt:** der Record lebt in Markdown/YAML, nicht in einer DB.
- **Fail-closed:** leere Felder bleiben leer; kein Raten.
- **Evidence over narrative:** Behauptungen brauchen Artefakt-Referenzen (§5).

## 2. Nicht-Ziele (harte Grenzen)

- Keine SurrealDB-Tabelle, kein Context-Brain-Write, kein MCP-Mutations-Pfad.
- Kein Runtime-/Docker-/Trading-State und keine Runtime-Mutation.
- Keine LR-/Live-/Echtgeld-Aussage; LR bleibt NO-GO.
- Kein Ersatz fuer bestehende Evidenz-Artefakte (`shadow_comparison.json`,
  Test-Metadaten, `cdb-session-close`-Handoff) - der Record **verweist** auf sie.

## 3. Kernfelder (minimal)

```yaml
symptom_or_signal:        # Pflicht: was wurde beobachtet (1-2 Saetze)
affected_area:            # Enum, siehe §4.1
affected_paths: []        # konkrete Dateien/Module (repo-relativ)
status_class:             # Enum, siehe §4.2 (trennt Stage/LR/Repo/Runtime/CI/Data-contract)
suspected_gap_or_bug:     # erste Vermutung, ausdruecklich noch nicht bewiesen
evidence: []              # Artefakt-Referenzen im INV-011-Format, siehe §5
test_gap:                 # fehlender Schutz-/Regressionstest (falls bekannt)
logic_or_design_finding:  # Logik-/Systemdesign-/Contract-Befund (falls vorhanden)
root_cause:               # nur wenn deterministisch belegt; sonst leer
fix_plan:                 # minimaler, reversibler Plan (KEIN Code hier)
residual_risk:            # was nach dem Fix-Plan offen/unsicher bleibt
followup_needed:          # Issue-Link/-Draft oder "none"
```

## 4. Feld-Semantik

### 4.1 `affected_area` (Enum)

`risk` | `execution` | `signal` | `regime` | `market` | `replay` |
`validation` | `ci` | `docs` | `context`

Mehrfachnennung erlaubt, wenn ein Symptom eine Grenze zwischen zwei Bereichen
betrifft (z. B. `signal` + `regime`).

### 4.2 `status_class` (Enum)

`Stage` | `LR` | `Repo/Engineering` | `Runtime` | `CI` | `Data-contract`

Erzwingt die CDB-Trennung: eine Board-Stage-Aussage ist **kein** LR-Verdikt,
ein CI-Rotstatus ist **kein** Runtime-Ausfall. Der Debug-Skill darf diese
Klassen nicht vermischen.

### 4.3 Optionale Erweiterungsfelder

Skills duerfen bei Bedarf ergaenzen (Contract-konform, nicht Pflicht):

```yaml
hypotheses: []            # von cdb-root-cause: gebildete/eliminierte Hypothesen
symptom_vs_cause:         # explizite Abgrenzung Symptom != Ursache
rule_ref:                 # INV-* / RC_* / Policy-Bezug
issue_ref:                # z. B. #1234
pr_ref:                   # z. B. #1250
```

## 5. Evidence-Format (INV-011)

Jeder Eintrag in `evidence[]` (und optional in `hypotheses[]`) MUSS eine
maschinen-lesbare Artefakt-Referenz nach `INV-011`
(`knowledge/governance/SYSTEM_INVARIANTS.md`) sein:

- `git:<sha>:<path>#L<start>-L<end>`
- `snapshot://<path>@<timestamp>`
- `sha256:<hash>`

Ergaenzend zulaessig (deterministisch reproduzierbar): `run_id:<id>`,
`config_hash:<hash>`, Pfad eines `report.json` / `shadow_comparison.json`.

Verboten: mehrdeutige Verweise wie "siehe Datei X" ohne Zeilen/Hash.

## 6. Alignment zu bestehenden Flaechen

| Fremdformat | Bezug | Rolle |
|---|---|---|
| Test-Metadaten (15 Felder) | `docs/skills/cdb-test-first/SKILL.md` §3 | `test_gap` referenziert `rule_ref`/`evidence_ref`-Vokabular |
| `shadow_comparison.json` | `core/replay/replay_vs_paper_compare.py` | Delta-Artefakt als `evidence`-Quelle |
| Determinismus-Repro | `core/replay/determinism.py` | Repro-Nachweis fuer `root_cause` |
| Session-Handoff | `docs/skills/cdb-session-close/SKILL.md` | Senke fuer `followup_needed` |

## 7. Beispiel (minimal, synthetisch)

```yaml
symptom_or_signal: "Replay-vs-Paper zeigt PnL-Delta > Toleranz auf BTCUSDT-Fenster"
affected_area: [replay, validation]
affected_paths:
  - core/replay/replay_vs_paper_compare.py
status_class: Data-contract
suspected_gap_or_bug: "Fee-Rundung divergiert zwischen Replay und Paper"
evidence:
  - "git:6a6ef980:core/replay/replay_vs_paper_compare.py#L40-L72"
  - "sha256:<comparison-artifact-hash>"
test_gap: "Metamorphic-Test fuer Fee-Verdopplung fehlt (cdb-test-first Typ 10)"
logic_or_design_finding: ""
root_cause: ""            # noch nicht deterministisch belegt -> INCONCLUSIVE
fix_plan: ""
residual_risk: ""
followup_needed: none
```

## 8. Verwendung durch die Skill-Familie

- **`cdb-root-cause`** (Slice 1): liest einen bestehenden Record oder startet
  einen frischen; fuellt `hypotheses`, `evidence`, `root_cause`,
  `symptom_vs_cause`, `fix_plan`, `residual_risk`.
- Weitere Debug-Skills (spaetere Slices, noch **nicht** gebaut) koennen denselben
  Record weiterreichen. Der Contract bleibt abwaertskompatibel: neue Felder
  werden additiv ergaenzt, bestehende nicht umbenannt.
