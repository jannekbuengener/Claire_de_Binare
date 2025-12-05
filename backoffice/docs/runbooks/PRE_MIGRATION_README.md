# Pre-Migration Execution Guide

**Erstellt**: 2025-11-16
**Status**: ✅ Execution-Artefakte bereit
**Nächster Schritt**: Pre-Migration-Tasks ausführen

---

## Übersicht

Dieser Ordner enthält alle notwendigen Tools und Dokumentationen, um die 4 CRITICAL Pre-Migration-Tasks sicher auszuführen.

---

## Dateien in diesem Ordner

### 📋 Dokumentation

| Datei | Zweck | Zielgruppe |
|-------|-------|------------|
| **pre_migration_checklist.md** | Schritt-für-Schritt-Anleitung mit manuellen & automatisierten Optionen | Alle (Start hier!) |
| **PIPELINE_COMPLETE_SUMMARY.md** | Vollständige Übersicht aller 4 Pipelines, Konflikte, nächste Schritte | Projekt-Lead |
| **canonical_readiness_report.md** | Go/No-Go-Bewertung (6 Kategorien, Conditional GO) | Architektur, QA |
| **PRE_MIGRATION_README.md** | Diese Datei - Einstieg in Pre-Migration | Alle |

### 🔧 Automatisierungs-Skripte

| Datei | Zweck | Verwendung |
|-------|-------|------------|
| **pre_migration_tasks.ps1** | Automatische Ausführung aller 4 Tasks | `.\pre_migration_tasks.ps1` |
| **pre_migration_validation.ps1** | Validierung nach Task-Ausführung | `.\pre_migration_validation.ps1` |

### 📄 Templates

| Datei | Zweck | Verwendung |
|-------|-------|------------|
| **.env.template** | Bereinigte ENV-Template-Datei (korrekte Dezimal-Konvention, keine Secrets) | Ins Repo-Root kopieren |

---

## Schnellstart (Empfohlener Workflow)

### Option 1: Automatisiert (Empfohlen)

```powershell
# 1. In sandbox/ wechseln
cd sandbox

# 2. Dry-Run (zeigt Änderungen, ohne sie auszuführen)
.\pre_migration_tasks.ps1 -DryRun

# 3. Echte Ausführung
.\pre_migration_tasks.ps1

# 4. Validierung
.\pre_migration_validation.ps1
```

**Erwartetes Ergebnis**:
```
✅ ALLE CHECKS BESTANDEN
Status: ✅ GO für Cleanroom-Migration
```

### Option 2: Manuell (Schritt-für-Schritt)

```powershell
# 1. Checkliste öffnen
code pre_migration_checklist.md

# 2. Schritte manuell durchführen (ca. 65 Min)
# 3. Validierung ausführen
.\pre_migration_validation.ps1
```

---

## Die 4 Pre-Migration-Tasks

| Task | ID | Beschreibung | Risiko | Aufwand |
|------|-----|--------------|--------|---------|
| **1** | SR-001 | Secrets aus ` - Kopie.env` bereinigen → `.env.template` | 🔴 CRITICAL | 15 Min |
| **2** | SR-002 | ENV-Naming auf Dezimal-Konvention umstellen | 🔴 CRITICAL | 20 Min |
| **3** | SR-003 | MEXC-API-ENV ergänzen | 🔴 CRITICAL | 5 Min |
| **4** | - | cdb_signal_gen aus docker-compose entfernen | 🟠 HIGH | 10 Min |

**Gesamt**: ~65 Min (automatisiert: ~5 Min)

---

## Was passiert bei jedem Task?

### Task 1: SR-001 - Secrets bereinigen

**Problem**: ` - Kopie.env` enthält echte Passwörter im Klartext:
- `POSTGRES_PASSWORD=Jannek8$`
- `GRAFANA_PASSWORD=Jannek2025!`

**Lösung**:
1. Alle echten Werte durch `<SET_IN_ENV>` ersetzen
2. Datei umbenennen zu `.env.template`
3. Sicherstellen: `.env` in `.gitignore`

**Validierung**: Keine Secrets in `.env.template`, Git-History sauber

---

### Task 2: SR-002 - ENV-Naming normalisieren

**Problem**: Inkonsistente ENV-Naming führt zu unwirksamen Risk-Limits:
- `MAX_DAILY_DRAWDOWN=5.0` wird als 500% interpretiert!

**Lösung**: Dezimal-Konvention (0.05 = 5%)
```bash
# ALT (FALSCH):
MAX_DAILY_DRAWDOWN=5.0
MAX_POSITION_SIZE=10.0
MAX_TOTAL_EXPOSURE=50.0

# NEU (KORREKT):
MAX_DAILY_DRAWDOWN_PCT=0.05   # 5%
MAX_POSITION_PCT=0.10          # 10%
MAX_EXPOSURE_PCT=0.50          # 50%
```

**Zusätzlich ergänzt**:
- `STOP_LOSS_PCT=0.02`
- `MAX_SLIPPAGE_PCT=0.01`
- `MAX_SPREAD_MULTIPLIER=5.0`
- `DATA_STALE_TIMEOUT_SEC=30`

**Validierung**: Alle 7 Risk-Parameter vorhanden, alte Namen entfernt

---

### Task 3: SR-003 - MEXC-API-ENV ergänzen

**Problem**: System nicht funktionsfähig ohne MEXC-API-Credentials

**Lösung**: In `.env.template` ergänzen:
```bash
MEXC_API_KEY=<SET_IN_ENV>
MEXC_API_SECRET=<SET_IN_ENV>
```

**Validierung**: Beide Keys vorhanden mit Platzhaltern

---

### Task 4: cdb_signal_gen entfernen

**Problem**: Service `cdb_signal_gen` in docker-compose.yml, aber `Dockerfile.signal_gen` fehlt

**Lösung**: Service-Block auskommentieren (wahrscheinlich Legacy, da `cdb_core` existiert)

**Validierung**: `docker compose config --quiet` ohne Fehler

---

## Nach erfolgreicher Pre-Migration

### 1. Status-Änderung

- **Vorher**: ⚠️ **CONDITIONAL GO**
- **Nachher**: ✅ **GO für Cleanroom-Migration**

### 2. Risiko-Level

- **Vorher**: 🟡 MEDIUM (4 CRITICAL-Risiken)
- **Nachher**: 🟢 LOW (alle kritischen Risiken behoben)

### 3. Nächste Schritte

Siehe `PIPELINE_COMPLETE_SUMMARY.md` → Abschnitt "Cleanroom-Migration-Ablauf":

**Phase 1**: Pre-Migration (✅ Abgeschlossen nach diesem Guide)
**Phase 2**: Migration (2-3h)
- Dateien aus sandbox/ ins Cleanroom-Repo kopieren
- DECISION_LOG.md mit ADRs ergänzen
**Phase 3**: Validierung (1h)
- docker compose up -d
- Health-Checks
- Smoke-Test
**Phase 4**: Post-Migration (laufend)
- SR-004, SR-005 beheben
- Test-Coverage erhöhen

---

## Troubleshooting

### "pre_migration_tasks.ps1 kann nicht ausgeführt werden"

**Ursache**: PowerShell Execution Policy

**Lösung**:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\pre_migration_tasks.ps1
```

### "Validation schlägt fehl - Secrets gefunden"

**Debug**:
```powershell
# Suche nach Secrets in .env.template
Select-String -Path .env.template -Pattern "Jannek|8\$|2025!"

# Manuell ersetzen
code .env.template
```

### "docker compose config" Fehler

**Häufige Ursachen**:
1. YAML-Syntax-Fehler (Einrückung)
2. Fehlende ENV-Variablen

**Debug**:
```powershell
# Detaillierte Fehlermeldung
docker compose config
```

---

## Skript-Parameter

### pre_migration_tasks.ps1

```powershell
# Dry-Run (keine Änderungen)
.\pre_migration_tasks.ps1 -DryRun

# Ohne Backup (schneller, aber riskanter)
.\pre_migration_tasks.ps1 -SkipBackup

# Kombination
.\pre_migration_tasks.ps1 -DryRun -SkipBackup
```

### pre_migration_validation.ps1

```powershell
# Standard
.\pre_migration_validation.ps1

# Verbose (detaillierte Ausgabe)
.\pre_migration_validation.ps1 -Verbose
```

---

## Wichtige Hinweise

### ⚠️ Secrets niemals committen!

**Vor jedem Commit**:
```powershell
# Check: Keine Secrets in staged files
git diff --cached

# Check: .env ist in .gitignore
git check-ignore .env
# Sollte ".env" ausgeben
```

### 🔐 .env vs .env.template

| Datei | Inhalt | Git-Status | Verwendung |
|-------|--------|------------|------------|
| `.env.template` | Platzhalter (`<SET_IN_ENV>`) | ✅ Committed | Template für neue Setups |
| `.env` | Echte Secrets | ❌ Gitignored | Lokale Konfiguration |

### 📊 Risiko-Level-Bedeutung

| Level | Symbol | Bedeutung |
|-------|--------|-----------|
| CRITICAL | 🔴 | Blocker - MUSS vor Migration behoben werden |
| HIGH | 🟠 | Sollte vor Production behoben werden |
| MEDIUM | 🟡 | Nice-to-have, nicht kritisch |
| LOW | 🟢 | Optional, Post-Migration OK |

---

## Support & Weitere Infos

### Detaillierte Dokumentation

- **Vollständige Pipeline-Übersicht**: `PIPELINE_COMPLETE_SUMMARY.md`
- **Kanonisches System-Modell**: `canonical_schema.yaml`
- **Readiness-Report**: `canonical_readiness_report.md`
- **Infra-Templates**: `infra_templates.md`

### Bei Fragen

1. Prüfe `pre_migration_checklist.md` → Troubleshooting-Sektion
2. Führe `pre_migration_validation.ps1 -Verbose` aus
3. Prüfe Backups in `sandbox/backups/`

---

**Viel Erfolg bei der Pre-Migration!** 🚀

**Status**: ⚠️ **CONDITIONAL GO** → ✅ **GO** (nach diesem Guide)
**Geschätzter Aufwand**: 5 Min (automatisiert) / 65 Min (manuell)
**Risiko**: 🟢 LOW (nach erfolgreicher Validierung)
