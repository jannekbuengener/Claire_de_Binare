# Issues & Blocker Backlog - Claire de Binaire

**Erstellt**: 2025-11-21
**Quelle**: PROJECT_STATUS.md + Code-Audit
**Status**: Active Backlog

---

## 🔴 KRITISCH - Deployment-Blocker

### Issue #1: ENV-Validation ausstehend
**Status**: 🔴 Offen (Lokal-Abhängig)
**Priorität**: P0 (Kritisch)
**Effort**: 30 Min

**Beschreibung:**
`.env` existiert, aber noch nicht mit `check_env.ps1` validiert.

**Acceptance Criteria:**
- [ ] `backoffice/automation/check_env.ps1` gegen `.env` ausgeführt
- [ ] Ergebnis dokumentiert (OK / WARN / ERROR)
- [ ] Fehlende ENV-Variablen ergänzt
- [ ] Status in PROJECT_STATUS.md aktualisiert

**Abhängigkeiten:**
- PowerShell (lokal)
- `.env` File (lokal, nicht im Repo)

**Blocker**: ⚠️ **Lokale Ausführung erforderlich**

---

### Issue #2: Systemcheck nicht durchgeführt
**Status**: 🔴 Offen (Lokal-Abhängig)
**Priorität**: P0 (Kritisch)
**Effort**: 1 Stunde

**Beschreibung:**
Container-Status ist nur Template, Health-Endpoints nicht verifiziert.

**Acceptance Criteria:**
- [ ] Docker Compose Stack gestartet (`docker compose up -d`)
- [ ] Container-Status geprüft (`docker compose ps`)
- [ ] Health-Endpoints getestet:
  - [ ] `curl http://localhost:8001/health` (Signal Engine)
  - [ ] `curl http://localhost:8002/health` (Risk Manager)
  - [ ] `curl http://localhost:8003/health` (Execution)
- [ ] Container-Status-Tabelle in PROJECT_STATUS.md aktualisiert
- [ ] Logs gesichtet (keine Errors)

**Abhängigkeiten:**
- Docker Desktop (lokal)
- Alle Services lauffähig

**Blocker**: ⚠️ **Lokale Ausführung erforderlich**

---

## 🟡 MITTEL - Qualitäts-Issues

### Issue #3: Dokumentations-Redundanz
**Status**: 🟢 Remote machbar
**Priorität**: P2 (Medium)
**Effort**: 2 Stunden

**Beschreibung:**
Multiple Status-Files existieren, unklare Source of Truth.

**Probleme:**
1. Mehrere Status-Dateien (PR_BODY.md, COMPLETION_SUMMARY.md, PROJECT_STATUS.md)
2. Keine klare Hierarchie
3. Überlappende Informationen

**Vorschlag:**
- **Single Source of Truth**: `PROJECT_STATUS.md` (kanonisch)
- **Helper Files**: In `backoffice/docs/reports/` verschieben
- **README.md**: Muss auf PROJECT_STATUS.md verweisen

**Acceptance Criteria:**
- [ ] Dokumentations-Hierarchie definiert (ADR oder Guideline)
- [ ] Helper-Files in `backoffice/docs/reports/` verschoben
- [ ] Links aktualisiert
- [ ] README.md verweist auf PROJECT_STATUS.md
- [ ] Keine redundanten Informationen mehr

**Remote machbar**: ✅ Ja (nur Dokumentations-Arbeit)

---

### Issue #4: Postgres-Backup-Strategie nicht umgesetzt
**Status**: 🟢 Remote machbar (teilweise)
**Priorität**: P2 (Medium)
**Effort**: 3 Stunden

**Beschreibung:**
Backup-Konzept ist in PROJECT_STATUS.md dokumentiert, aber nicht als Script/Job umgesetzt.

**Acceptance Criteria:**
- [ ] Backup-Script erstellt (`backoffice/automation/postgres_backup.sh` oder `.ps1`)
- [ ] Script testet:
  - [ ] `pg_dump` Befehl korrekt
  - [ ] Ablageort erstellt
  - [ ] Dateinamens-Schema (YYYY-MM-DD_HHMM)
  - [ ] Retention-Logic (14 Tage)
- [ ] Dokumentation in PROJECT_STATUS.md aktualisiert
- [ ] Optional: Cron-Job / Task-Scheduler-Config (Windows)

**Remote machbar**: ✅ Script schreiben (Ja), Testen (Nein - braucht lokale DB)

---

### Issue #5: Risk-Engine Production-Grade Logic
**Status**: 🟡 Teilweise remote machbar
**Priorität**: P2 (Medium)
**Effort**: 8 Stunden (Epic)

**Beschreibung:**
`services/risk_engine.py:430` enthält TODO-Kommentar für Production-Grade-Logik.

**TODO-Kommentar:**
```python
# TODO: Replace placeholder risk logic with production-grade rules and
# connectivity to portfolio and order management services.
```

**Teilaufgaben:**
1. **Risk-Logic Review** (Remote möglich):
   - [ ] Bestehende Risk-Layers dokumentieren
   - [ ] Fehlende Validierungen identifizieren
   - [ ] ADR für Production-Grade-Risk-Logic schreiben

2. **Portfolio-Integration** (Lokal erforderlich):
   - [ ] Portfolio-Service anbinden
   - [ ] State-Tracking implementieren
   - [ ] Tests schreiben & ausführen

3. **Order-Management-Integration** (Lokal erforderlich):
   - [ ] Order-Service anbinden
   - [ ] Event-Flow validieren
   - [ ] E2E-Tests schreiben

**Remote machbar**: ✅ Design & Documentation (Ja), Implementation (Teilweise)

---

## 🟢 NIEDRIG - Nice-to-Have

### Issue #6: Markdownlint-Warnungen beheben
**Status**: 🟢 Remote machbar
**Priorität**: P3 (Low)
**Effort**: 1 Stunde

**Beschreibung:**
CI-Pipeline führt markdownlint aus (non-blocking), aber Warnungen werden nicht behoben.

**Acceptance Criteria:**
- [ ] `markdownlint '**/*.md'` lokal ausgeführt
- [ ] Warnungen analysiert
- [ ] Behebbare Warnungen gefixt
- [ ] `.markdownlintrc` angepasst (falls nötig)
- [ ] CI-Job grün

**Remote machbar**: ✅ Ja (nur Markdown-Editing)

---

### Issue #7: Type-Coverage erhöhen
**Status**: 🟢 Remote machbar
**Priorität**: P3 (Low)
**Effort**: 4 Stunden

**Beschreibung:**
mypy läuft in CI (non-blocking), Type-Coverage ist ~50% (Target: >70%).

**Acceptance Criteria:**
- [ ] Type-Hints in `services/` hinzugefügt
- [ ] mypy ohne `--ignore-missing-imports` lauffähig
- [ ] Type-Coverage >70%
- [ ] mypy in CI auf blocking setzen

**Remote machbar**: ✅ Ja (nur Code-Editing ohne Ausführung)

---

### Issue #8: Link-Checking implementieren
**Status**: 🟢 Remote machbar
**Priorität**: P3 (Low)
**Effort**: 2 Stunden

**Beschreibung:**
CI-Pipeline hat Placeholder für Link-Checking, aber nicht implementiert.

**Acceptance Criteria:**
- [ ] `markdown-link-check` in CI-Pipeline integriert
- [ ] Alle internen Links validiert
- [ ] Broken Links gefixt
- [ ] Job non-blocking (MVP-Phase)

**Remote machbar**: ✅ Ja (CI-Config + Markdown-Fixes)

---

## 📊 Priorisierungs-Matrix

| Issue | Priorität | Effort | Remote? | Blocker? |
|-------|-----------|--------|---------|----------|
| #1 ENV-Validation | P0 | 30 Min | ❌ | ✅ Deployment |
| #2 Systemcheck | P0 | 1h | ❌ | ✅ Deployment |
| #3 Docs-Redundanz | P2 | 2h | ✅ | ❌ |
| #4 Postgres-Backup | P2 | 3h | 🟡 | ❌ |
| #5 Risk-Engine | P2 | 8h | 🟡 | ❌ |
| #6 Markdownlint | P3 | 1h | ✅ | ❌ |
| #7 Type-Coverage | P3 | 4h | ✅ | ❌ |
| #8 Link-Checking | P3 | 2h | ✅ | ❌ |

**Legende:**
- P0 = Kritisch (Deployment-Blocker)
- P2 = Medium (Qualität)
- P3 = Low (Nice-to-Have)
- ✅ Remote machbar
- 🟡 Teilweise remote
- ❌ Lokal erforderlich

---

## 🎯 Empfohlene Reihenfolge (Remote-First)

### **Sofort (Remote, heute machbar):**
1. **#3 Dokumentations-Redundanz** (2h) - Aufräumen & Strukturieren
2. **#4 Postgres-Backup-Script** (2h) - Script schreiben (ohne Test)
3. **#6 Markdownlint-Warnungen** (1h) - Quick-Win

**Total**: 5 Stunden

### **Diese Woche (Remote):**
4. **#5 Risk-Engine Design** (4h) - Review & ADR (ohne Implementation)
5. **#8 Link-Checking** (2h) - CI-Pipeline erweitern

**Total**: +6 Stunden

### **Lokal (wenn Docker/PowerShell verfügbar):**
6. **#1 ENV-Validation** (30 Min) - KRITISCH
7. **#2 Systemcheck** (1h) - KRITISCH
8. **#4 Postgres-Backup Test** (1h) - Script testen
9. **#5 Risk-Engine Implementation** (4h) - Services integrieren

**Total**: +6.5 Stunden

---

## 📝 Notizen

### **Wichtig:**
- Issues #1 und #2 sind **Deployment-Blocker** - müssen vor Production-Release gelöst sein
- Issues #3-#8 sind **Qualitäts-Improvements** - können parallel laufen

### **Nächste Schritte:**
1. Priorisierung mit Jannek abstimmen
2. Remote-machbare Issues zuerst abarbeiten
3. Für lokale Issues: Termin mit Jannek koordinieren

---

**Erstellt**: 2025-11-21
**Projekt**: Claire de Binaire - Autonomous Crypto Trading Bot
**Phase**: N1 - Paper Trading Implementation
