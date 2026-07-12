# README Link Inventory Evidence (#3994)

Status: Evidence
Issue: #3994
Date: 2026-07-12
Scope: README link validation and minimal navigation reconcile only

## Summary

- Tracked `README.md` files are discovered via `git ls-files` (automatic).
- Classification uses rule-based policy in
  [`tests/fixtures/readme_link_policy.yaml`](../../tests/fixtures/readme_link_policy.yaml)
  — not a manual per-file list.
- Active README surfaces are validated offline by
  [`tools/validate_readme_links.py`](../../tools/validate_readme_links.py).
- Shared link helpers live in
  [`tools/markdown_link_utils.py`](../../tools/markdown_link_utils.py) and are
  reused by [`tools/validate_onboarding_docs.py`](../../tools/validate_onboarding_docs.py)
  (#3233 semantics preserved).

## Inventory (reproduce)

```bash
python -m tools.validate_readme_links --inventory
```

Expected classification buckets:

| Class | Rule |
|---|---|
| `active` | Default — all paths not matching a skip prefix |
| `archive_snapshot` | `docs/archive/`, `knowledge/archive/` |
| `fixture_testdata` | `tests/fixtures/`, `artifacts/`, `reports/p5_canary/` |

New untracked-class README paths default to `active` (fail-closed validation).

## Link corrections delivered

| File | Fix |
|---|---|
| `.gemini/README.md` | `../GEMINI.md`, `../agents/AGENTS.md` |
| `.vscode/README.md` | `../AGENTS.md`, `../docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md` |
| `docs/onboarding/core-eventflows/README.md` | `../../../` depth for repo-root targets (7 links) |
| `tools/evidence_harvester/README.md` | `../../docs/evidence/...` |
| `tools/paper_trading/README.md` | `../../services/risk/README.md` |
| `README.md` | Canonical entrypoint list + navigation block linked |
| `knowledge/README.md` | Key entry points linked |
| `services/README.md` | Navigation block + compose README link |

## Documented exceptions

- Archive/snapshot README trees: classified `archive_snapshot`, not link-guarded.
- Fixture/evidence README trees: classified `fixture_testdata`, not link-guarded.
- Skill-pack catalog READMEs: reference tables left as inline code where paths
  are illustrative, not primary navigation chains.

## Non-goals (#3995, #4005, #4006)

- No snapshot/CURRENT_STATUS reconcile (#3995).
- No community-health file rewrite (#4005).
- No worktree/branch cleanup (#4006).
- No historical archive content modernization.

## Safety

- LR remains **NO-GO**; no runtime, trading, DB, MCP, or live-capital changes.
