# 🔍 AUDIT-PLAN FÜR CLAIRE DE BINARE CLEANROOM

**Datum**: 2025-01-14  
**Version**: 1.0  
**Status**: ⚡ AKTIV

---

## 📊 ANALYSEERGEBNISSE

### ✅ STÄRKEN (Was funktioniert)

1. **Struktur-Compliance**: Ordnerstruktur exakt nach Schema umgesetzt
2. **Dokumentations-Vollständigkeit**: 31 Artefakte (~8400 Zeilen) vorhanden
3. **Security-Score**: Von 70% auf 95% verbessert
4. **Kanonisches Schema**: Vollständige Service-Definitionen in YAML

### ⚠️ SCHWACHSTELLEN (Gefunden)

1. **Fehlende Kern-Dokumente**:
   - `PROJECT_STATUS.md` nicht vorhanden
   - `MANIFEST.md` fehlt
   - `MASTER_ÜBERSICHT.md` nicht migriert

2. **Test-Artefakte in Docs**:
   - `__pycache__` Ordner sollten nicht in docs/tests sein
   - .pyc Dateien gehören ins .gitignore

3. **Redundanz**:
   - Multiple Status-Dateien (FINAL_STATUS, MIGRATION_READY, etc.)
   - Überlappende Index-Dateien (INDEX.md, sources_index.md, file_index.md)

4. **Unklare Verantwortlichkeiten**:
   - Tests in `/tests` UND `/backoffice/docs/tests`
   - Services-Doku in `/backoffice/docs/services` UND Services selbst in `/backoffice/services`

---

## 🎯 AUDIT-PHASEN (Priorisiert)

### **PHASE 1: KRITISCH - Security & Compliance** 🔴
**Timeline**: SOFORT (30 Min)

#### Checklist:
- [ ] `.env` File auf Secrets prüfen
- [ ] `.env.template` validieren (keine echten Werte)
- [ ] API-Keys Status (Read-only bestätigen)
- [ ] Docker-Security-Flags validieren
- [ ] Passwort-Policy für Redis/Postgres/Grafana

#### Commands für Audit:
```bash
# Security-Scan
grep -r "password\|secret\|key\|token" --exclude-dir=.git .env
diff .env .env.template

# Permissions Check
find . -type f -name "*.py" -exec ls -la {} \; | grep -E "^-rwx"
```

#### Deliverable: `SECURITY_AUDIT_REPORT.md`

---

### **PHASE 2: HOCH - ENV-Standardisierung** 🟠
**Timeline**: 45 Min

#### Probleme zu lösen:
1. **Dezimal vs. Prozent**: Alle auf Dezimal-Format (0.05 = 5%)
2. **Naming-Konventionen**: `UPPER_SNAKE_CASE` durchsetzen
3. **Prefix-Konsistenz**: Alle mit `CDB_` beginnen

#### Audit-Matrix:
```yaml
env_variables:
  risk_limits:
    - MAX_POSITION_SIZE: decimal (0.05)  # ✅
    - STOP_LOSS_PERCENT: decimal (0.02)  # ✅
    - MAX_DAILY_LOSS: decimal (0.10)     # ✅
  service_config:
    - CDB_REDIS_HOST: string             # ✅
    - CDB_POSTGRES_DB: string            # ✅
    - MEXC_API_KEY: string               # ⚠️ Kein CDB_ Prefix
```

#### Deliverable: `ENV_STANDARDIZATION.yaml`

---

### **PHASE 3: HOCH - Service-Code-Alignment** 🟠
**Timeline**: 60 Min

#### Validierung je Service:
```
/backoffice/services/
├── execution_service/
│   ├── config.py         → ENV-Vars korrekt?
│   ├── Dockerfile        → FROM python:3.11-slim?
│   └── requirements.txt  → Versionen fixiert?
├── risk_manager/
└── signal_engine/
```

#### Prüfpunkte:
- [ ] Config.py liest alle ENV-Vars aus canonical_schema.yaml
- [ ] Health-Endpoints implementiert (`/health`)
- [ ] Redis-Connections mit Retry-Logic
- [ ] Logging-Format konsistent

#### Deliverable: `SERVICE_VALIDATION_MATRIX.md`

---

### **PHASE 4: MITTEL - Dokumenten-Konsolidierung** 🟡
**Timeline**: 30 Min

#### Zu konsolidieren:
1. **Status-Dokumente** → Ein `PROJECT_STATUS.md`
2. **Index-Dateien** → Ein `MASTER_INDEX.md`
3. **Provenance** → Archiv-Ordner für alte Versionen

#### Neue Struktur:
```
/backoffice/docs/
├── PROJECT_STATUS.md        # SINGLE SOURCE OF TRUTH
├── MASTER_INDEX.md          # Zentrale Navigation
├── archive/                 # Alte Versionen
│   └── legacy_status/
└── audit/                   # Audit-Reports
```

#### Deliverable: `DOCUMENTATION_CLEANUP.md`

---

### **PHASE 5: MITTEL - Test-Struktur-Bereinigung** 🟡
**Timeline**: 20 Min

#### Aktionen:
1. **Entfernen**: `__pycache__` aus `/backoffice/docs/tests`
2. **Verschieben**: Tests aus docs → `/tests`
3. **Gitignore**: `*.pyc`, `__pycache__/` hinzufügen

#### Ziel-Struktur:
```
/tests/
├── unit/
├── integration/
├── fixtures/
└── conftest.py

/backoffice/docs/tests/  # NUR Dokumentation
├── TEST_STRATEGY.md
└── TEST_COVERAGE.md
```

#### Deliverable: `TEST_REORGANIZATION.md`

---

### **PHASE 6: NIEDRIG - Pre-Deployment-Check** 🟢
**Timeline**: 15 Min

#### Final Checklist:
- [ ] Docker-Compose validieren: `docker-compose config`
- [ ] Container-Namen konsistent: `cdb_*`
- [ ] Volumes persistent: `redis_data`, `postgres_data`
- [ ] Networks definiert: `cdb_network`
- [ ] Prometheus-Config vorhanden

#### Smoke-Test:
```bash
docker-compose up -d
sleep 30
curl -f http://localhost:8081/health  # signal_engine
curl -f http://localhost:8082/health  # risk_manager
curl -f http://localhost:8083/health  # execution
```

#### Deliverable: `DEPLOYMENT_READINESS.md`

---

## 📋 SOFORT-AKTIONEN

### 1. Fehlende Kern-Dateien erstellen:
```bash
# PROJECT_STATUS.md Template
cat > backoffice/PROJECT_STATUS.md << 'EOF'
# PROJECT STATUS - Claire de Binare
**Datum**: $(date +%Y-%m-%d)
**Version**: Cleanroom 1.0
**Status**: Pre-Deployment

## Container-Status
- [ ] cdb_redis: STOPPED
- [ ] cdb_postgres: STOPPED
- [ ] cdb_signal: STOPPED
[...]
EOF
```

### 2. Redundanz eliminieren:
```bash
# Archive alte Status-Files
mkdir -p backoffice/docs/archive/legacy_status
mv backoffice/docs/provenance/FINAL_STATUS.md backoffice/docs/archive/legacy_status/
mv backoffice/docs/runbooks/MIGRATION_READY.md backoffice/docs/archive/legacy_status/
```

### 3. Git-Cleanup:
```bash
# .gitignore erweitern
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".pytest_cache/" >> .gitignore

# Cached Files entfernen
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
```

---

## 🚀 NÄCHSTE SCHRITTE

1. **JETZT**: Phase 1 (Security-Audit) starten
2. **HEUTE**: Phases 2-3 (ENV + Services) 
3. **MORGEN**: Phases 4-6 (Cleanup + Deployment)

---

## 📊 ERFOLGS-METRIKEN

| Metrik | IST | SOLL | 
|--------|-----|------|
| Security-Score | 95% | 100% |
| ENV-Konsistenz | 70% | 100% |
| Service-Health | 0/8 | 8/8 |
| Test-Coverage | Unknown | >80% |
| Doku-Redundanz | High | None |

---

## 💡 EMPFEHLUNGEN

### Kritisch:
1. **CI/CD-Pipeline** aufsetzen (GitHub Actions)
2. **Monitoring-Dashboard** in Grafana vorbereiten
3. **Backup-Strategie** für Postgres definieren

### Nice-to-Have:
1. **README.md** für jeden Service
2. **API-Dokumentation** (OpenAPI/Swagger)
3. **Performance-Baseline** etablieren

---


### Nächste Schritte:

Diese Liste kannst du 1:1 in das nächste Audit / Runbook übernehmen:

Nächste Schritte (Struktur & Operative Umsetzung)

Doku einhängen

 Beide neuen Dokumente in das Repo einspielen (backoffice/docs/infra/…).

 In KODEX – Claire de Binare.md und PROJECT_STATUS.md kurz auf das Onboarding-Dokument verweisen.

 In README einen kurzen Absatz ergänzen: „Startpunkt: CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION“.

Python-Artefakte & Ignore-Regeln

 .gitignore prüfen/ergänzen (__pycache__/, *.py[cod]).

 Alle __pycache__/-Verzeichnisse aus dem Repo entfernen.

 Commit: „chore: remove pycache and tighten python ignore rules“.

mexc_top5_ws-Serviceisierung

 Neuen Ordner backoffice/services/screener_ws/ anlegen.

 mexc_top5_ws.py als service.py dorthin migrieren, minimalen Service-Rahmen bauen.

 Service-README + Eintrag in backoffice/docs/services/ anlegen.

 Commit: „feat: screener_ws service from mexc_top5_ws root script“.

README & Top-Level-Doku

 README auf Cleanroom-Nullpunkt + N1-Phase aktualisieren.

 Klarstellen: backoffice/docs/ = Single Source of Truth, tests/ vs. backoffice/docs/tests/ trennen.

 Commit: „docs: align README with cleanroom baseline and N1 phase“.

Archiv-Rolle klarziehen

 In backoffice/docs/infra/repo_map.md Rolle von archive/ als historischer Bereich beschreiben.

 In AUDIT_CLEANROOM.md sicherstellen, dass archive/ als historisch bewertet wird, nicht als Strukturfehler.

 Optional: später per ADR entscheiden, ob archive/ in einen Unterordner von backoffice/docs/ migriert werden soll.

**Bereit für Audit-Start?** → Phase 1 beginnen mit Security-Scan!
