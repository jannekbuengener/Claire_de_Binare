# Claire de Binare Repository Canon

Status: Canonical
Issue: #1140

## Decision

Das Repository `Claire_de_Binare` ist die einzige kanonische Quelle fuer Code,
Infrastruktur, Agenten-, Governance-, Knowledge-, Template- und
Navigationsdokumentation. Es gibt kein zweites produktives Repository und keine
zweite Dokumentationsquelle.

## Canon Matrix

| Domain | Canonical Path |
| --- | --- |
| Agent registry | `agents/AGENTS.md` |
| Cursor subagents (helper roles) | `.cursor/agents/` + `_CDB_SUBAGENT_CONTRACT.md` |
| Governance / policy | `knowledge/governance/` |
| GitHub-consumed governance gates | `.github/governance/` |
| Repository / campaign / readiness config | `config/` |
| Knowledge hub | `knowledge/` |
| GitHub templates / community docs | `.github/` |
| Navigation pack | `docs/navigation/mcp-navpack/` |
| Navigation / runbooks / archive | `docs/` |
| Reviewed, versioned evidence | `docs/evidence/` |
| Generated reports and run output | `artifacts/` |
| Runtime / deployment infrastructure | `infrastructure/` |
| Root entrypoints | `README.md`, `AGENTS.md`, `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CURRENT_STATUS.md`, `PROJECT_STATUS.md` |

The approved root layout and the 2026-07-15 cleanup decisions are defined in
[`ROOT_INFORMATION_ARCHITECTURE.md`](ROOT_INFORMATION_ARCHITECTURE.md). The
machine-readable allowlist is `config/repository/root_layout.json`.

## Status SSOT Rule

Status im Repository ist absichtlich rollenspezifisch und nicht in einer
einzigen generischen "Current Status"-Datei gebuendelt.

| Status class | Canonical source | Rule |
| --- | --- | --- |
| Operational / live-readiness status | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Autoritative Quelle fuer aktuellen Go/No-Go-Status und operative Live-Readiness-Blocker |
| Repository / engineering status | `CURRENT_STATUS.md` | Autoritative Quelle fuer aktuellen Repo-, Main-, Test- und aktiven Arbeitsstatus |
| Board / stage status | `docs/runbooks/CONTROL_REGISTER.md` plus GitHub Control Board Stage-/Milestone-Zustand | Autoritative Quelle fuer aktuellen Stage-/Operating-Focus; das Stage-System ist orthogonal zum LR-System |
| Historical implementation / audit snapshots | `PROJECT_STATUS.md`, `knowledge/CURRENT_STATUS.md` | Nur punktuelle historische Snapshots; keine aktuelle operative oder repo-weite Wahrheit |
| Evidence / milestone / governance reports | z. B. `docs/archive/governance-audit-2026-01-15.md`, `CODEX_RUN_REPORT.md`, `docs/governance/status/` | Nachweis-, Audit- oder Milestone-Artefakte; nicht-kanonisch fuer aktuellen Gesamtstatus |

## Status Usage Rules

- `README.md` bleibt Front Door und darf Status nur zusammenfassen oder auf die
  jeweilige kanonische Quelle verweisen.
- Board-/Stage-Claims und LR-Go/No-Go-Claims muessen explizit getrennt bleiben.
- Eine Stage-Transition darf weder Live-Kapital-Freigabe noch Strategie-Validierung implizieren, solange die jeweilige kanonische Quelle das nicht ausdruecklich sagt.
- Statusdateien mit historischem oder sekundaerem Charakter muessen ihren
  Status-Typ explizit kennzeichnen.
- Neue Reports, Pass-Reports oder Audit-Snapshots duerfen scope-lokale Findings
  dokumentieren, aber nicht als aktuelle repo-weite Wahrheit auftreten.

## Operational Runbook Canon Rule

- Aktive Operating Rules und operator-nahe Runbooks gehoeren unter `knowledge/operating_rules/`.
- Der kanonische Pfad fuer das Live-Trading-Runbook ist `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md`.
- `knowledge/LIVE_TRADING_RUNBOOK.md` darf nur noch als lokaler Pointer fuer Discoverability bestehen und keine zweite vollwertige Runbook-Fassung mehr tragen.
- `docs/live-readiness/` bleibt die kanonische Quelle fuer aktuellen Go/No-Go-Status und Evidence, nicht fuer den operativen Runbook-Body.

## Internal Redirect Map

| Legacy entrypoint | Local target |
| --- | --- |
| `AGENTS.md` | `agents/AGENTS.md` |
| `CDB_CONSTITUTION.md` | `knowledge/governance/CDB_CONSTITUTION.md` |
| `CDB_GOVERNANCE.md` | `knowledge/governance/CDB_GOVERNANCE.md` |
| `LEGACY_FILES.md` | `docs/archive/LEGACY_FILES.md` |

## Repo Rules

- Navigation, guards and scripts must prefer local repo paths.
- New tracked root entries require an explicit information-architecture decision
  and an update to `config/repository/root_layout.json`.
- Generators write to `artifacts/`; reviewed evidence is promoted explicitly to
  `docs/evidence/` instead of being generated directly into documentation.
- Executable infrastructure remains under `infrastructure/`, not `docs/` or
  `knowledge/`.
- Alle kanonischen Verweise muessen innerhalb von `Claire_de_Binare` aufloesbar sein.
- Pointer files may exist at root for discoverability, but they must resolve internally.
- Status-bearing docs must declare whether they are `operational`, `repository`, `historical snapshot`, or `scoped evidence` whenever ambiguity is plausible.
- No secondary file may override or restate the current repo-wide operational verdict independently of the canonical live-readiness source.

## README vs. `index.md` Navigation Rule

| Surface | Rolle | Beispiel |
| --- | --- | --- |
| `README.md` in einem Ordner | Lokaler Index + SSOT-Grenzen für diesen Tree | [`docs/runbooks/README.md`](../runbooks/README.md), [`services/risk/README.md`](../../services/risk/README.md) |
| `index.md` | Kurz-Pointer-Seite über mehrere Untertrees | [`docs/index.md`](../index.md), [`docs/ci/index.md`](../ci/index.md), [`docs/db/index.md`](../db/index.md) |

Regeln:

- `docs/index.md` bleibt die kürzeste repo-weite Docs-Landingpage; sie verlinkt auf README-Indizes, ersetzt sie nicht.
- Ordner mit vielen Dateien bekommen ein `README.md` (Tabelle + Abgrenzung); `index.md` nur wo bereits etabliert oder für flache Nav-Hubs.
- Status-SSOT bleibt in den kanonischen Statusdateien (siehe Status SSOT Rule); READMEs fassen zusammen oder verweisen, erfinden keinen operativen Verdict.
- Archiv unter `docs/archive/` ist read-only und niemals eine zweite kanonische Quelle.

## Archive

Historische Einzelartefakte duerfen unter `docs/archive/` liegen. Sie sind keine
alternative Repository- oder Dokumentationsquelle und werden nicht standardmaessig
in den Context-Index aufgenommen.
