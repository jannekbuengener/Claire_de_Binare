# Copilot Tasklist – PR-basierte Umsetzung (Ultra-kurz)

Diese Tasklists sind **deterministisch**, **session-unabhängig** und **PR-spezifisch**.  
Regeln:  
- Kein Architekturumbau  
- Kein Knowledge-Hub-Write  
- Max. 300 LOC pro PR  
- Bei Unsicherheit: markieren, nicht entscheiden  

---

## PR-01 – CI-Guard (Core-Duplikate verhindern)

- Erstelle CI-Script (bash oder python)
- Prüfe verbotene Pfade:
  - services/**/core/**
  - doppelte secrets.py
- Exit != 0 bei Fund
- Klare Fehlermeldung (Pfad + Regel)
- Script unter scripts/ oder tools/
- Keine bestehende CI ändern
- Snippet + kurze Erklärung ausgeben

---

## PR-02 – Repo-Hygiene (Safe Deletes)

- Lösche *.backup Dateien
- Lösche *.skip Dateien
- Entferne service-lokale core/__init__.py (Duplikate)
- KEINE Logikdateien anfassen
- Nach Löschung: Import-Test lokal
- Ergebnis dokumentieren (kurz)

---

## PR-03 – Makefile Bugfix

- Korrigiere falsche backoffice/ Pfade
- Setze infrastructure/scripts/ korrekt
- Keine neuen Targets hinzufügen
- make test / make test-unit prüfen
- Diff minimal halten

---

## PR-04 – Unit-Test-Skeletons (Host-only)

- Lege Test-Dateien unter tests/unit/ an
- Nur Import- & Smoke-Tests
- Nutze conftest.py für PYTHONPATH
- Keine externen Services mocken
- pytest lokal lauffähig
- Keine Coverage-Ziele erzwingen

---

## PR-05 – Docker-Compose Dev/Base Split

- Entferne Bind-Mounts aus Base
- Ports nur in dev override
- read_only + Bind-Mount Konflikte lösen
- Network prod: internal=true
- Keine neuen Services hinzufügen
- Nur YAML-Änderungen

---

## PR-06 – Replay-Enabler (optional, klein)

- Clock-Interface vorbereiten (Spec-only oder minimal)
- Random-Seed via ENV vorbereiten
- Keine Business-Logik ändern
- Tools nur als Platzhalter
- Fokus: Vorbereitung, nicht Vollimplementierung

---

Ende der Tasklist.
