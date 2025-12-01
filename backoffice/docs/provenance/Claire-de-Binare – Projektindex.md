# Claire-de-Binare – Projektindex

Willkommen im Projekt **Claire-de-Binare**.
Dieses Dokument ist der zentrale Einstiegspunkt: Es sagt dir, wo der aktuelle Stand ist, welche Dateien wichtig sind und wo du als Nächstes weitermachst.

---

## 1. Aktueller Projektstatus

* System: **vollständig kanonisiert**
* Pipelines: **4/4 abgeschlossen** (inkl. Pre-Migration & Migration-Prep)
* CRITICAL-Risiken: **4/4 behoben** (SR-001, SR-002, SR-003, cdb_signal_gen)
* Artefakte: **31** strukturierte Dokus / Templates / Skripte
* Security: **70% → 95%**
* Completeness: **85% → 100%**
* Consistency: **90% → 100%**
* Risiko-Level: **MEDIUM → LOW**
* Status: **✅ READY FOR Claire de Binare MIGRATION**
* Zeit bis „erste produktionsnahe Tests“: **1–2 Stunden**

Details zum Status:
→ `sandbox/MIGRATION_READY.md`
→ `sandbox/PIPELINE_COMPLETE_SUMMARY.md`
→ `sandbox/PRE_MIGRATION_EXECUTION_REPORT.md`

---

## 2. Repositories & Rollen

* **SOURCE_REPO (Arbeitskopie):**
  `claire_de_binare - Kopie`
  → Hier liegen alle Analyse-, Pipeline- und Kanon-Artefakte im Ordner `sandbox/`.

* **TARGET_REPO (Claire de Binare):**
  `Claire_de_Binare_Claire de Binare`
  → Wird nach der Migration die zentrale, aufgeräumte Quelle für Architektur, Doku und Templates.

Grundregel:

* Änderungen, Experimente, Rekonstruktionen → im **SOURCE_REPO/sandbox/**
* Saubere, stabile Referenz für das System → im **Claire de Binare-Repo**, nach der Migration.

---

## 3. Wichtige Dateien im SOURCEREPO (sandbox/)

Kanon & Architektur:

* `canonical_schema.yaml`
  → Maschinenlesbares Systemmodell (Services, ENV, Risk-Parameter, Events, Infra, Security).

* `facts_canonical.md`
  → Menschlich lesbarer Kanon: ein Datensatz pro Entity, inkl. Quellen & Normalisierungen.

* `canonical_system_map.md`
  → Big-Picture der Systemarchitektur, Datenflüsse, Risk-Engine, Event-Pipeline.

Readiness & Zusammenfassungen:

* `PIPELINE_COMPLETE_SUMMARY.md`
  → Überblick über alle Pipelines, Artefakte, Metriken.

* `canonical_readiness_report.md`
  → Readiness-Analyse (Security, Completeness, Deployability, Risiko-Level).

* `PRE_MIGRATION_EXECUTION_REPORT.md`
  → Was in der Pre-Migration automatisiert erledigt wurde (SR-001–SR-003, Legacy-Service).

* `MIGRATION_READY.md`
  → Operativer Startpunkt für die Migration (Schnellstart, Optionen, Status).

Templates & Infra:

* `project_template.md`
  → Template-Struktur für neue Projekte / Repos (Architektur, Config, Risk-Patterns, Workflows).

* `infra_templates.md`
  → Docker-/Compose- und Infra-Blueprints.

* `env_index.md`
  → Liste aller ENV-Variablen (Name, Kategorie, Bedeutung, Scope – keine Werte).

---

## 4. Was du als Nächstes tun kannst

### A) Migration ins Claire de Binare-Repo starten

Wenn du die Claire de Binare-Migration durchführen willst:

1. `sandbox/MIGRATION_READY.md` lesen
2. Den dort beschriebenen **Schnellstart** nutzen

   * Automatisiert: Migration-Script (ca. 15 Minuten)
   * Manuell: Migration-Plan (2–3 Stunden)

Ziel:
→ Kanon, Doku und Templates sauber ins **Claire de Binare-Repo `Claire_de_Binare_Claire de Binare`** überführen.

### B) System lokal testen / in Staging bringen

Nach der Migration (oder schon testweise aus der Arbeitskopie):

1. `.env.template` → `.env` kopieren (lokal, nicht committen)
2. `<SET_IN_ENV>`-Platzhalter durch echte Werte ersetzen
3. `docker compose up -d` starten
4. Health-Checks & Smoke-Test:

   * `market_data → signals → orders → order_results`

---

## 5. Orientierung für neue Sessions / KIs

Wenn eine neue KI-Session oder ein neues Tool mit Claire-de-Binare arbeiten soll, ist die Reihenfolge:

1. Dieses Dokument: `INDEX.md`
2. Status & Kontext: `sandbox/MIGRATION_READY.md`
3. Kanon verstehen:

   * `sandbox/canonical_schema.yaml`
   * `sandbox/facts_canonical.md`
   * `sandbox/canonical_system_map.md`
4. Operative Aufgaben:

   * Migration → `MIGRATION_READY.md`
   * Templates / neue Projekte → `project_template.md`, `infra_templates.md`

---

## 6. Kurz-Zusammenfassung

* Claire-de-Binare ist **fachlich und technisch vollständig modelliert**.
* Alle CRITICAL-Risiken sind behoben, die Pre-Migration ist durch.
* Der nächste logische Schritt ist die **Migration ins Claire de Binare-Repo**.
* Danach: Tests, Hardening-Finetuning, produktionsnahe Deployments.

Startpunkt für die Arbeit:
→ `sandbox/MIGRATION_READY.md`
Startpunkt für das Verstehen:
→ `sandbox/canonical_system_map.md` + `sandbox/facts_canonical.md`
