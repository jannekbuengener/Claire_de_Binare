# DB-Namen-Inkonsistenz-Bericht
**Datum**: 2025-01-11
**Status**: ⚠️ **KRITISCH** – Inkonsistenz gefunden
**Scope**: Projektweit (Code, Doku, Scripts, ENV-Files)

---

## 🚨 Problem-Statement

Projektname-Ordner lautet `claire_de_binare` (ohne "i"), aber **Datenbank-Namen** sind NICHT konsistent:

- ✅ **Korrekt (Mehrheit)**: `claire_de_binare` (ohne "i") – **87 Vorkommen**
- ❌ **Inkonsistent**: `claire_de_binaire` (mit "i") – **28 Vorkommen**

**Impact**:
- Container-Startfehler bei falschen ENV-Variablen
- Postgres-Connection-Errors in Python-Services
- Backup-Skripte greifen ggf. falsche DB

---

## 📊 Detaillierte Auswertung

### ✅ **Korrekt: `claire_de_binare`** (87 Vorkommen)

**Produktions-kritische Dateien**:
- `docker-compose.yml` Zeile 35: `POSTGRES_DB: claire_de_binare` ✅
- `backoffice/.env.example` Zeile 37: `POSTGRES_DB=claire_de_binare` ✅
- `backoffice/services/execution_service/config.py` Zeile 36: Default `claire_de_binare` ✅
- `backoffice/services/query_service/config.py` Zeile 16: Default `claire_de_binare` ✅
- `operations/backup/daily_backup_full.ps1` Zeile 22: `pg_dump claire_de_binare` ✅
- `scripts/daily_backup.ps1` Zeile 20: `pg_dump claire_de_binare` ✅

**Dokumentation** (alle korrekt):
- `QUICK_START.md` (3 Vorkommen, alle `claire_de_binare`)
- `BACKUP_ANLEITUNG.md` (4 Vorkommen, alle Pfade korrekt)
- `backoffice/docs/research/QUICK_REFERENCE_AGENTS.md` (neu erstellt, korrekt)
- `backoffice/audits/PR_BESCHREIBUNG.md` (dokumentiert Vereinheitlichung)

---

### ❌ **Inkonsistent: `claire_de_binaire`** (28 Vorkommen)

#### **1. Execution Service (KRITISCH)**

**Datei**: `backoffice/services/execution_service/EXECUTION_SERVICE_STATUS.md`
- **Zeile 102**:
  ```python
  f"postgresql://postgres:{os.getenv('POSTGRES_PASSWORD', 'changeme')}@cdb_postgres:5432/claire_de_binaire"
  ```
  → ❌ **Sollte sein**: `claire_de_binare`

- **Zeile 177**:
  ```bash
  docker exec -it cdb_postgres psql -U postgres -d claire_de_binaire -c "SELECT * FROM orders LIMIT 1;"
  ```
  → ❌ **Sollte sein**: `claire_de_binare`

**Impact**: Falls dieser Code-Snippet noch irgendwo verwendet wird, würde `psycopg2` die falsche DB versuchen zu öffnen.

---

#### **2. Archiv-Dokumente (informativ, nicht kritisch)**

**Datei**: `backoffice/audits/DIFF-PLAN.md`
- **Zeile 13**: `-- Database: database_claire_de_binaire` (historisch, zeigt ALTE inkonsistente Version)
- **Zeile 19**: `sed -i 's/database_claire_de_binaire/claire_de_binare/g'` (dokumentierte Korrektur)
→ **OK**: Audit-Dokument zeigt Änderungshistorie, keine Action erforderlich

**Datei**: `.github/chatmodes/Organiesieren.chatmode.md`
- **Zeilen 94, 98, 114**: Historische Beispiele für Inkonsistenzen (Lernmaterial für Copilot)
→ **OK**: Chatmode-Prompts zeigen Best Practices, keine Action erforderlich

**Datei**: `backoffice/docs/reports/CODE_CLEANUP_AUDIT.md`
- **17 Vorkommen**: Dokumentiert historische Inkonsistenz und Korrektur-Empfehlung
→ **OK**: Report dokumentiert Problem und Lösung

**Datei**: `backoffice/docs/reports/FINAL_STATUS.md`
- **Zeilen 196, 219**: Windows File Sharing Path mit "i" (`claire_de_binaire`)
→ ⚠️ **PRÜFEN**: Ordnername ist definitiv `claire_de_binare` (ohne "i") – Tippfehler im Report?

---

#### **3. Research-Dokumente (nur Referenzen)**

**Datei**: `backoffice/docs/research/cdb_redis.md`
- **Zeilen 85, 297**: Erwähnt explizit, dass DB-Name `claire_de_binare` (ohne Accent) sein MUSS
→ ✅ **OK**: Dokument betont korrekte Variante

**Datei**: `backoffice/docs/research/KNOWLEDGE_BASE_INTEGRATION_2025-01-11.md`
- **Zeile 282**: Erwähnt historische Inkonsistenz
→ ✅ **OK**: Dieses neue Dokument dokumentiert das Problem

**Datei**: `backoffice/docs/END_TO_END_TEST_GUIDE.md`
- **Zeile 177**: `**💡 WICHTIG:** Database-Name ist claire_de_binare (NICHT claire_de_binaire!)`
→ ✅ **OK**: Warnt explizit vor Inkonsistenz

---

## 🔧 Action Items (Prio 1)

### **1. Fix Execution Service Dokumentation**

**Datei**: `backoffice/services/execution_service/EXECUTION_SERVICE_STATUS.md`

**Zeile 102 (alt)**:
```python
f"postgresql://postgres:{os.getenv('POSTGRES_PASSWORD', 'changeme')}@cdb_postgres:5432/claire_de_binaire"
```

**Zeile 102 (neu)**:
```python
f"postgresql://postgres:{os.getenv('POSTGRES_PASSWORD', 'changeme')}@cdb_postgres:5432/claire_de_binare"
```

**Zeile 177 (alt)**:
```bash
docker exec -it cdb_postgres psql -U postgres -d claire_de_binaire -c "SELECT * FROM orders LIMIT 1;"
```

**Zeile 177 (neu)**:
```bash
docker exec -it cdb_postgres psql -U postgres -d claire_de_binare -c "SELECT * FROM orders LIMIT 1;"
```

---

### **2. Prüfe FINAL_STATUS.md Windows-Pfad**

**Datei**: `backoffice/docs/reports/FINAL_STATUS.md`

**Zeile 196 (aktuell)**:
```
C:\Users\janne\Documents\claire_de_binaire
```

**Zeile 196 (korrigiert, falls Ordner wirklich `...binare` heißt)**:
```
C:\Users\janne\Documents\claire_de_binare
```

**ACHTUNG**: Erst Filesystem prüfen! Falls der Ordner wirklich `claire_de_binaire` heißt, ist die ENV-Variable falsch!

---

### **3. Globale Validierung**

**Command**:
```powershell
## Suche nach ALLEN Varianten (inkl. "database_claire_...")
rg -n "claire_de_binaire|database_claire_de_binaire|database_claire_de_binare" -g "!*.md" -g "!archive/*"
```

**Erwartung**: Nur `.env.example`, `config.py`, `docker-compose.yml` sollten `claire_de_binare` enthalten, KEINE Varianten mit "i" oder "database_"-Prefix.

---

## ✅ Empfohlene Vereinheitlichung

**Projektweiter Standard**:
```
claire_de_binare
```

**Begründung**:
1. ✅ Projektordner heißt `claire_de_binare`
2. ✅ docker-compose.yml nutzt `claire_de_binare`
3. ✅ Backup-Skripte nutzen `claire_de_binare`
4. ✅ Query Service + Execution Service Default ist `claire_de_binare`
5. ✅ 87 Vorkommen vs. 28 inkonsistente

**Alternative**: Falls Ordner wirklich `claire_de_binaire` heißt (mit "i"), müssten **alle** ENV-Variablen, Scripts, Configs geändert werden → **NICHT empfohlen** (zu hohe Änderungsanzahl).

---

## 🔍 Filesystem-Prüfung (nächster Schritt)

**Vor Korrektur ausführen**:
```powershell
## Prüfe tatsächlichen Ordnernamen
(Get-Item "C:\Users\janne\Documents\claire_de_bina*").Name

## Erwartung: claire_de_binare
```

Falls `claire_de_binaire` zurückkommt → **ALARM**: Dann ist Projektordner inkonsistent mit Code!

---

## 📝 Änderungs-Tracking

| Datum | Aktion | Status |
|-------|--------|--------|
| 2025-01-11 | Inkonsistenz entdeckt (87 vs 28 Vorkommen) | ⏳ Identifiziert |
| 2025-01-11 | Action Items definiert (2 kritische Fixes) | ⏳ Ausstehend |
| – | Execution Service Doku korrigiert | ⏳ Pending |
| – | FINAL_STATUS.md Pfad validiert | ⏳ Pending |
| – | Globale Validierung abgeschlossen | ⏳ Pending |

---

**Ende des Berichts** | Nächste Schritte: 1. Filesystem prüfen, 2. Fixes anwenden, 3. Globale Validierung