# CDB Skill-Meta Schema v1

Status: kanonischer Vertrag fuer optionale Skill-Metadaten
Scope: neue und erweiterte CDB Domain-Skills unter `docs/skills/<name>/`
Referenz-Implementierung: `docs/skills/gh-fix-ci/` (`META.yaml`, `evals.json`)

## 1. Zweck

`SKILL.md` ist der ausfuehrbare Skill-Inhalt und bleibt die kanonische
Quelle fuer Agenten-Anweisungen. `META.yaml` und `evals.json` sind
**optionale Metadaten** im selben Canon-Verzeichnis:

| Artefakt | Rolle |
|---|---|
| `SKILL.md` | Ausfuehrbare Anweisungen, Workflows, Guardrails |
| `META.yaml` | Maschinenlesbare Metadaten (Name, Version, Dateien, Invocation) |
| `evals.json` | Manuelle oder halbautomatische Eval-Hinweise (kein CI-Runner in v1) |

Surface-Adapter (`.opencode/`, `.cursor/`, `.codex/`, `.claude/`) spiegeln
**nur `SKILL.md`**. Meta-Artefakte bleiben canon-only, ausser ein spaeterer
expliziter Slice verlangt etwas anderes. Siehe
[`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) §8.1 und §16.

## 2. Wann Meta-Artefakte nutzen

Pflicht: **nein** — die meisten CDB-Skills brauchen nur `SKILL.md`.

Empfohlen, wenn mindestens eines zutrifft:

- Der Skill hat ein ausfuehrbares Script oder CLI-Einstieg.
- Evals oder Smoke-Checks sollen dokumentiert werden.
- Abhaengigkeiten (`gh`, `python`, Container) muessen maschinenlesbar sein.
- Mehrere Maintainer oder Versionen brauchen klare Metadaten.

Nicht noetig fuer reine Prompt-/Workflow-Skills ohne ausfuehrbare Artefakte.

## 3. Verzeichnislayout

```text
docs/skills/<skill-name>/
  SKILL.md          # Pflicht (kanonisch, wird gespiegelt)
  META.yaml         # Optional (canon-only)
  evals.json        # Optional (canon-only)
  scripts/          # Optional (canon-only, falls Skill Scripts hat)
```

Starter-Templates: [`_templates/META.yaml`](_templates/META.yaml),
[`_templates/evals.json`](_templates/evals.json).

## 4. `META.yaml` — Pflicht- und optionale Felder

### 4.1 Pflicht (v1)

| Feld | Typ | Beschreibung |
|---|---|---|
| `skill_name` | string | Kurzname, gleich Ordnername unter `docs/skills/` |
| `version` | string | Semver (`MAJOR.MINOR.PATCH`) |
| `status` | string | `active`, `deprecated`, oder `draft` |
| `description` | string (block) | Ein-Satz-Zusammenfassung des Skills |
| `canonical_location` | string | Pfad zum Canon-Verzeichnis, z. B. `docs/skills/<name>/` |

### 4.2 Empfohlen

| Feld | Typ | Beschreibung |
|---|---|---|
| `created` | date (`YYYY-MM-DD`) | Erstanlage |
| `last_updated` | date | Letzte inhaltliche Aenderung |
| `maintainer` | string | Verantwortlicher Owner |
| `files` | list[string] | Dateien im Skill-Verzeichnis (inkl. `SKILL.md`) |
| `invocation.default` | string | Primaerer Aufruf (Befehl oder Slash) |
| `invocation.examples` | list | Named examples mit `command` + `description` |
| `dependencies.required` | map | Tool-Versionen (`gh`, `python`, …) |
| `dependencies.optional` | map | Optionale Tools |
| `safety_rules` | list[string] | Kurze Guardrails (kein Auto-Merge, kein Live-Go, …) |
| `tags` | list[string] | Discovery-Tags |

### 4.3 Optional / skill-spezifisch

Weitere Abschnitte sind erlaubt (z. B. `exit_codes`, `features`, `references`,
`changelog`), solange sie skill-spezifisch bleiben und `SKILL.md` nicht
ersetzen. `gh-fix-ci` zeigt ein erweitertes Beispiel.

### 4.4 Nicht in META.yaml

- Keine Secrets, Tokens oder Pfade zu Credential-Dateien.
- Keine LR-/Live-/Echtgeld-Freigaben.
- Keine Duplikation des vollen Skill-Workflows aus `SKILL.md`.

## 5. `evals.json` — Mindeststruktur

Evals sind **Dokumentation und manuelle Pruefhinweise**, kein CI-Contract in v1.

### 5.1 Top-Level

| Feld | Pflicht | Beschreibung |
|---|---|---|
| `skill_name` | ja | Gleich `META.yaml` / Ordnername |
| `version` | ja | Gleich `META.yaml` |
| `evals` | ja | Liste von Eval-Eintraegen (kann leer `[]` sein fuer reine Docs-Skills) |

### 5.2 Eval-Eintrag (minimal)

| Feld | Pflicht | Beschreibung |
|---|---|---|
| `name` | ja | Kurz-ID (`snake_case`) |
| `description` | ja | Was geprueft wird |

Mindestens eines von:

| Feld | Beschreibung |
|---|---|
| `command` | Shell-Befehl fuer manuellen Lauf |
| `note` | Rein dokumentarischer Hinweis ohne ausfuehrbaren Befehl |

Optional: `expected_exit_code`, `expected_output_contains`,
`expected_output_json_fields`, `skip_reason`, `mock_*` Felder fuer
dokumentierte Unit-Test-Muster (siehe `gh-fix-ci`).

### 5.3 Non-goals (evals v1)

- Kein automatischer Eval-Runner in CI (separater Slice noetig).
- Keine Live-Trading- oder Produktiv-DB-Tests.
- Keine Secrets in Commands oder erwarteten Outputs.

## 6. Neuanlage-Workflow (Kurz)

1. `docs/skills/<skill-name>/SKILL.md` anlegen (kanonisch).
2. Optional: `_templates/META.yaml` und `_templates/evals.json` kopieren und
   anpassen.
3. Surface-Adapter-Header setzen und `SKILL.md` spiegeln (Registry §7–§8).
4. `python tools/validate_skill_surface_mirror.py` bis `PASS`.
5. Registry-Eintrag und `AGENTS.md`-Pointer bei Bedarf.

Vollstaendiger Workflow: [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) §9.

## 7. Update- und Deprecation-Regeln

- `SKILL.md`-Aenderungen: Adapter re-mirroren (Drift-Guard).
- `META.yaml` / `evals.json`: nur Canon aktualisieren; `last_updated` und
  `version` in `META.yaml` anheben bei inhaltlicher Aenderung.
- Bei Deprecation: `status: deprecated` in `META.yaml`, `DEPRECATION.md`
  gemaess Registry §11.

## 8. Referenzen

- [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) — SSOT fuer Surfaces
- [`gh-fix-ci/META.yaml`](gh-fix-ci/META.yaml) — erweiterte Referenz
- [`gh-fix-ci/evals.json`](gh-fix-ci/evals.json) — erweiterte Eval-Referenz
- [`cdb-drift-reconcile/SKILL.md`](cdb-drift-reconcile/SKILL.md) — Mirror-Drift
