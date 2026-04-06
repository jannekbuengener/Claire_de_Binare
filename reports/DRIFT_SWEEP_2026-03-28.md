# Drift Sweep Report — 2026-03-28

**Scope:** Repo reality vs. docs/canon sweep (Issue #1298)
**Erstellt:** 2026-03-28
**Methode:** evidence-first, kein Runtime-Eingriff, kein Soak
**Prüfer:** Claude Code (Session Lead)
**Status:** REPORT-ONLY — keine Edits ohne Follow-up-Issue

---

## Executive Summary

Der Sweep hat **4 high-severity Findings** und **4 medium-severity Findings** identifiziert.
Der kritischste Cluster ist ein **vollständig veralteter Context Core** (SERVICE_CATALOG.md und ARCHITECTURE_MAP.md, Stand 2025-12-28), der die BLUE-Stack-Realität seit mindestens 3 Monaten nicht mehr abbildet: fehlender `cdb_candles`-Service, falsche Statuszuordnung für `cdb_allocation`, `cdb_regime` und `cdb_market`, und ein völlig veraltetes Compose-Architekturmodell.
Parallel existiert eine **aktive** Datei (`tools/secrets/README.md`) mit externen URLs auf das retired `Claire_de_Binare_Docs`-Repo — ein direkter Canon-Verstoß.
Das **LR-AUDIT-STATUS-Dokument** (kanonische SSOT) liegt 13 Tage hinter CURRENT_STATUS.md und zeigt stark abweichende Phasenstati.

Kein Finding bedroht den Betrieb sofort, aber mehrere hohe Findings korrumpieren die Bootstrapqualität neuer Sessions.

---

## Findings-Tabelle

| ID | Severity | Kategorie | Claim / Soll | Ist-Zustand | Evidenz (Datei + Abschnitt) | Impact | Empfohlene Maßnahme | Status |
|----|----------|-----------|--------------|-------------|------------------------------|--------|----------------------|--------|
| D-01 | **high** | Runtime-/Inventar-Drift | `knowledge/governance/SERVICE_CATALOG.md` ist kanonisches Service-Inventar | Erstellt 2025-12-28, nie aktualisiert. Zeigt `cdb_allocation`, `cdb_regime` als "BEREIT (deaktiviert)". `cdb_market` als "BEREIT, nicht implementiert". `cdb_candles` fehlt komplett. Compose-Architektur zeigt altes `base.yml + dev.yml`-Modell als primär. | `knowledge/governance/SERVICE_CATALOG.md` Z. 31-33, 88-124 vs. `infrastructure/compose/compose.blue.yml` Z. 97-198 | Jede Session, die SERVICE_CATALOG.md lädt, bekommt falsche Service-States und eine nicht mehr existente Compose-Topologie. | Neues Issue: vollständiges Update von SERVICE_CATALOG.md auf BLUE/RED-Realität | **hard contradiction** |
| D-02 | **high** | Runtime-/Inventar-Drift | `knowledge/ARCHITECTURE_MAP.md` ist kanonische Architektur-Referenz | Erstellt 2025-12-28, nie aktualisiert. `cdb_candles` fehlt vollständig. `cdb_allocation`/`cdb_regime`/`cdb_market` als "Deaktiviert" geführt. Compose-Architekturdiagramm zeigt altes `base.yml → dev.yml`-Modell. Core-Pipeline-Diagramm fehlt `candles → regime → allocation → risk`-Flow. `cdb_reports`, `cdb_postgres_exporter`, `cdb_redis_exporter`, `cdb_cadvisor` (alles RED) fehlen. Stack-Start-Befehl zeigt `stack_up.ps1 -Profile dev` statt kanonischem `.\tools\cdb.ps1`. | `knowledge/ARCHITECTURE_MAP.md` Z. 39-72, 88-89, 145-160 vs. `infrastructure/compose/compose.blue.yml` + `compose.red.yml` | Architektur-Map bildet weder den BLUE- noch den RED-Stack korrekt ab. Neue Agenten und Reviewer navigieren auf Basis falscher Topologie. | Neues Issue: Update ARCHITECTURE_MAP.md auf BLUE/RED-Realität (simultanes Update mit D-01) | **hard contradiction** |
| D-03 | **high** | Legacy-Leckage / Canon-Verstoß | Aktive Dokumentation soll intern auf Working Repo verweisen (WORKING_REPO_CANON.md-Policy) | `tools/secrets/README.md` Z. 152-162 enthält zwei externe GitHub-Links auf `https://github.com/jannekbuengener/Claire_de_Binare_Docs/blob/main/...` (SECRET_ROTATION_POLICY.md und GRAFANA_ADMIN_INCIDENT.md) — ein aktives, non-archive Dokument mit retired Docs-Hub-URLs | `tools/secrets/README.md` Z. 152-162; `docs/meta/WORKING_REPO_CANON.md` Policy-Abschnitt | Direkter Verstoß gegen Canon-Policy. Links führen auf externen Repo-Inhalt; nicht verifiziert, ob die Zieldateien noch existieren oder korrekt sind. | Links auf lokale Äquivalente umschreiben oder entfernen; `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md` existiert lokal (laut README-Referenz) | **hard contradiction** |
| D-04 | **high** | Status-Drift | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` ist kanonische SSOT für operativen Go/No-Go | Letzte Reconciliation: 2026-03-15 (13 Tage hinter aktuellem Stand). Phasenstatus-Divergenz zu CURRENT_STATUS.md (Stand 2026-03-27):<br>• P1: LR-AUDIT zeigt `OPEN`, CURRENT zeigt `PARTIAL`<br>• P2: LR-AUDIT zeigt `PARTIAL`, CURRENT zeigt `DONE`<br>• P3: LR-AUDIT zeigt `OPEN`, CURRENT zeigt `PARTIAL`<br>• P4: LR-AUDIT zeigt `OPEN`, CURRENT zeigt `PARTIAL` (LR-040 72h laufend) | `LR-AUDIT-STATUS-2026-03-05.md` Section B "Phase Status Table"; `CURRENT_STATUS.md` Abschnitt "Live-Readiness Phase Status" | Wer nur das kanonische SSOT-Dokument liest, sieht 13 Tage alten Stand. Keine falsche Aussage über NO-GO (bleibt konsistent), aber Phasengranularität stark abweichend. | LR-AUDIT-STATUS reconcilen auf aktuellen Stand (oder explizit als "Snapshot-Dokument" kennzeichnen und CURRENT_STATUS.md formell zur SSOT hochstufen) | **potential drift** |
| D-05 | **medium** | Status-Drift | `CURRENT_STATUS.md` "Latest Commit: 5a50700" korrekt | Git-Status der Session zeigt neuere Commits: e4130d3 (emoji blocking), b2ebb41 (snapshot cluster), 0faf0e8 (LR-040 NO-GO), c315d07, 56c5248 — allesamt nach 5a50700 | `CURRENT_STATUS.md` Z. 7; gitStatus-Kontext dieser Session | Geringfügiger Impact: Commit-SHA-Verweis ist für operative Entscheidungen nicht kritisch, aber zeigt, dass CURRENT_STATUS nach Session 11 nicht mehr aktualisiert wurde | Beim nächsten Session-Ende CURRENT_STATUS.md regulär aktualisieren (Normal-Housekeeping) | **potential drift** |
| D-06 | **medium** | Status-Drift | LR-040 72h-Run-Ergebnis in CURRENT_STATUS offen/laufend | CURRENT_STATUS Z. 93: "Geplantes Ende: 2026-03-28 12:12 UTC". Heutiges Datum: 2026-03-28. Untracked file `knowledge/logs/sessions/2026-03-28-issue-1224-lr040-no-go-formalized.md` und untracked `reports/p5_canary/2026-03-28/README.md` deuten darauf hin, dass das Gate-Ergebnis bereits formalisiert wurde. CURRENT_STATUS zeigt noch offenes Ergebnis. | `CURRENT_STATUS.md` Z. 35, 93; gitStatus untracked files | Gate-Entscheidung LR-040 möglicherweise abgeschlossen, aber weder in CURRENT_STATUS noch in LR-AUDIT-STATUS nachgetragen | Gate-Outcome nach Formalisierung in CURRENT_STATUS.md nachtragen; LR-AUDIT-STATUS reconcilen | **potential drift** |
| D-07 | **medium** | Context-/Bootstrap-Drift | CONTEXT_CORE_BUILD_FINAL_REPORT.md beschreibt "6 Context Core Files" die bei Session-Start geladen werden MÜSSEN | Report vom 2025-12-28 listet als Context Core: `knowledge/ARCHITECTURE_MAP.md`, `governance/SERVICE_CATALOG.md`, `knowledge/GOVERNANCE_QUICKREF.md`, `knowledge/SYSTEM_INVARIANTS.md`, `knowledge/OPERATIONS_RUNBOOK.md`, `knowledge/CURRENT_STATUS.md`. Aktueller CLAUDE.md-Read-Order umfasst andere Dateien. Pfad `governance/SERVICE_CATALOG.md` inkorrekt (korrekt: `knowledge/governance/SERVICE_CATALOG.md`). | `knowledge/context_build/CONTEXT_CORE_BUILD_FINAL_REPORT.md` Z. 60-66; `CLAUDE.md` (root) Abschnitt "Mandatory session-start read order" | CONTEXT_CORE_BUILD_FINAL_REPORT.md ist historisches Sprint-Artefakt und kein aktives Steuerungsdokument. Kein direkter operativer Schaden, da CLAUDE.md die aktuelle Read-Order vorgibt. | Als historisches Artefakt explizit kennzeichnen (Status: archived/historical, nicht canonical) | **historical tolerated legacy** |
| D-08 | **medium** | Pointer-/Redirect-Drift | `WORKING_REPO_CANON.md` Canon Matrix listet Root-Entrypoints: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md` | Root-level-Pointer-Dateien dieser Namen existieren möglicherweise nicht mehr oder sind nur Weiterleitungen. `agents/AGENTS.md` nennt `knowledge/governance/CDB_CONSTITUTION.md` + `knowledge/governance/CDB_GOVERNANCE.md` als kanonische Pfade. Ob Root-Dateien existieren: nicht verifiziert. | `docs/meta/WORKING_REPO_CANON.md` Z. 26; `agents/AGENTS.md` Z. 13-14 | Nicht verifiziert — möglicherweise inkonsistente Pointer-Deklaration | Existenz der Root-Dateien prüfen; wenn nur Pointer: im Canon als "root pointer" kennzeichnen | **nicht verifiziert** |

---

## Detailbefunde nach Prüfachse

### Achse 1 — Status-Drift

**README.md ↔ CURRENT_STATUS ↔ LR-AUDIT-STATUS:**
- README.md zeigt NO-GO konsistent mit CURRENT_STATUS und LR-AUDIT-STATUS → **keine Widersprüche am Schaufenster**
- Phasenstati divergieren zwischen LR-AUDIT-STATUS (SSOT, Reconciliation 2026-03-15) und CURRENT_STATUS (2026-03-27): P2 ist in CURRENT_STATUS "DONE", in LR-AUDIT-STATUS "PARTIAL" — das ist ein 13-Tage-Drift im kanonischen Dokument
- LR-040-Outcome: Fenster 2026-03-28 12:12 UTC nominell geschlossen. Untracked-Dateien deuten auf formalisiertes NO-GO hin, aber kein kanonisches Dokument zeigt den Outcome bisher

### Achse 2 — Canon-Drift

- `docs/meta/WORKING_REPO_CANON.md`, `agents/AGENTS.md`, `knowledge/SYSTEM.CONTEXT.md` und `knowledge/ACTIVE_ROADMAP.md`: alle konsistent — Docs-Hub ist retired, Working Repo ist Canon → **keine aktive Canon-Drift in den Steuerungsdokumenten**
- ABER: `tools/secrets/README.md` ist eine aktive non-archive Datei mit 2 expliziten Docs-Hub-URLs → direkter Canon-Verstoß in einem operativen Dokument
- `knowledge/governance/SERVICE_CATALOG.md` und `knowledge/ARCHITECTURE_MAP.md` zeigen de facto noch das alte Compose-Modell (base.yml+dev.yml) als primäre Architektur — also implizit noch den "alten" Stack-Status

### Achse 3 — Runtime-/Inventar-Drift

**compose.blue.yml (kanonisch, aktuell) vs. SERVICE_CATALOG.md (2025-12-28):**

| Service | SERVICE_CATALOG.md | compose.blue.yml (real) |
|---------|-------------------|------------------------|
| cdb_postgres | AKTIV ✓ | AKTIV ✓ |
| cdb_redis | AKTIV ✓ | AKTIV ✓ |
| cdb_market | BEREIT (deaktiviert, "nicht implementiert") | **AKTIV, Port 8009** |
| cdb_candles | **FEHLT KOMPLETT** | **AKTIV, Port 8007** |
| cdb_regime | BEREIT (deaktiviert) | **AKTIV, Port 8008** |
| cdb_allocation | BEREIT (deaktiviert) | **AKTIV, Port 8006** |
| cdb_risk | AKTIV ✓ | AKTIV, Port 8002 ✓ |
| cdb_execution | AKTIV ✓ | AKTIV, Port 8003 ✓ |
| cdb_db_writer | AKTIV ✓ | AKTIV ✓ |
| cdb_paper_runner | AKTIV ✓ | AKTIV, Port 8004 ✓ |

**compose.red.yml (aktuell) vs. SERVICE_CATALOG.md:**

| Service | SERVICE_CATALOG.md | compose.red.yml (real) |
|---------|-------------------|-----------------------|
| cdb_ws | AKTIV ✓ | AKTIV, Port 8000 ✓ |
| cdb_signal | AKTIV ✓ | AKTIV, Port 8005 ✓ |
| cdb_prometheus | AKTIV (Port: nicht spezifiziert) | AKTIV, Port 19090 |
| cdb_grafana | AKTIV ✓ | AKTIV, Port 3000 ✓ |
| cdb_loki | AKTIV (logging.yml) | **FEHLT in compose.red.yml** (nicht verifiziert ob eigenständig) |
| cdb_promtail | AKTIV (logging.yml) | **FEHLT in compose.red.yml** (nicht verifiziert ob eigenständig) |
| cdb_reports | **FEHLT KOMPLETT** | **AKTIV (keine Port-Bindung)** |
| cdb_postgres_exporter | **FEHLT** | **AKTIV, Port 9187** |
| cdb_redis_exporter | **FEHLT** | **AKTIV, Port 9121** |
| cdb_cadvisor | **FEHLT** | **AKTIV (kein Port)** |

### Achse 4 — Context-/Bootstrap-Drift

- `CLAUDE.md` (root) und `agents/roles/CLAUDE.md` haben identische Read-Order und sind intern konsistent
- `agents/AGENTS.md` Read-Order (governance docs + CDB_KNOWLEDGE_HUB.md) weicht von `CLAUDE.md`-Read-Order ab — kein harter Widerspruch, aber unterschiedliche Perspektiven
- CONTEXT_CORE_BUILD_FINAL_REPORT.md (Sprint-Artefakt 2025-12-28): historisches Dokument, das nicht mehr die aktive Read-Order oder den Autoload-Stand repräsentiert — kein aktiver Schaden, aber potenziell verwirrend für Neuleser

### Achse 5 — Pointer-/Redirect-Drift

- README.md Pointer auf alle kanonischen Quellen: intern und korrekt
- `docs/meta/WORKING_REPO_CANON.md` "Internal Redirect Map" zeigt Root-Files als Pointer auf `agents/AGENTS.md`, `knowledge/governance/...` etc. — plausibel, aber Existenz der Root-Pointer-Dateien nicht einzeln verifiziert
- `knowledge/ARCHITECTURE_MAP.md` Z. 18: `"Operatives Inventar: governance/SERVICE_CATALOG.md"` — fehlender `knowledge/`-Prefix (falscher Pfad)

### Achse 6 — Legacy-Leckagen

- **tools/secrets/README.md**: Einzige aktive non-archive Datei mit externen Docs-Hub-URLs → direkter Legacy-Leck in einem operativen Dokument
- **knowledge/governance/SERVICE_CATALOG.md** und **knowledge/ARCHITECTURE_MAP.md**: Beide zeigen das pre-BLUE/RED-Compose-Modell als primäre Architektur — de facto Legacy-Leck in kanonisch deklarierten Dokumenten
- `knowledge/context_build/CONTEXT_CORE_BUILD_FINAL_REPORT.md`: Sprint-Artefakt, kein kanonisches Dokument, aber nicht als historisch/archiviert markiert

---

## Clustering

### Sofort handlungsrelevante Widersprüche

| Finding | Begründung |
|---------|-----------|
| D-01 (SERVICE_CATALOG.md) | Kanonisch, wird bei Session-Start geladen, zeigt komplett falsche Service-Zustände und fehlenden cdb_candles |
| D-02 (ARCHITECTURE_MAP.md) | Kanonisch, wird bei Session-Start geladen, falsche Topologie, falsche Service-States, fehlendes Candles/Reports |
| D-03 (tools/secrets/README.md externe URLs) | Aktive Datei, direkter Canon-Verstoß, Links auf möglicherweise nicht mehr aktuelle externe Quelle |
| D-04 (LR-AUDIT-STATUS 13d hinter Stand) | Kanonische SSOT hat 13-Tage-Drift zu CURRENT_STATUS — P1/P2/P3-Status erheblich abweichend |

### Mittelfristige Drift

| Finding | Begründung |
|---------|-----------|
| D-05 (CURRENT_STATUS commit stale) | Housekeeping-Item, kein operativer Impact |
| D-06 (LR-040 Outcome offen) | Gate-Ergebnis nominell geschlossen, aber nicht in kanonischen Dokumenten sichtbar |
| D-08 (Root-Pointer Existenz) | Nicht verifiziert, möglicherweise tolerable Inkonsistenz |

### Tolerierbare historische Altlasten

| Finding | Begründung |
|---------|-----------|
| D-07 (CONTEXT_CORE_BUILD_FINAL_REPORT.md) | Sprint-Artefakt aus 2025-12-28, kein aktives Steuerungsdokument, keine operative Wirkung |

---

## Restunsicherheiten

1. **cdb_loki / cdb_promtail**: SERVICE_CATALOG.md zeigt sie als aktiv (logging.yml). In compose.red.yml nicht gefunden. Existenz eines separaten `logging.yml` im aktuellen Stand nicht verifiziert — ob diese Services noch existieren oder entfernt wurden, ist unklar.
2. **Root-Pointer-Dateien** (`AGENTS.md`, `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md` im Root): Existenz nicht einzeln verifiziert.
3. **LR-040 exakter Gate-Status**: Untracked-Datei `2026-03-28-issue-1224-lr040-no-go-formalized.md` suggeriert NO-GO-Formalisierung, wurde aber nicht gelesen — Inhalt und offizieller Status unbekannt.
4. **ARCHITECTURE_MAP.md "Known Drifts" (Sektion 6)**: Listet prod.yml/tls.yml Naming-Drift aus 2025-12. Ob diese Dateien noch existieren und ob der Drift behoben wurde, nicht verifiziert.
5. **Grafana-Passwort-Secret-Name**: `compose.red.yml` verwendet `grafana_password`, CLUSTER-History zeigt `GRAFANA_ADMIN_PASSWORD` — Divergenz im Secret-Naming nicht vollständig verfolgt.

---

## Quellenverzeichnis geprüfter Dateien

| Datei | Prüfstatus |
|-------|-----------|
| `README.md` | geprüft |
| `CURRENT_STATUS.md` | geprüft |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | geprüft |
| `docs/meta/WORKING_REPO_CANON.md` | geprüft |
| `knowledge/SYSTEM.CONTEXT.md` | geprüft |
| `knowledge/ACTIVE_ROADMAP.md` | geprüft |
| `knowledge/context_build/CONTEXT_CORE_BUILD_FINAL_REPORT.md` | geprüft |
| `knowledge/governance/SERVICE_CATALOG.md` | geprüft |
| `knowledge/ARCHITECTURE_MAP.md` | geprüft |
| `tools/secrets/README.md` | geprüft |
| `agents/AGENTS.md` | geprüft |
| `agents/roles/CLAUDE.md` | geprüft |
| `infrastructure/compose/compose.blue.yml` | geprüft |
| `infrastructure/compose/compose.red.yml` | geprüft |
| `CLAUDE.md` (root) | geprüft (via system-reminder) |
| `knowledge/context_build/` (alle Dateien) | Glob-geprüft, Report selektiv gelesen |
| Claire_de_Binare_Docs-Referenzen in non-archive Dateien | Grep-geprüft (88 Treffer, davon alle signifikanten in archive oder historisch — außer tools/secrets/README.md) |
