# Cleanroom Runbooks – Index & Übersicht

Dieses Verzeichnis enthält alle operativen Runbooks für die Cleanroom-Phase IV (Execution Blueprint).
Jedes Dokument ist eigenständig verwendbar und kann als Vorlage für andere Projekte übernommen werden.

---

## 🧭 Übersicht

| Datei | Zweck | Inhaltsschwerpunkt |
|-------|-------|--------------------|
| [RUNBOOK_CLEANROOM_EXEC.md](RUNBOOK_CLEANROOM_EXEC.md) | Haupt-Runbook | Vollständiger Ablaufplan aller Tracks (Dry-Run, Security-Sanitation, Doku-Kuration) mit CLI-/Desktop-Befehlen |
| [CHECKLISTS_EXEC.md](CHECKLISTS_EXEC.md) | Checklisten | Go/No-Go-, Pre-Flight- und Post-Flight-Checklisten zur operativen Durchführung |
| [COMMANDS_CLI.txt](COMMANDS_CLI.txt) | CLI-Kommandos | Copy-Paste-fähige Befehlsfolgen für Git, CI und Sanitation |
| [COMMANDS_DESKTOP.txt](COMMANDS_DESKTOP.txt) | GitHub Desktop | Schritt-für-Schritt-Anleitung für visuelle Workflows |
| [ROLLBACK_PLAYBOOK.md](ROLLBACK_PLAYBOOK.md) | Rollback-Guide | Szenarien & Notfall-Wiederherstellungen für PRs, Force-Pushes, Pfadfehler |
| [COMMS_PACK.md](COMMS_PACK.md) | Kommunikationspaket | Vorlagen für Stakeholder-Mails, PR-Bodies, Release Notes |
| [SCHEDULE_OWNER_MATRIX.md](SCHEDULE_OWNER_MATRIX.md) | Zeit- & Owner-Matrix | Ablaufplan mit Verantwortlichkeiten, Zeitfenstern und Nachweisfeldern |

---

## 🔐 Verwendungsrichtlinien

1. **Keine Ausführung aus den Runbooks heraus.**
   Alle Befehle sind vorbereitend – kein direktes Pushen, Löschen oder Rewriting ohne Freigabe.
2. **Versionskontrolle:** Änderungen an diesen Dokumenten nur per PR – kein Direkt-Commit.
3. **Re-Use:** Bei Projekten außerhalb von *Claire de Binaire* müssen Projektname, Branch-Prefix und Secret-Platzhalter angepasst werden.
4. **Nachverfolgung:** Jeder ausgeführte Schritt muss mit Beweislink (CI-Log, Screenshot, Commit-ID) dokumentiert werden.

---

## 🧩 Integration in andere Projekte

Kopiere das gesamte Verzeichnis `docs/runbooks/` oder importiere das ZIP-Bundle:
`cleanroom_runbooks_bundle.zip`.
Anschließend in der README oder CONTRIBUTING-Doku verlinken:

````markdown
Weitere Informationen zur Projekt-Sanitation und Dokumentenkuration findest du unter [docs/runbooks/](../runbooks/).
````

---

**Version:** v1.0.0-cleanroom  
**Erstellt:** 2025-11-12  
**Maintainer:** Project Manager / Dev Lead / Security Lead
