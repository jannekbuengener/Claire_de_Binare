# Session 2026-08-04 — #4153 Campaign-Manifest Slice

## Status

`HOLD_CAMPAIGN_PARAMETER_GRID_UNRESOLVED`

Kein Schema-/Manifest-Commit. Kein PR. Keine Campaign-Ausführung. Kein Merge.
Kein `cdb-local-ci`. LR=`NO-GO`.

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

Bootloader-Fallback:
- `CDB.LOADER_V3.0.md` — nicht im Repo auflösbar
- historische Bezeichnung „Claire MCP Server-9“ — nicht als Datei/Surface auflösbar
- verwendet: `AGENTS.md` / `agents/AGENTS.md`, Cursor `cdb-session-start`,
  Context MCP (`cdb_context_briefing`), Live-GitHub + Repo-Preflight

## Work surface

- Worktree: `D:\Dev\Workspaces\Repos\cdb-wt-4153-campaign-manifest`
- Branch: `batch/validation-research-issue-4153-campaign-manifest` (clean, = `origin/main`)
- Base: `origin/main` @ `301bc757be7cb4162db6db114a5c445f2aca392f`
- Alte Worktrees `#4153` / Campaign-Audit / Exec **nicht** mutiert

## Live verification (PASS side)

| Item | Evidence |
| --- | --- |
| `origin/main` | `301bc757…` (CDB-052 merge; no later commits) |
| #4153 | OPEN |
| #4147 | OPEN |
| #4152 | OPEN (offline replay not blocked; orders/paper/live/echtgeld still banned) |
| #4336 | CLOSED |
| Open #4153 PRs | none |
| Repo preflight | `READY_FOR_REPLAY_SENSITIVITY` (8/8) |
| Parameter-control register FP | `464caa6d3d4e9a28740c6b1dd45c5d2c0bc26dde40e1951db4bbfb6539e76f5e` |
| YAML `canonical_json_sha256` | `d72029e61b591b74eab8e4ad8f12e7581287806a95dbb266dd38b179d4608a94` |
| Effective-Config FP | `87faf4e6332ddb3d2b147bdb6c0bbd60cd0e1a1c25557171a85047d42cc7171d` |
| Window selection SHA | `3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52` |
| Locked windows | 39 / 39 present in local window-bank manifest |
| Per-window content FPs | 39 unique content fingerprints present (local bank) |
| Strategy | `primary_breakout_v1` is the only strategy bound in the readiness fixture / PB1 canon |
| Expansion intent (issue) | OFAT + begrenzte Interaktionsgruppen (nicht Full-Cartesian-Default) |
| CDB-002 / CDB-003 | `RESEARCH_ALLOWED` / `ALLOW_REPLAY_RESEARCH` live verified |

## Parallel scope note (non-blocking for HOLD reason)

Remote branch `origin/batch/validation-research-issue-4153` exists with 3 commits
above main (executable orchestration + invented grid, ~1248 runs). **No open PR.**
Not reused (per session isolation). Not treated as Owner-ratified grid.

## Blocking defect — parameter grid unresolved

Exact missing Owner determinations (cannot invent):

### 1. Parameter dimensions vs register semantics

| Register ID | Exact name | Config fields | Defaults | Register `allowed_range` |
| --- | --- | --- | --- | --- |
| CDB-002 | PB1 Entry-/Exit-Lookback | `entry_lookback_minutes`, `exit_lookback_minutes` | 240 / 120 | `jeweils >0` (no discrete grid) |
| CDB-003 | PB1 Breakout-Buffer und Cooldown | `breakout_buffer`, `min_minutes_between_entries` | 0.0005 / 60 | qualitative only |
| CDB-021 | Scenario Packs | scenario harness | harness defaults | `durch Harness` |

Issue `#4153` lists research variables but **no numeric ranges/steps**.

### 2. Existing non-authoritative designs (must not silently promote)

**A. Synthetic fixture** `tests/fixtures/arvp/sensitivity/experiment_manifest_valid_v1.json`
(`executable:false`, FP `11f62b44…`):

- `pb1_lookback` → CDB-002, range 60–240 step 30 → OFAT≈429 with 39 windows
- `pb1_buffer_cooldown` → CDB-003, range 0.0–0.02 step 0.005 (ratio)
- Conflates entry+exit lookback into one family
- Conflates buffer (ratio) + cooldown (minutes) into one ratio family (**unit mismatch**)
- Readiness doc Non-goal: „No parameter grids“ for the readiness slice

**B. Unmerged exec branch** `batch/validation-research-issue-4153` @ `d643ce90`:

- Splits into entry/exit/buffer/cooldown (+ CDB-021 scenarios)
- Uses `interaction_values` / OFAT steps not present in register or issue
- Declares ~1248 runs; `source_commit`/`register_fp` not bound to `301bc757` / live register
- Includes campaign **orchestration** (out of this manifest-only slice)

**C. Audit arithmetic** 429 (OFAT) vs 1365 (cartesian) assumed design A and is therefore
also non-authoritative until the grid is ratified.

### 3. Required Owner choices before Manifest-GO can proceed

1. **Dimension model:** coarse families (A) vs split PB1 knobs (B) vs other explicit list
2. **Per-dimension discrete values or (min,max,step)** including units
3. **Baseline point** per dimension (defaults above vs custom)
4. **Expansion mode enum:** `baseline_plus_ofat` vs `baseline_plus_ofat_plus_interaction_groups` vs `full_cartesian` vs explicit variant list
5. **Interaction groups:** which family pairs/triples; endpoint-only vs full subgrid
6. **Whether CDB-021 scenario packs are in-scope** for this first executable manifest
7. **`max_run_count` ceiling** after `expected_run_count` is computed from (1)–(5)

Until these are Owner-ratified in issue canon (comment or follow-up contract),
building an executable campaign manifest would invent research values.

## Non-blocking observations (for next slice after grid GO)

- Schema successor still needed: v1 has `executable: const false` and
  `explicit_bans.campaign_execution: const true`
- Prefer v1.1 / if-then so synthetic fixtures stay valid
- SHA binding: bind `correctness_baseline_commit=301bc757…` (immutable Correctness
  baseline) separate from post-merge main tip; preflight must verify ancestry + live FPs
- Dataset binding: 39 content FPs available from local window bank; request FPs need
  runner/provider path (R8) — bind per-window provenance, not synthetic aggregate only
- Manifest-only slice must not import exec-branch orchestrator

## Boundaries

- LR=`NO-GO`
- No campaign runs / no results / no Campaign-GO
- #4152 untouched
- #4153 / #4147 remain OPEN

## Next smallest safe step

Owner comment on `#4153` ratifying items 1–7 above (or a single attached JSON grid
contract). Then resume Manifest-only slice on a clean worktree from live `origin/main`.
