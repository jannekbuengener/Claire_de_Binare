# NEXUS.MEMORY.md
**CDB – Canonical Memory Interface**  
Version: 1.0 • Date: 2025-12-12 • Status: Governance-bound

---

## 0. Geltungsbereich & Rangordnung

Diese Datei ist Teil des **Governance-Layers** von Claire de Binare (CDB).  
Sie unterliegt vollständig:

1. `CDB_CONSTITUTION.md`
2. `CDB_GOVERNANCE.md`
3. `CDB_AGENT_POLICY.md`

Im Konfliktfall gilt stets die höhere Instanz.

---

## 1. Zweck (Why this exists)

`NEXUS.MEMORY.md` definiert die **kanonische Schnittstelle für Systemgedächtnis**.

Sie ist:
- **kein Wissensspeicher**
- **keine Dokumentation**
- **keine Datenbank**

Sondern:

> Ein **Governance-kontrollierter Übergabepunkt** zwischen
> validierten Erkenntnissen und persistentem Langzeitgedächtnis (z. B. Vector-DB).

---

## 2. Aktiver Funktionsumfang (Minimal, Tier‐1)

Im aktuellen Tier‐1‐Setup erfüllt NEXUS ausschließlich folgende Funktionen:

- Definition **was Memory ist**
- Definition **wer Memory schreiben darf**
- Definition **wann Memory geschrieben werden darf**
- Sicherstellung von:
  - Transparenz
  - Auditierbarkeit
  - No‐Blackbox‐Konformität

**Es findet noch kein automatischer Memory‐Merge statt.**

---

## 3. Abgrenzung (Non‐Goals)

NEXUS ist **nicht**:

- ein Logbuch
- ein Entscheidungsprotokoll (→ Knowledge Hub)
- ein Workflow‐Artefakt
- ein Ersatz für externe Knowledge Bases
- ein autonomes Lernsystem

Alles, was diese Kriterien verletzt, ist **Governance‐widrig**.

---

## 4. Memory‐Definition (kanonisch)

Als *Memory* gelten ausschließlich:

- systemweit bestätigte Annahmen
- stabile Architektur‐Entscheidungen
- sicherheitsrelevante Invarianten
- bewährte, mehrfach validierte Erkenntnisse

Nicht als Memory gelten:

- Roh‐Analysen
- Meinungen einzelner Modelle
- temporäre Entscheidungen
- Entwurfsstände

---

## 5. Schreib‐ & Leserechte (hart)

### 5.1 Lesen
- Alle Modelle & Agenten dürfen lesen.

### 5.2 Schreiben
Memory‐Writes sind **streng limitiert**:

- ⛔ niemals im Analysis Mode
- ⛔ niemals autonom
- ⛔ niemals implizit
- ✅ nur im **Delivery Mode**
- ✅ nur nach **expliziter User‐Freigabe**
- ✅ nur über den **Session Lead**

Direkte KI‐Writes sind verboten.

---

## 6. Governance‐Pflichten bei Memory‐Writes

Jeder zukünftige Memory‐Write MUSS:

1. eine Quelle haben (Decision / Review)
2. begründet sein (Warum persistent?)
3. versioniert sein
4. rückverfolgbar sein
5. widerrufbar sein

Kein Eintrag ohne Audit‐Trail.

---

## 7. Beziehung zu Agentenrollen

Die Rolle **knowledge‐architect** ist konzeptionell zuständig für:

- Strukturierung von Wissen
- Bewertung von Memory‐Kandidaten
- Vorbereitung von Memory‐Writes

Aber:
- ohne Sonderrechte
- ohne autonome Befugnisse
- immer unter Governance & User‐Kontrolle

---

## 8. Perspektive Tier‐2 (nicht aktiv)

Erst in Tier‐2 kann NEXUS erweitert werden um:

- Memory‐Merge‐Workflow
- Vector‐DB‐Anbindung
- dedizierten Memory‐Manager

Auch dann gilt:
**Kein Schreiben ohne User‐Freigabe.**

---

## 9. Zentrales Sicherheitsprinzip

> Memory darf das System **stabiler machen**,
> aber **niemals autonomer als erlaubt**.

Wenn nicht eindeutig klar ist,
ob etwas Memory werden darf → **es wird kein Memory**.

---

## 10. Abschlussformel

`NEXUS.MEMORY.md` ist bewusst klein gehalten.

> Wenn etwas erklärungsbedürftig ist,
> gehört es **nicht** hier hinein.

---

## 11. Erlangtes Wissen & Arbeitsnotizen

Dieser Abschnitt dient als Sammlung von praktischem Wissen, To-dos und Aufgaben für die Zusammenarbeit von Agenten, gemäß der Anweisung des Users vom 2025-12-13.

### 11.1 Migrationsregeln
- Beim Migrieren von Dockerfiles aus `t1/`: Existiert ein service-spezifisches Dockerfile (z.B. `t1/service/Dockerfile`) neben einem allgemeineren (`t1/service.Dockerfile`), sollte das allgemeinere verworfen werden.

### 11.2 Post-Migration Erkenntnisse (t1/ → Ziel-Struktur, 2025-12-13)

**Strukturelle Validierung:**
- ✅ Services korrekt migriert: market, signal, risk, execution, db_writer
- ✅ Infrastructure-Struktur korrekt: database/, monitoring/, scripts/
- ⚠️ `/core/` ist leer - Services importieren aber nicht-existentes `common.models`

**Kritische Pfad-Brüche identifiziert:**
1. `docker-compose.yml:38` - Schema-Pfad zeigt auf `./backoffice/docs/DATABASE_SCHEMA.sql` (nicht migriert), korrekt: `./infrastructure/database/schema.sql`
2. Service-Imports fehlerhaft: `from ..common.models import Signal` → sollte `from core.domain.models import Signal` (wenn `/core/domain/` befüllt)

**Architektur-Entscheidung erforderlich:**
- Shared Models (Signal, Order, etc.) müssen nach `/core/domain/` migriert werden
- Alle Services müssen Import-Pfade anpassen
- Alternative: Temporär `common/` als Symlink zu `/core/domain/` (Quick-Fix, nicht dauerhaft)

### 11.3 Tier-Migration Finale (t1/, t2/, t3/ → Zielstruktur, 2025-12-13)

**t1/ Migration (Essential Core):**
- Services → `services/market/`, `services/signal/`, `services/risk/`, `services/execution/`, `services/db_writer/`
- Infrastructure → `infrastructure/database/`, `infrastructure/monitoring/`
- Docker Config → Root (`docker-compose.yml`, `.dockerignore`, `Dockerfile`)
- Tests → `tests/`

**t2/ Migration (Tools & Scripts):**
- GitHub Templates → `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`
- Automation Scripts → `infrastructure/scripts/` (8 files: backup_postgres.ps1, daily_check.py, query_analytics.py, setup_backup_task.ps1, check_env.ps1, security_audit.sh)
- Migration Historie → `infrastructure/scripts/archive/migration_2025_11_16/` (3 files: cleanroom_migration_script.ps1, pre_migration_tasks.ps1, pre_migration_validation.ps1)
- Execution Simulator → `services/execution/simulator.py`

**t3/ Migration (Research & Legacy):**
- Portfolio Manager (Legacy) → `tools/research/portfolio_manager.py`
- Utility Scripts → `tools/link_check.py`, `tools/provenance_hash.py`
- Paper Trading Test → `tools/paper_trading/` (email_alerter.py, service.py)

**Status:** ✅ Alle Tier-Verzeichnisse migriert und entfernt (2025-12-13 02:10 UTC+1)