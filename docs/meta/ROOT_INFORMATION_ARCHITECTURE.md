# Root Information Architecture

Status: Canonical

Scope: tracked repository root

Decision date: 2026-07-15

## Ziel

Der Repository-Root bleibt eine kleine Front-Door für Quellcode, Betrieb,
Konfiguration, Dokumentation und bewusst gewählte Einstiegspunkte. Fachliche
Unterlagen, Laufnachweise und bereichsspezifische Konfiguration liegen in ihren
jeweiligen Unterordnern. Neue Root-Einträge benötigen eine explizite Ergänzung
des maschinenlesbaren Vertrags in
[`config/repository/root_layout.json`](../../config/repository/root_layout.json).

## Entscheidungsmatrix

| Ehemaliger Root-Eintrag | Befund | Entscheidung | Kanonisches Ziel |
|---|---|---|---|
| `config` (Datei ohne Endung) | Veraltete Emoji-Konfiguration ohne aktive Consumer; `.github/emoji-config.yaml` ist CI-aktiv | Löschen | `.github/emoji-config.yaml` |
| `evidence-run/` | Zwei versionierte Laufnachweise | Verschieben | `docs/evidence/runtime-runs/`; neue Runs nach `artifacts/evidence-runs/` |
| `examples/` | Zwei LR-Contract-Beispiele | Verschieben | `docs/contracts/examples/` |
| `governance/` | Mischung aus CI-Gate, Readiness-Konfiguration, Policy-Duplikat und historischem Prozess | Aufteilen | `.github/governance/`, `config/live-readiness/`, `knowledge/governance/`, `docs/archive/governance/` |
| `k8s/` | Unvollständiges Platzhalter-Skelett, Placeholder-Image, veralteter Port, keine aktive Deployment-/CI-Nutzung; Issue #293 geschlossen | Löschen | Entscheidungsstand in `knowledge/decisions/K8S_BUDGET_DECISION.md` |
| `manifests/` | Aktive ARVP-Kampagnen- und Compose-Override-Konfiguration | Verschieben | `config/arvp/` |
| `mcp_navpack_claire_de_binare_repository/` | Aktive Navigationshilfe, kein eigener Produktbereich | Verschieben | `docs/navigation/mcp-navpack/` |
| `reports/` | Versionierte historische Reports und Evidence | Verschieben | `docs/evidence/reports/`; neue Reports nach `artifacts/reports/` |

## Bewusst im Root verbleibende Verzeichnisse

| Bereich | Begründung |
|---|---|
| `core/`, `services/` | Produktiver Source-Code und Laufzeitmodule |
| `infrastructure/` | Aktive Compose-, Datenbank-, Monitoring-, TLS- und Deployment-Oberfläche; kein Dokumentenablageordner |
| `tests/` | Repo-weite Verifikation |
| `tools/`, `scripts/` | Repo-weite Automatisierung und Operator-Werkzeuge |
| `ci/` | Lokale Docker-CI Phase-1 Ausführungsschicht und Evidence (`ci/artifacts/`) |
| `config/` | Bereichsübergreifende, versionierte Konfiguration ohne eigenen Runtime-Owner |
| `docs/`, `knowledge/`, `agents/` | Dokumentation, Canon/Entscheidungen und Agentensteuerung |
| `artifacts/` | Kanonische Zieloberfläche für erzeugte, standardmäßig nicht versionierte Ausgaben |
| `third_party/` | Explizit vendorte externe Abhängigkeiten |
| `.github/` und Agent-/IDE-Dot-Verzeichnisse | Tool-native Konfiguration an den von den Tools erwarteten Pfaden |

`infrastructure/` bleibt damit ausdrücklich im Root. Würde Kubernetes später
freigegeben, wären ausführbare Deploy-Artefakte nach neuem Issue und Human-GO
unter `infrastructure/k8s/` anzulegen. Knowledge dokumentiert die Entscheidung,
ist aber kein Ziel für ausführbare Manifeste.

## Evidence- und Output-Regel

- `docs/evidence/`: geprüfte, redigierte und bewusst versionierte Nachweise.
- `artifacts/`: neu erzeugte Reports, Laufdaten und lokale/CI-Ausgaben.
- Eine Übernahme von `artifacts/` nach `docs/evidence/` ist eine explizite
  Dokumentationsänderung; Generatoren schreiben nicht direkt in den Docs-Canon.
- Root-Verzeichnisse wie `reports/` oder `evidence-run/` dürfen nicht neu entstehen.

## Schutzmechanismus

```bash
python -m tools.validate_root_layout
make root-layout-guard
```

Der Guard wertet ausschließlich von Git verfolgte Pfade aus. Lokale temporäre
Dateien werden weiterhin durch `.gitignore`, Session-Hygiene und Pre-Close-Checks
behandelt. Eine neue fachliche Top-Level-Fläche muss zuerst in dieser Architektur
begründet und anschließend in `root_layout.json` freigegeben werden.
