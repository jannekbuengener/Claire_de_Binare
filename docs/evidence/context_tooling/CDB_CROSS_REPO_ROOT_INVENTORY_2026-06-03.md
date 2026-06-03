# Cross-repo root and GitHub target inventory — 2026-06-03

Status: Evidence artifact (Issue **#2853**, parent **#2847**)  
Boundaries: Read-only discovery; no repo cloning; no productive DB/MCP writes; LR **NO-GO**

---

## Canonical source

| Item | Path |
|------|------|
| Inventory config (SSOT) | `infrastructure/config/mcp/cross_repo_root_inventory.json` |
| Builder + CLI | `tools/mcp/cross_repo_root_inventory.py` |
| Harness attachment | `tools/surrealdb/context_live_invocation_harness.py` |
| Certification gate | `tools/surrealdb/context_certify.py` (`cross_repo_root_inventory`) |

Regenerate operator table:

```bash
python -m tools.mcp.cross_repo_root_inventory --format markdown
make context-root-inventory
```

Optional GitHub reachability (read-only `gh repo view`, no clone):

```bash
python -m tools.mcp.cross_repo_root_inventory --format json
```

---

## Operator machine snapshot (2026-06-03)

Working repo: `D:/Dev/Workspaces/Repos/Claire_de_Binare` @ `origin/main`  
Workspaces sibling dir: `D:/Dev/Workspaces/Repos`

| key | local_status | local_path | github_slug | github_target_status | required |
|-----|--------------|------------|-------------|----------------------|----------|
| working | OK | `.` | jannekbuengener/Claire_de_Binare | OK (when gh available) | yes |
| db | OK | `tools/surrealdb` | same as working | same as working | yes |
| mcp | OK | `tools/mcp` | same as working | same as working | yes |
| config | OK | `claire-de-binare.mcp.json`, `pyproject.toml` | same as working | same as working | yes |
| traumtaenzer | OK | sibling `TraumTaenzer` | jannekbuengener/TraumTaenzer | OK (when gh available) | no |
| sample_brain | MISSING | — | jannekbuengener/sample_brain | not cloned locally | no |
| gpt_mcp_server | MISSING | — | jannekbuengener/gpt-mcp-server | not cloned locally | no |

**roots_verdict:** `pass_with_limits` when optional external repos are absent locally.  
**Fail-closed:** required roots (`working`, `db`, `mcp`, `config`) with `local_status != OK` → `roots_verdict=fail` and harness/certify blocking.

---

## Reconciliation with benchmark / preflight

| Surface | Before #2853 | After #2853 |
|---------|----------------|---------------|
| `CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md` | Ad-hoc markdown table | Same facts; machine table from inventory command |
| `context_live_invocation_harness` | Tool matrix only | Adds `root_inventory` block; fails if required root missing |
| `context_certify` | MCP/registry gates only | Adds `cross_repo_root_inventory` gate |
| Nav `REPO.map.json` | In-repo roots only | Unchanged; cross-repo SSOT is `cross_repo_root_inventory.json` |

---

## Limitations and recheck trigger

- No cloning or private-repo fetch without operator GO.
- `github_target_status` for MISSING local paths does **not** imply local PASS.
- Re-run inventory after: cloning `sample_brain` / `gpt-mcp-server`, moving working repo, or changing `CDB_WORKSPACES_REPOS`.
- Security alert scope (#2860–#2869) and epic #2289/#2513 explicitly out of scope.

---

## Validation (implementation slice)

- `pytest -q tests/unit/tools/mcp/test_cross_repo_root_inventory.py`
- `pytest -q tests/unit/tools/mcp/ -m unit`
- Targeted harness/certify unit tests as needed

Refs **#2853**, **#2847**.
