# Navigation / Entry Point / Snapshot Audit (#3995)

Status: Evidence
Issue: #3995
Prerequisite: #3994 / PR #4011 @ `49eb7546`
Date: 2026-07-13
Scope: Docs-only navigation, snapshot freshness, cross-hub links

## Validator architecture (final)

**Decision:** Extend the existing `#3994` engine — no third link-check landscape.

| Component | Role |
|---|---|
| `tools/markdown_link_utils.py` | Shared parsing + offline relative link resolution |
| `tools/validate_readme_links.py` | Single guard engine: git-discovered READMEs + policy `explicit_active_surfaces` |
| `tests/fixtures/readme_link_policy.yaml` | README classification + explicit canon entry points |
| `tools/validate_onboarding_docs.py` | Unchanged semantic onboarding guard (#3233) |
| CI | Unchanged step `python -m tools.validate_readme_links` (now covers canon surfaces too) |
| `make readme-links-guard` | Unchanged target name (backward compatible) |

**Rejected:** Separate `validate_entry_point_links.py` with duplicated discovery/parsing.

## Entry-point inventory (Tier A active)

| Surface | Role |
|---|---|
| `README.md` | GitHub front door + current-main snapshot |
| `docs/index.md` | Docs hub (onboarding guard) |
| `CURRENT_STATUS.md` | Engineering ledger |
| `docs/runbooks/CONTROL_REGISTER.md` | Board/stage SSOT |
| `docs/meta/WORKING_REPO_CANON.md` | Canon matrix |
| `knowledge/CDB_KNOWLEDGE_HUB.md` | Decision hub (non-governance) |
| `agents/AGENTS.md` | Agent bootloader |
| Area READMEs (`services/`, `tests/`, `tools/`, `core/`, `knowledge/`, …) | Tree indexes |

## Drift register (D1–D10)

| ID | Before | After | Status |
|---|---|---|---|
| D1 | README snapshot listed stale clusters (#2535, #1976, …); missing #3994 | Replaced with live `origin/main` clusters (#4011, #4010/#4009, #4007); LR NO-GO preserved | **fixed** |
| D2 | Plain `#1445` / `#2440` issue refs; unlinked ledger pointer | GitHub issue links + linked `CURRENT_STATUS.md` | **fixed** |
| D3 | `CURRENT_STATUS.md` missing #3994/#4011 ledger line | Added DONE_MERGED #3994; #3995 documented OPEN (not merged pre-PR) | **fixed** |
| D4 | `core/README.md` SSOT paths inline-only | Relative markdown links + Navigation block | **fixed** |
| D5 | `tests/`, `tools/`, `knowledge/` READMEs lacked root/docs index return path | Navigation blocks added where parent path missing | **fixed** (runbooks already had `../index.md`) |
| D6 | No link guard for non-README canon surfaces | `explicit_active_surfaces` in readme policy + engine extension | **fixed** |
| D7 | `CONTROL_REGISTER.md` plain issue/path refs | Linked issues + SSOT paths | **fixed** |
| D8 | `CDB_KNOWLEDGE_HUB` snapshot read as quasi-current | Historical banner on hub file blocked by Docs Hub Guard secret-pattern false positives on legacy handoff lines; **historical marking moved to `knowledge/README.md` entry** | **fixed (via knowledge/README)** |
| D9 | Skill-pack catalog inline paths | Documented exception (#3994); no primary nav breakage found | **unchanged (exception)** |
| D10 | #4012 architecture map drift | Out of scope | **deferred → #4012** |

## Documented exceptions

- Archive README trees (`docs/archive/`, `knowledge/archive/`) — `archive_snapshot` class (#3994)
- Fixture/evidence README trees — `fixture_testdata` class (#3994)
- Skill-pack reference tables with illustrative inline paths — not primary navigation

## Non-goals respected

- #4005 community-health rewrites
- #4006 worktree/branch cleanup
- #4012 ARCHITECTURE_MAP / SERVICE_CATALOG
- LR verdict change (remains **NO-GO**)
- Runtime / trading / DB / MCP changes

## Reproduce

```bash
make readme-links-guard
make onboarding-docs-guard
python -m tools.validate_readme_links --inventory
git diff --check
```
