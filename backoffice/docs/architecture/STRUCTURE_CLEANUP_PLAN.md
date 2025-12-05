
---

## 2) `STRUCTURE_CLEANUP_PLAN.md`

```markdown
# STRUKTUR-CLEANUP-PLAN (Post-Nullpunkt – Claire de Binare)

Stand: 2025-01-17  
Repository: `Claire_de_Binare_Cleanroom`  
Kontext: Cleanroom-Nullpunkt ist definiert, Dokumentation ist konsolidiert. Dieses Dokument beschreibt die geplanten Struktur-Cleanups, die auf diesem Nullpunkt aufsetzen.

Ziel: Die physische Repository-Struktur (Ordner, Dateien, Caches) an die dokumentierten Prinzipien und das N1-Zielbild anpassen – ohne den Nullpunkt oder die Cleanroom-Dokumente zu verändern.

---

## 1. Leitprinzipien

1. **Doku bleibt führend**  
   - `backoffice/docs/` beschreibt den Zielzustand. Struktur-Cleanups orientieren sich an KODEX, DECISION_LOG und den Nullpunkt-Dokumenten.

2. **Iterative, kleine Schritte**  
   - Änderungen werden in klar trennbare Commits aufgeteilt (z. B. „nur __pycache__“, „nur mexc_top5_ws-Service“).

3. **Archiv nicht vermischen**  
   - `archive/` bleibt historisches Material. Keine aktiven Workflows dort etablieren.

4. **Keine Änderung am Nullpunkt**  
   - CLEANROOM_BASELINE-Dokumente und ADR-039 bleiben unverändert und dienen als Referenz.

---

## 2. Thema A – Root-Archiv (`archive/`)

**Ist-Zustand**

- `archive/` liegt im Repo-Root und enthält:
  - `backoffice_original/`, `docs_original/`
  - `sandbox_backups/`, `meeting_archive/`, `security_audits/`
  - diverse historische Backups und ältere Versionen
- Rolle: Historische Referenz, nicht aktiver Arbeitsbereich.

**Zielbild**

- `archive/` bleibt als **historisches Top-Level-Verzeichnis** bestehen.
- In der Doku ist klar kommuniziert:
  - `archive/` = „Cold Storage“ (kein aktiver Workspace)
  - Nur für Audits, Forensik und historische Rekonstruktion.

**Konkrete Schritte**

1. In `backoffice/docs/infra/repo_map.md` einen kurzen Abschnitt ergänzen:
   - Beschreibung der Rolle von `archive/` (historisch, read-only).
2. In `backoffice/docs/audit/AUDIT_CLEANROOM.md` sicherstellen:
   - `archive/` wird als historischer Bereich markiert, nicht als Verstoß.
3. Optional (spätere Phase): Umzug nach `backoffice/docs/archive/` diskutieren und ggf. per ADR entscheiden.

---

## 3. Thema B – `mexc_top5_ws.py` im Repo-Root

**Ist-Zustand**

- Datei `mexc_top5_ws.py` liegt im Repository-Root.
- Funktion: WebSocket-/Daten-Script (Top-5-MEXC), nicht sauber in den Service-Layer integriert.

**Zielbild**

- Das Script wird als eigener Service unter `backoffice/services/` geführt, z. B.:
  - `backoffice/services/screener_ws/`
    - `service.py` (aus `mexc_top5_ws.py` migriert)
    - `config.py`, `models.py` (bei Bedarf)
    - `Dockerfile`, `requirements.txt`
    - `README.md`
- Service ist im KODEX / in der Service-Doku verankert.

**Konkrete Schritte**

1. Neuen Ordner anlegen: `backoffice/services/screener_ws/`
2. `mexc_top5_ws.py` in `backoffice/services/screener_ws/service.py` verschieben.
3. Falls nötig: `__init__.py` hinzufügen, damit der Ordner als Package fungiert.
4. Minimale `README.md` im neuen Service-Ordner erstellen:
   - Zweck, Input/Output, Abhängigkeiten, Verweis auf N1-Phase (Paper-Test / Data-Feed).
5. `backoffice/docs/services/` um eine Service-Beschreibung für den Screener-Service ergänzen.
6. In `docker-compose.yml` und ggf. in weiteren Infra-Dokumenten:
   - Service eintragen oder zumindest als Option beschreiben.
7. Alte Referenzen auf `mexc_top5_ws.py` im Root (z. B. in Docs) auf den neuen Pfad anpassen.

**Empfohlener Commit**

- „feat: screener_ws service from mexc_top5_ws root script“

---

## 4. Thema C – `__pycache__/` und temporäre Artefakte

**Ist-Zustand**

- Mehrere `__pycache__/`-Ordner sind im Repo vorhanden, u. a.:
  - `backoffice/services/risk_manager/__pycache__/`
  - `backoffice/services/signal_engine/__pycache__/`
  - `tests/integration/__pycache__/`
  - `tests/unit/__pycache__/`
- Diese Dateien sollten nicht versioniert werden.

**Zielbild**

- Keine `__pycache__/`-Verzeichnisse im Git-Repository.
- `.gitignore` deckt alle Python-Bytecode-Artefakte ab.

**Konkrete Schritte**

1. `.gitignore` prüfen und ggf. ergänzen:
   - Eintrag sicherstellen: `__pycache__/` und `*.py[cod]`
2. Alle bestehenden `__pycache__/`-Verzeichnisse aus dem Repo entfernen:
   - lokal löschen
   - Commit mit reinem Cleanup (ohne Codeänderungen)
3. Optional: In `backoffice/docs/infra/infra_knowledge.md` einen kurzen Hinweis ergänzen:
   - „Python-Bytecode und Caches werden nicht committed.“

**Empfohlener Commit**

- „chore: remove __pycache__ and tighten python ignore rules“

---

## 5. Thema D – Tests vs. Test-Dokumentation

**Ist-Zustand**

- `tests/` im Repo-Root enthält Test-Code (Unit/Integration).  
- `backoffice/docs/tests/` enthält Test-Dokumentation.
- Trennung ist bereits vorhanden, aber nicht überall explizit erklärt.

**Zielbild**

- Die Trennung von Test-Code und Test-Dokumentation ist dokumentiert und wird konsequent eingehalten.

**Konkrete Schritte**

1. In `backoffice/docs/tests/` ein kurzes Index-Dokument (falls noch nicht vorhanden) pflegen, das beschreibt:
   - Zweck des Ordners
   - Beziehung zu `tests/`
2. In README und im Cleanroom-Onboarding-Dokument (Onboarding & Repo Navigation):
   - Kurzen Hinweis ergänzen, dass:
     - `tests/` = ausführbare Tests
     - `backoffice/docs/tests/` = Testkonzepte, Testpläne, Coverage-Übersicht
3. Bei neuen Tests:
   - Sicherstellen, dass relevante Teststrategien in den Docs abgebildet werden (insbesondere für Risk-/Execution-Logik in N1).

**Empfohlener Commit**

- „docs: clarify separation of test code and test documentation“

---

## 6. Thema E – README / Top-Level-Einstieg

**Ist-Zustand**

- README im Repo-Root existiert, ist aber möglicherweise noch auf Pre-Nullpunkt- oder Migrationskontexte ausgerichtet.

**Zielbild**

- README spiegelt den Cleanroom-Nullpunkt und die N1-Phase wider.
- README verweist auf:
  - KODEX
  - EXECUTIVE_SUMMARY
  - CLEANROOM_BASELINE_SUMMARY
  - N1_ARCHITEKTUR
  - Cleanroom-Onboarding-Dokument

**Konkrete Schritte**

1. README-Text überprüfen und aktualisieren:
   - Migration als Historie / abgeschlossene Phase formulieren.
   - Aktuelle Phase: N1 – Paper-Test.
   - Kurze Erklärung, dass `backoffice/docs/` die Single Source of Truth ist.
2. Link-/Pfad-Hinweise anpassen (keine alten Root-KODEX/DECISION_LOG-Pfade).
3. Hinweis einbauen, dass neue Contributor mit dem Onboarding-Dokument starten sollen.

**Empfohlener Commit**

- „docs: align README with cleanroom baseline and N1 phase“

---

## 7. Empfohlene Commit-Reihenfolge

Zur Reduktion von Risiko und Merge-Konflikten:

1. **Cleanup-Commit (Caches)**
   - __pycache__ entfernen, .gitignore anpassen.
   - Commit: „chore: remove __pycache__ and tighten python ignore rules“

2. **Screener-Service-Commit**
   - `mexc_top5_ws.py` in `backoffice/services/screener_ws/` überführen.
   - Service-Doku ergänzen.
   - Commit: „feat: screener_ws service from mexc_top5_ws root script“

3. **README-/Onboarding-Commit**
   - README aktualisieren.
   - Cleanroom-Onboarding-/Repo-Navigation-Dokument verlinken.
   - Commit: „docs: update onboarding and repo navigation for cleanroom baseline“

4. **Optionaler Archiv-Commit**
   - Nur wenn später gewünscht und per ADR entschieden:
     - `archive/` restrukturieren oder verschieben.
   - Commit: „chore: restructure archive as historical documentation area“

---

## 8. Nächste Schritte (für Audit / Roadmap)

Diese Liste kann in zukünftige Audits oder Projektpläne übernommen werden:

- [ ] Prüfen, ob alle `__pycache__`-Verzeichnisse entfernt und in `.gitignore` abgedeckt sind.  
- [ ] `mexc_top5_ws.py` in einen sauberen Service (`backoffice/services/screener_ws/`) überführen.  
- [ ] README an Cleanroom-Nullpunkt und N1-Phase anpassen.  
- [ ] Kurzen Hinweis auf Trennung `tests/` vs. `backoffice/docs/tests/` in README und Test-Doku ergänzen.  
- [ ] Rolle von `archive/` in `repo_map.md` und `AUDIT_CLEANROOM.md` klar als historischer Bereich definieren.  
- [ ] Optional: Entscheidung treffen (per ADR), ob `archive/` langfristig in einen Unterordner von `backoffice/docs/` migriert werden soll.

Dieses Dokument dient als operative Brücke zwischen der definierten Cleanroom-Dokumentation und den noch ausstehenden Strukturänderungen im Repository.
