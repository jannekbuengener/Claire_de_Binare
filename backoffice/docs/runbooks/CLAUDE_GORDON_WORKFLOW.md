# CLAUDE → GORDON Pipeline – Claire de Binaire

## 1. Ziel

Definierte Arbeitskette zwischen:
- **Claude** (Architekt, Entwickler, Orchestrator)
- **Gordon** (MCP-Executor, Docker-/System-Operator)

Ziel: Wiederholbare Abläufe für N1 (Paper-Test) und spätere Phasen.

---

## 2. Rollen

### Claude

- Liest und ändert Code, Tests, Doku.
- Definiert Architektur, ENV-Regeln, Risk-Logik.
- Formuliert präzise Befehle für Gordon.
- Bewertet Ergebnisse (Logs, Test-Output, Health-Status).

### Gordon

- Führt Kommandos aus (Docker, Shell, PowerShell, Tools).
- Meldet Status, Logs, Fehlertexte zurück.
- Verändert keine Architektur/Logik eigenständig.
- Arbeitet strikt nach Claude-Anweisungen.

---

## 3. Standard-Pipeline: N1 Systemcheck + Tests

### 3.1 Schritt 1 – ENV-Check

**Claude → Gordon (Befehl):**
```bash
# ENV-Template und .env prüfen
powershell backoffice/automation/check_env.ps1
```

**Gordon:**
1. Führt das Script aus.
2. Liefert Claude:
   - Exit-Code
   - Konsolen-Output
   - Liste fehlender oder doppelter Variablen.

**Claude:**
- Bewertet Ergebnis.
- Passt `.env.template` / `.env` / Doku an.
- Gibt ggf. neuen ENV-Check-Befehl.

---

### 3.2 Schritt 2 – Infrastruktur starten

**Claude → Gordon:**
```bash
docker compose up -d cdb_redis cdb_postgres cdb_prometheus cdb_grafana
```

**Gordon:**
- Startet die genannten Services.
- Meldet Claude:
  - `docker compose ps`-Auszug
  - Auffällige Logs bei Startproblemen.

---

### 3.3 Schritt 3 – Core-Services starten

**Claude → Gordon:**
```bash
docker compose up -d cdb_ws cdb_core cdb_risk cdb_execution
docker compose ps
```

**Gordon:**
- Startet die Container.
- Prüft Status mit `docker compose ps`.
- Meldet:
  - Status (running / exited)
  - Health-Spalte, falls vorhanden.

**Claude:**
- Aktualisiert PROJECT_STATUS.md (Container-Tabelle).
- Gibt bei Bedarf weitere Befehle (Logs, Restart, etc.).

---

### 3.4 Schritt 4 – Health-Checks

**Claude → Gordon:**
```bash
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8002/health
curl -fsS http://localhost:8003/health
```

**Gordon:**
- Führt die Requests aus.
- Liefert Claude:
  - HTTP-Statuscodes
  - Response-Bodys (z. B. `{ "status": "ok" }` oder Fehler).

**Claude:**
- Bewertet, ob Services „healthy“ sind.
- Leitet ggf. Log-Abfragen oder Bugfix-Aufträge ab.

---

### 3.5 Schritt 5 – Logs prüfen

**Claude → Gordon (bei Problemen oder Review):**
```bash
docker compose logs --tail=100 cdb_core cdb_risk cdb_execution
```

**Gordon:**
- Holt Logs.
- Gibt Claude:
  - relevante Logzeilen (Errors, Tracebacks, Warnings).
  - Zeitstempel, Container-Namen.

**Claude:**
- Analysiert Fehler.
- Passt Code/Config an.
- Definiert neue Tests oder Fixes.

---

### 3.6 Schritt 6 – pytest ausführen

**Claude → Gordon:**
```bash
# Im Projekt-Root, venv oder Container je nach Setup
pytest -v
```

**Gordon:**
- Führt Tests aus.
- Liefert Claude:
  - Zusammenfassung (passed/failed, Anzahl).
  - Voller Output von fehlgeschlagenen Tests.

**Claude:**
- Interpretiert Testergebnisse.
- Fixes im Code.
- Erweitert Tests (neue Fälle, Kantenbedingungen).

---

## 4. Pipeline für Backups (PostgreSQL)

### 4.1 Schritt 1 – Backup ausführen

**Claude → Gordon:**
```powershell
# Beispiel-Pfad anpassen
$timestamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
pg_dump -h localhost -p 5432 -U claire -d claire_de_binare `
    -F p -f "C:\Backups\cdb_postgres\${timestamp}_full.sql"
```

**Gordon:**
- Führt das Backup aus.
- Meldet Claude:
  - Erfolg/Fehlschlag.
  - Pfad der Backup-Datei.

### 4.2 Schritt 2 – Retention (14 Tage)

**Claude → Gordon:**
```powershell
Get-ChildItem "C:\Backups\cdb_postgres" -File |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
  Remove-Item
```

**Gordon:**
- Löscht alte Backups.
- Bestätigt Anzahl gelöschter Dateien.

**Claude:**
- Hält Datum des letzten erfolgreichen Backups in PROJECT_STATUS.md fest.

---

## 5. Fehler-Handling-Pipeline

### 5.1 Container startet nicht

**Claude → Gordon:**
```bash
docker compose ps
docker compose logs --tail=100 <problem-container>
```

**Gordon:**
- Liefert Status + Logs.

**Claude:**
- Diagnostiziert Ursache (Config, ENV, Code).
- Plant Fix + ggf. neue Tests.
- Gibt neue Kommandos (z. B. `docker compose up -d --build`).

---

## 6. Zusammenfassung – Ablauf in der Praxis

1. **Claude** aktualisiert Code, Tests, Doku.
2. **Claude** formuliert klare Befehle.
3. **Gordon** führt die Befehle aus (Docker, Scripts, Tests).
4. **Gordon** liefert Status, Logs, Outputs zurück.
5. **Claude** interpretiert, entscheidet, passt System an.
6. Zyklus wiederholt sich (Continuous Hardening + Testing).

Diese Datei dient als Referenz dafür, wie Claude und Gordon miteinander arbeiten, sodass Aufgaben klar getrennt, aber eng verzahnt bleiben.
