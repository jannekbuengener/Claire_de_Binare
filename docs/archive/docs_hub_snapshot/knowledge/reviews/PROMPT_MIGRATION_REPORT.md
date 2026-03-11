---
type: migration_report
date: 2025-12-17
issue: "#118"
status: completed
---

# Prompt Migration Report: .txt → .md

## Summary
All `.txt` prompt and tasklist files have been successfully migrated to `.md` format with proper frontmatter.

## Migrated Files

### Prompts (agents/prompts/)
| Original File | New File | Agent | Status |
|---------------|----------|-------|--------|
| `Meta Template Planungs Prompt (huge).txt` | `Meta_Template_Planungs_Prompt.md` | UNKNOWN | ✅ Migrated |
| `Prompt CLAUDE - Durchsetzbarkeit.txt` | `Prompt_CLAUDE_Durchsetzbarkeit.md` | CLAUDE | ✅ Migrated |
| `Prompt Gemini - Konsistenz.txt` | `Prompt_GEMINI_Konsistenz.md` | GEMINI | ✅ Migrated |
| `Prompt Gemini - Strukturierung.txt` | `Prompt_GEMINI_Strukturierung.md` | GEMINI | ✅ Migrated |
| `PROMPT_CODEX.txt` | `PROMPT_CODEX.md` | CODEX | ✅ Migrated |

### Tasklists (agents/tasklists/)
| Original File | New File | Status |
|---------------|----------|--------|
| `2TASK-LISTcopilot.txt` | `TASK_LIST_Copilot_02_Legacy.md` | ✅ Migrated (deprecated) |
| `3TASK-LISTcopilot.txt` | `TASK_LIST_Copilot_03_Legacy.md` | ✅ Migrated (replaced by Issue #124) |

## Actions Taken

1. **Created 5 new .md prompt files** with standardized frontmatter:
   ```yaml
   ---
   role: prompt
   agent: <AGENT_NAME>
   status: migrated
   source: <original_filename>
   ---
   ```

2. **Created 2 legacy tasklist .md files** documenting the deprecated content

3. **Marked all original .txt files as DEPRECATED** with clear migration notices

4. **No changes to DOCS_HUB_INDEX.md** - already marked `.txt` files as deprecated

## Frontmatter Schema
All migrated files follow this structure:
- `role`: Type of document (prompt/tasklist)
- `agent`: Target agent (CLAUDE/GEMINI/CODEX/COPILOT/UNKNOWN)
- `status`: Migration status (migrated/deprecated)
- `source`: Original filename for traceability
- `replaced_by`: (optional) Replacement file/issue reference

## Acceptance Criteria
- ✅ Every `.txt` has corresponding `.md` file
- ✅ Original `.txt` files preserved with deprecation notice
- ✅ Index already references deprecated status (no update needed)
- ✅ All content preserved 1:1 (no rewriting)

## Notes
- **Meta Template file**: Agent classification is "UNKNOWN" - requires manual review to determine if it's for a specific agent or shared
- **Tasklist 02 & 03**: Legacy files replaced by current COPILOT_TASKLIST_01-06.md series
- **Root-level files**: No `copilot.txt` or `gemini.txt` found at root level (already removed)

## Next Steps
1. Commit changes to Docs Hub
2. Update Issue #118 status to "Done"
3. Begin Issue #119 (Büro-Files Scan)

---
**Issue:** #118  
**Completed:** 2025-12-17T00:44:40Z  
**Agent:** Copilot (GitHub Manager)
