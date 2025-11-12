# Cleanroom Cleanup Plan

## Scope Matrix
| Kategorie | Anzahl | Beispielpfade | Bemerkung |
|-----------|--------|---------------|-----------|
| 🔵 Core | 37 | backoffice/services/signal_engine/service.py, compose.yml | Laufzeitkritische Services & Orchestrierung |
| 🟢 Supporting | 296 | backoffice/docs/ARCHITEKTUR.md, scripts/run_hardening.py | Stützen Betrieb, Tests, Doku |
| 🟡 Legacy | 24 | archive/legacy_quickstart/QUICK_START.md, backoffice/SESSION_MEMO_* | Historische Referenzen, zu kuratieren |
| 🔴 Obsolete | 37 | artifacts/security/gitleaks_report.json, .coverage, tmp_metrics.ps1 | Build-/Scan-Artefakte, Caches |
| ⚠️ SecretDetected | 3 | .env, postgres_env.txt, postgres_env_runtime.txt | Sofortige Sanitation nötig |

## Maßnahmenübersicht
| Phase | Pfad(e) | Kategorie | Aktion | Begründung | Quelle |
|-------|---------|-----------|--------|------------|--------|
| Phase 1 – Analyse | .env, postgres_env*.txt | ⚠️ SecretDetected | Secret-Exposure erfassen, Owner identifizieren | Hardcodierte Zugangsdaten im Repo | Inventur `.env`, `postgres_env.txt`, `postgres_env_runtime.txt` |
| Phase 1 – Analyse | backoffice/services/**/requirements.txt | 🔵 Core | Abhängigkeitsmatrix erstellen | Mehrfach gepflegte Requirements erzeugen Drift | Inventur `backoffice/services/*/requirements.txt` |
| Phase 2 – Planung | artifacts/**, backoffice/artifacts/** | 🔴 Obsolete | Git-Ignorierung vorbereiten, Löschstrategie definieren | Build-/Test-Artefakte, nicht versionswürdig | Inventur `artifacts/…`, `backoffice/artifacts/…` |
| Phase 2 – Planung | tests/__pycache__/**, src/__pycache__/** | 🔴 Obsolete | Cache-Pfade in .gitignore aufnehmen | Automatisch generierte Bytecode-Dateien | Inventur `tests/__pycache__/…`, `src/__pycache__/…` |
| Phase 3 – Umsetzung | backoffice/docs/**, archive/** | 🟢/🟡 | Konsolidierung in neue Doc-Struktur | Redundante/Legacy-Doku zentralisieren | Inventur `backoffice/docs/**`, `archive/**` |
| Phase 3 – Umsetzung | scripts/tmp_* & tmp_*.txt | 🔴 Obsolete | Temporäre Utilities archivieren oder entfernen | Einmalige Reports/Skripte, nicht mehr benötigt | Inventur `tmp_compose_report.txt`, `tmp_metrics.ps1`, `tmp_metrics_report.txt` |
| Phase 4 – Validierung | docker/*.yml, compose.yml, tests/** | 🔵/🟢 | Build/Test-Run nach Bereinigungen | Sicherstellen, dass keine Regression entsteht | Inventur `compose.yml`, `docker-compose.yml`, `tests/…` |
| Phase 5 – Delete | artifacts/**, backoffice/artifacts/**, .coverage, tmp_* | 🔴 Obsolete | Finales Entfernen nach Review | Dateien reine Artefakte, regenerierbar | Inventur (siehe Löschkandidatenliste) |
| Phase 5 – Delete | mhutchie.git-graph-1.30.0.vsix | 🟡 Legacy | Entfernen/nicht versionieren | Editor-Extension, groß, nicht laufzeitrelevant | Inventur `mhutchie.git-graph-1.30.0.vsix` |

## Löschkandidaten (Phase 5)
- artifacts/** – CI/Security/Runtime-Artefakte (Inventur `artifacts/...`)
- backoffice/artifacts/** – Service-Artefakte, mehrfach vorhanden (Inventur `backoffice/artifacts/...`)
- .coverage – Einzeldatei Coverage-Dump (Inventur `.coverage`)
- tmp_compose_report.txt, tmp_metrics.ps1, tmp_metrics_report.txt – Temporäre Reports/Skripte (Inventur `tmp_*`)
- tests/__pycache__/**, src/__pycache__/** – Python-Bytecode (Inventur `__pycache__`)
- mhutchie.git-graph-1.30.0.vsix – Eingebettete Editor-Erweiterung (Inventur `mhutchie.git-graph-1.30.0.vsix`)

## Risiken
- Verlinkungen auf verschobene Doku brechen (README, Service-Dokumente).
- Build-/Test-Skripte könnten implizit Artefakte erwarten (z. B. Pfad-Lokalitäten).
- False Positives beim Identifizieren von Legacy-Dateien (SESSION_MEMO ggf. noch aktiv).

## Akzeptanzkriterien
- Jede Maßnahme enthält Pfad, Kategorie, Begründung und Inventur-Quelle.
- Secrets werden nicht im Klartext wiedergegeben.
- Phase-5-Aktionen erst nach vorangehenden Phasen freigegeben.
- Plan genehmigt durch Projektowner, bevor Dateien angefasst werden.
