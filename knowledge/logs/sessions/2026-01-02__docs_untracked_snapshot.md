# Untracked Files Snapshot - 2026-01-02

**Branch:** main
**Date:** 2026-01-02

## Untracked Files List
(See git status output)

## Classification Plan

| File/Pattern | Bucket | Action | Rationale |
|---|---|---|---|
| `.worktrees/` | GENERATED | Ignore | Worktree metadata |
| `.claude_settings.json` | LOCAL | Ignore | Local settings |
| `configs/` | LOCAL | Ignore | Local configs |
| `copilot*.txt` | LOST-KNOWLEDGE | Archive | Context/Instructions |
| `verlosung/*.crt` | SENSITIVE | Quarantine/Delete | Potential certs (public but treat as sensitive per policy) |
| `verlosung/*.yml` | DUPLICATE | Delete | Ops pack copies (merged in Slice B) |
| `knowledge/logs/*` | DOCS-OK | Add | Session logs |
| `knowledge/archive/*` | DOCS-OK | Add | Archived knowledge |
| `tools/cdb.psm1` | CODE | Delete | Code in Docs Repo |
| `Branch Aufräumen Roadmap.md` | DOCS-OK | Move | Roadmap |
| `Governance-Audit Roadmap.md` | DOCS-OK | Move | Roadmap |
| `Textdokument (neu).txt` | LOST-KNOWLEDGE | Archive | Current instructions |
| `cdb_docs_index.yaml` | DOCS-OK | Add | Index file |
