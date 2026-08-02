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

## Status Freshness Rule

Status-Flaechen mischen zwei Sorten von Aussagen: **Live-Claims**, die nur
solange stimmen wie die Realitaet sie stuetzt, und **append-only Historie**,
die den Stand eines vergangenen Zeitpunkts festhaelt und bewusst nicht
nachgezogen wird. Beides muss maschinell unterscheidbar sein.

Der Guard `python -m tools.validate_status_freshness` prueft die Live-Claims
von `README.md`, `CURRENT_STATUS.md` und `docs/runbooks/CONTROL_REGISTER.md`
semantisch. Er vergleicht bewusst **kein** Alter und kein Aenderungsdatum: ein
altes Dokument besteht, solange jeder Live-Claim weiterhin zutrifft, und ein
heute editiertes Dokument faellt durch, sobald es einen ueberholten Zustand
behauptet.

### Markerkonvention

| Marker | Bedeutung |
| --- | --- |
| `<!-- cdb:status-freshness header-date=YYYY-MM-DD -->` | Header-Datum des Dokuments; muss im sichtbaren Text neben dem Marker stehen und darf nicht aelter sein als das juengste im Body verwendete Datum |
| `<!-- cdb:live-claim type=main_sha value=<sha> -->` | Das Dokument behauptet einen bestaetigten `origin/main`-Stand |
| `<!-- cdb:live-claim type=issue_state issue=<n> state=open\|closed\|merged -->` | Das Dokument behauptet einen aktuellen Issue-/PR-Zustand |
| `<!-- cdb:historical-as-of date=YYYY-MM-DD -->` … `<!-- cdb:historical-end -->` | Absichtlicher historischer Snapshot; von Live-Pruefungen ausgenommen |

### Ergebnisklassen

- `PASS` — Claim ist gegen Git bzw. GitHub belegt.
- `FAIL` — Claim widerspricht dem belegten Zustand, oder die Markierung ist
  strukturell defekt.
- `UNVERIFIED` — Git- oder GitHub-Zugriff fehlt. Ein GitHub-abhaengiger Claim
  gilt bei API-Ausfall nie als `PASS`; `--strict` macht `UNVERIFIED` zum Fehler.

### Semantik der Claim-Typen

- `main_sha`: Der genannte Commit muss von `origin/main` aus erreichbar sein und
  alle Flaechen muessen denselben Stand nennen. Ein fortschreitendes `main`
  entwertet einen korrekten Snapshot damit nicht, ein erfundener oder
  divergierender Snapshot dagegen schon.
- `issue_state`: Der deklarierte Zustand wird gegen GitHub live geprueft.
- `header_date`: Reine Konsistenzpruefung innerhalb des Dokuments.

### Regeln fuer Autoren

- Ein absichtlicher historischer Snapshot wird durch ein
  `historical-as-of`/`historical-end`-Paar markiert; sein Datum darf nicht
  neuer sein als das Header-Datum.
- In einem historischen Block darf kein `live-claim` stehen.
- Live-Claims in Prosa (`origin/main` mit Commit, `in delivery` mit
  Issue-Referenz) brauchen einen passenden Marker, sonst schlaegt der Guard
  fehl. Damit kann Drift nicht unbemerkt neu entstehen.
- Historische Ledger-Eintraege werden nicht umgeschrieben. Ein Reconcile-Ergebnis
  gehoert in den aktuellen Block, nicht in den historischen.

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
| `index.md` | Kurz-Pointer-Seite über mehrere Untertrees | [`docs/index.md`](../index.md), [`docs/ci/index.md`](../ci/index.md), [`docs/db/index.md`](../db/index.md), [`docs/env/index.md`](../env/index.md), [`docs/external-docs/index.md`](../external-docs/index.md) |

Regeln:

- `docs/index.md` bleibt die kürzeste repo-weite Docs-Landingpage; sie verlinkt auf README-Indizes, ersetzt sie nicht.
- Ordner mit vielen Dateien bekommen ein `README.md` (Tabelle + Abgrenzung); `index.md` nur wo bereits etabliert oder für flache Nav-Hubs.
- Status-SSOT bleibt in den kanonischen Statusdateien (siehe Status SSOT Rule); READMEs fassen zusammen oder verweisen, erfinden keinen operativen Verdict.
- Archiv unter `docs/archive/` ist read-only und niemals eine zweite kanonische Quelle.

## Area Entry Link Rule

Ein Link, der einen Repository-Bereich als Einstieg meint, verweist auf die
lokale `README.md` dieses Bereichs und nicht auf den nackten Ordner.

Entscheidungsfrage:

```text
Soll der Leser einen Bereich verstehen oder eine konkrete Datei öffnen?
```

- Bereich verstehen → lokale `README.md` (Bereichs- oder Unterbereichs-Index).
- Konkrete Datei öffnen → direkter Dateilink.

### Bereichseinstieg

- Linkziel für einen Bereichseinstieg ist `…/<area>/README.md`.
- Der sichtbare Linktext darf weiterhin den Ordnerpfad zeigen. Beispiel
  (Ziel relativ zur jeweiligen Quelldatei auflösen):

```markdown
[`services/risk/`](services/risk/README.md)
```

- Redundante Dual-Link-Darstellungen mit getrenntem Ordnerlink **und**
  README-Link sind unzulässig. Wenn eine Tabelle den Ordnernamen und die
  README fachlich braucht, bleibt der Ordnerpfad unlinked Text; das einzige
  Bereichs-Linkziel ist die README.
- Eine README muss nicht jede Datei eines Trees auflisten. Sie vermittelt
  Zweck, Zuständigkeit/SSOT-Grenzen und die relevanten nächsten Einstiege.

### Direkte Dateilinks (erlaubt)

Direkte Dateilinks bleiben, wenn genau diese Datei das beabsichtigte Ziel ist,
insbesondere:

- Canon-Dateien und Policies
- Status-SSOTs und Live-Readiness-Verdikte
- Contracts und operative Runbooks
- konkrete Tools, Tests oder ausführbare Konfiguration
- maschinenlesbare Entrypoints (YAML/JSON und ähnliche Steuerdateien)

### Etablierte `index.md`-Ausnahmen

Nur die folgenden, live vorhandenen flachen oder bereichsübergreifenden Hubs
dürfen als Bereichseinstieg statt einer lokalen README dienen:

| Hub | Rolle |
| --- | --- |
| [`docs/index.md`](../index.md) | kürzeste repo-weite Docs-Landingpage |
| [`docs/ci/index.md`](../ci/index.md) | CI-/PR-Gate-Navigationshub |
| [`docs/db/index.md`](../db/index.md) | DB-/Schema-Navigationshub |
| [`docs/env/index.md`](../env/index.md) | Env-/Secrets-/Toggle-Hub |
| [`docs/external-docs/index.md`](../external-docs/index.md) | externe Docs-Verweis-Hub |

Neue `index.md`-Ausnahmen erfordern eine explizite Canon-Erweiterung. Sie
werden nicht still angenommen.

### Fehlende README

Fehlt für einen aktiven, navigationsrelevanten Bereich eine lokale `README.md`,
ist das eine Informationsarchitektur-Lücke. Ein nackter Ordnerlink ist kein
zulässiger dauerhafter Ersatz.

### Bevorzugte Navigationstiefe

```text
Repository-Front-Door
→ Bereichs-README
→ Unterbereichs-README
→ konkrete kanonische Datei
```

### Ausgeschlossene Flächen

Nicht als aktive Standardnavigation behandeln:

- `docs/archive/**`
- `knowledge/archive/**`
- `artifacts/**` und sonstige generierte Outputs
- vendorte oder externe Trees
- Test-Fixtures und Beispielbäume, sofern sie nicht ausdrücklich aktive
  Einstiegspunkte sind

Ein bewusster direkter Link dorthin bleibt möglich, wenn er fachlich begründet
ist.

### Enforcement-Hinweis

Diese Regel ist der Navigationsvertrag. Der bestehende README-Link-Guard
(`python -m tools.validate_readme_links`) prüft Link-Existenz, noch nicht die
Area-Entry-Präferenz. Automatischer Enforcement-Guard folgt in einem späteren
Slice (S7).

## Archive

Historische Einzelartefakte duerfen unter `docs/archive/` liegen. Sie sind keine
alternative Repository- oder Dokumentationsquelle und werden nicht standardmaessig
in den Context-Index aufgenommen.
