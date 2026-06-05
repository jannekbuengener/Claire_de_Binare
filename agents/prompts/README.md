# Agent prompts (`agents/prompts/`)

Historische und rollenspezifische Prompt-Vorlagen (Codex, Gemini, Claude, Meta-Planung). **Kein** kanonischer Agent-Bootloader.

## SSOT boundary

| Thema | Kanon |
|---|---|
| Agent-Registry, Read Order | [`agents/AGENTS.md`](../AGENTS.md) |
| Rolle Cursor/Claude | [`agents/roles/CLAUDE.md`](../roles/CLAUDE.md) |
| Rolle Codex | [`agents/roles/CODEX.md`](../roles/CODEX.md) |
| Session-Skills | [`.cursor/skills/README.md`](../../.cursor/skills/README.md) |

Prompts hier sind Arbeitskopien; bei Widerspruch gilt `agents/AGENTS.md` und die jeweilige Rollendatei.

## Inhalt (Auswahl)

| Datei | Zweck |
|---|---|
| `PROMPT_CODEX.md` / `PROMPT_CODEX.txt` | Codex-Arbeitsprompt |
| `Prompt_GEMINI_*.md` | Gemini-Varianten |
| `Prompt_CLAUDE_Durchsetzbarkeit.md` | Claude-Durchsetzbarkeit |
| `Meta_Template_Planungs_Prompt.md` | Planungs-Meta-Template |

## Related

- [`agents/HV/README.md`](../HV/README.md) — High-Voltage Multi-Agent Engine (separater Scope)
