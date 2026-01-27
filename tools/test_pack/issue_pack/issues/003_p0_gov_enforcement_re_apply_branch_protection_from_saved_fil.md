## ISSUE 3 — [P0][GOV][ENFORCEMENT] Re-apply Branch Protection from saved files using Playwright (MCP)
Labels: prio:p0, type:gov, scope:repo, scope:security
Scope:
- Restore branch protection rules for `main`
- Required checks and review requirements
Description:
- Branch protection must be restored from the previously saved configuration.
- Use Playwright via MCP to apply settings through GitHub UI (automation), referencing local saved files.
Implementation Notes:
- Source of truth folder: `D:\Dev\Workspaces\Worktrees\branch-protection files`
- Codex must inspect this folder and translate it into exact GitHub settings
Acceptance Criteria:
- Branch protection for `main` active and matches saved config
- Direct pushes blocked; PR required
- Required checks set and enforced
- Admin bypass disabled or explicitly controlled (document choice)
- A proof artifact is produced: screenshot(s) or exported settings summary in an evidence folder
Dependencies:
- None (but coordinate with CI checks from Issue 4)

---
