# CDB Skills (`/docs/skills/`)

Status: kanonische Skill-Flaeche (siehe `SKILL_SURFACE_REGISTRY.md`).

`docs/skills/` ist die **Single Source of Truth** fuer CDB-Skills.
Alle anderen Surface-Pfade (`.opencode/`, `.cursor/`, `.codex/`,
`.claude/`) sind Mirror-Adapter und muessen gegen diese Dateien
synchron gehalten werden.

## Kanonische Skill-Dateien

| Skill | Pfad | Eingefuehrt |
|---|---|---|
| `gh-fix-ci` | [`gh-fix-ci/SKILL.md`](gh-fix-ci/SKILL.md) | bestehend |
| `cdb-github-api-ops` | [`cdb-github-api-ops/SKILL.md`](cdb-github-api-ops/SKILL.md) | PR #3569 |

## Registry

- [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md): verbindliche
  Definition der kanonischen Flaeche, der Surface-Adapter-Typen und
  der Drift-Regeln.

## Neue Skills

Bitte zuerst in `docs/skills/<skill-name>/SKILL.md` anlegen, dann auf
die Surfaces spiegeln. Workflow-Details siehe Registry, Abschnitt 9.

## Anti-Pattern

- Do NOT Skills direkt in `.opencode/`, `.cursor/`, `.codex/`,
  `.claude/` ohne kanonische Datei in `docs/skills/` anlegen.
- Do NOT Mirror-Kopien ohne Pflicht-Header aus Registry, Abschnitt 7.

## Related Surfaces

OpenCode: [`.opencode/skills/README.md`](../../.opencode/skills/README.md)
Cursor: [`.cursor/skills/README.md`](../../.cursor/skills/README.md)
Codex: [`.codex/cdb_skills/README.md`](../../.codex/cdb_skills/README.md)
Claude: [`.claude/skills/`](../../.claude/skills/)
Registry: [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md)
