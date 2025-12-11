
### Bedeutung:

- **memory=8GB**  
  → WSL2 hat eine harte Obergrenze von 8 GB.  
  → Agents müssen RAM-sensitive Aufgaben *limitiert* betrachten.  
  → Keine „Großscans“ durch den gesamten Filesystem-Baum.

- **processors=8**  
  → Starke Parallelisierungsfähigkeit.  
  → CPU-bound Analysen (Repo-Hygiene, Code-Statistik, Log-Parsing) laufen performant.  
  → Agents wie `repository-auditor`, `refactoring-engineer`, `dataflow-enhancer` profitieren.

- **swap=4GB**  
  → Falls RAM knapp wird, kann WSL in Swap auslagern.  
  → Performance sinkt stark beim Überschreiten von ~7GB realer Nutzung.  
  → Agents müssen *immer* Scope-Begrenzungen anfordern, bevor sie große Analysen fahren.

- **localhostForwarding=true**  
  → Docker/Services sind über `localhost:` erreichbar, kein NAT-Hopping.  
  → Perfekt für Agents, die Logs oder HTTP Endpoints analysieren sollen.

- **defaultVhdSize=256GB**  
  → Genügend Platz für Repos, Container, Logs.  
  → Aber: Agents dürfen niemals automatisch „alles durchsuchen“.

---

# 2. Docker Runtime Environment

## 2.1 Docker Desktop (WSL2 Backend)
- Läuft vollständig innerhalb der oben beschriebenen Ressourcenlimits.
- Docker nutzt **8 vCPUs**, aber teilt sich RAM mit WSL.

## 2.2 Auswirkungen auf Analysen
- Docker-Logs & Volumes liegen im **WSL-FS**, nicht auf Windows → schneller Zugriff.
- CPU starke Services (Prometheus, Loki, Grafana) laufen stabil, solange 8GB nicht überschritten werden.
- Viele gleichzeitige Container können Swap triggern → Agents sollen konservativ planen.

---

# 3. Relevanz für Claude Code & Agents

## 3.1 Agents, die stark betroffen sind:

### **RAM-intensive Agents**
- `repository-auditor`  
- `stability-guardian`  
- `dataflow-enhancer`  
- `system-architect` (bei großen Repos / Trees)

**Regel:**  
Keine Vollscans. Nur gezielte Bereiche.

---

### **CPU-intensive Agents**
- `dataflow-enhancer` (CI-/Repo-Metriken)  
- `refactoring-engineer`  
- `code-reviewer` (Statistik-Analysen)  

Dank 8 vCPUs → gute Parallelfähigkeit.

---

### **IO-intensive Agents**
- `repository-auditor`  
- `documentation-engineer` (beim Lesen vieler Dateien)  
- `market-analyst` / `data-analyst` (wenn Logs/CSVs groß sind)

---

# 4. Zugriffspfade (MCP Gateway Stack)

Claude sieht dein System NICHT wie ein lokaler Prozess, sondern über:

- Filesystem  
- GitHub/GitLab  
- Logs/Outputs  
- Docker-artige Pfade, *wenn* sie gemountet sind  

→ Agents dürfen NICHT eigenständig Docker-Kommandos vorschlagen.  
→ Sie dürfen nur analysieren, was per MCP zugreifbar ist.

---

# 5. Richtlinien für Agents & Workflows

### 5.1 Agents müssen IMMER:

- den Scope begrenzen  
- Speicherbedarf berücksichtigen  
- IO-Last abschätzen  
- große Analysen in Teile aufsplitten  
- nur das analysieren, was du ihnen freigibst  

---

### 5.2 Workflows (z. B. Feature / Bugfix) müssen beachten:
(Referenzen: WORKFLOW_Feature_Implementation.md, WORKFLOW_Bugfix.md)

- Keine Bulk-Analysen von Repos  
- Keine vollständigen Test-Scans ohne Angabe  
- Keine Multi-Service-Analysen ohne Scope  
- Architektur- und Risiko-Prozesse dürfen *auf diese Limits hinweisen*

---

# 6. Empfehlungen für Performance

**Do:**
- Repos unter `/home/...` statt `C:\` (bereits Standard in WSL2)
- Analysen immer in Bereichen (Ordnern, Files)  
- Logs begrenzen (z. B. letzte 1000 Zeilen)

**Don’t:**
- Vollständige Log-Archive durchforsten  
- Gigabyte-Dumps analysieren lassen  
- Gleichzeitig mehrere schwere Agents auf dasselbe Repo werfen  

---

# 7. Zusammenfassung

Dein System ist:

- **8GB RAM (Hard Cap)**  
- **8 vCPUs (Parallele Power)**  
- **4GB Swap (Notfall)**  
- **WSL2 mit Docker Backend**  
- **Optimiert für CDB Stack: Grafana, Prometheus, Loki, Agents**

Agents & Workflows sind jetzt **perfekt informiert**, unter welchen realen Bedingungen sie arbeiten.

