# CDB Security Alert Wave 4350-4359 — Grafana 13.1.2 upstream bump + zipkin plugin hold

Status: EVIDENCE (repo canon, mirrors the machine-readable JSON at
`CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.json`).
LR verdict: NO-GO. Board stage: `trade-capable` (orthogonal, not a live gate).

## 1. Scope and safety boundaries

- Wave issues: `#4350` – `#4359` (all HIGH GitHub Code Scanning alerts, tool Trivy).
- Related tracker candidates: parent `#2513`, existing Grafana cluster
  tracker `#2933`, prior Zipkin plugin tracker `#2292` (retained for lineage
  only; not scope-expanded).
- Explicitly out of scope: the 13 additional capped Security Alert Readout
  candidates from `2026-08-05` (workflow_run `30990577816`); this wave does
  not remediate or mutate those issues.
- Forbidden and not used in this wave: alert dismissal, security exceptions,
  `.trivyignore` growth, admin-merge bypass, runtime/productive mutation,
  live/echtgeld authorization, foreign-worktree edits, takeover of unrelated
  open PRs (`#4348`, `#4349`, `#4347`, `#4345`).

## 2. Bootloader and Read-Order (evidence)

Context Brain preflight was attempted through the local
`project-0-Claire_de_Binare-cdb_context` MCP server. The available
`cdb_context_briefing` tool returned no records for this task ID and no
evidence, claim, decision or memory records for the wave. Trust level is
therefore `none`; the correct classification under the CDB Fallback
Classification Matrix is `insufficient_evidence`, not `unavailable`. Full
Brain Evidence block is at the bottom of this file (§ 12).

Read-Order files consulted (from `agents/AGENTS.md`):

- `knowledge/governance/CDB_CONSTITUTION.md`
- `knowledge/governance/CDB_GOVERNANCE.md`
- `knowledge/governance/CDB_AGENT_POLICY.md`
- `knowledge/governance/SYSTEM_INVARIANTS.md`
- `docs/meta/REPOSITORY_CANON.md`
- `CURRENT_STATUS.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `agents/OPEN_CODE_AGENTS.md`

Security canon and skills read for this wave:

- `docs/security/TRIAGE_RUNBOOK.md`
- `docs/runbooks/merge_policy_ci_gate.md`
- `.cursor/skills/cdb-session-start/SKILL.md`
- `.cursor/skills/cdb-pr-router/SKILL.md`
- `.cursor/skills/cdb-pr-completeness-review/SKILL.md`
- `.cursor/skills/cdb-batch-merge-conductor/SKILL.md`
- `.cursor/agents/cdb-security-triage.md`

Prior evidence relevant to this wave:

- `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3065-3070-CVE-42504_2026-06-08.md`
  — CVE-2026-42504 root cause = Go stdlib rebuild required; UPSTREAM_BLOCKED.
- `docs/evidence/security/CDB_SECURITY_GRAFANA_3764_CVE-42504_VERIFY_2026-07-06.md`
  — 13.0.3 → 13.1.0 did NOT clear CVE-2026-42504; the same class of
  finding is now re-verified against `13.1.1` (still present) and `13.1.2`
  (still present on the zipkin + elasticsearch plugin paths).
- `docs/evidence/security/CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.md`
  — kin-openapi + prometheus x/text wave classification pattern reused here.
- `docs/evidence/security/CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.md`
  — canonical cluster tracker convention (Grafana upstream = `#2933`).

## 3. Live GitHub / repo state at start of wave

- `origin/main` tip: `42b9703c276c5f49810247ceea6b1442a6158ee2` (Grafana
  `13.1.1-ubuntu` era; PR `#4162` merged before this wave in commit
  `4608aeff96ad9832a0335ab55676eea70021ae44`).
- All ten wave issues (`#4350` – `#4359`) are `OPEN` on `main` at wave start,
  labeled `security` + `codeql`, with the ten Code Scanning alerts still
  `open` and fingerprint-matched to the ten issue bodies. No wave issue is
  already closed and no wave issue has a linked closing PR yet.
- Open PRs not overlapping this wave (kept untouched):
  - `#4348` (dependabot / requirements)
  - `#4349` (dependabot / dev requirements)
  - `#4347` and `#4345` (unrelated CI / infra work)
- Related recently merged PRs (kept for lineage only, not overlapping):
  - `#4162` — `13.0.3-ubuntu` → `13.1.1-ubuntu` bump. This is why the
    stale hint mentioning `13.0.3-ubuntu@sha256:7c1acd...` no longer
    reflects the on-`main` state; `security-scan.yml`, `base.yml` and
    `compose.red.yml` were already aligned on the `13.1.1` manifest-list
    digest before this wave started (verified via `rg` on 2026-08-05).
  - `#4310` — Prometheus `v3.13.1` → `v3.13.2`; unrelated to the wave CVEs.

## 4. PR routing

`cdb-pr-router` was executed for the wave. Outcome:

- Decision: `CREATE_DEDICATED_PR`.
- Preferred objective: `security-alert-wave-2026-08-05`.
- Branch: `dedicated/security-alert-wave-2026-08-05`.
- Suggested title: `fix(security): process Grafana alert wave #4350–#4359`.
- Merge mode: `false`. Issue closure before merge: `false`.
- No compatible existing security PR was found. `#4348` / `#4349` are
  dependabot / dependency lanes without security-triage contract overlap
  and were not taken over.

## 5. Alert inventory (live, tool-verified)

Source: `gh api code-scanning/alerts?state=open&tool_name=Trivy` on
`2026-08-05`, filtered by the ten issue fingerprints; verified against the
issue-body fields for `Alert Number`, `HTML URL`, `Ref`, `SHA`, `Path`,
`Tool`, `Rule`, `Severity` and `Fixed Version`. Full JSON in
`artifacts/security-alerts-4350-4359/trivy-alerts-matched.json` and mirrored
in the sibling `.json` evidence file.

| Issue | Alert | CVE | Path | Package | Installed | Fixed Version | Fingerprint |
|---|---|---|---|---|---|---|---|
| `#4350` | 5539 | CVE-2026-25681 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `golang.org/x/net` | `v0.49.0` | `0.55.0` | `abd5ff85d7f65a8d` |
| `#4351` | 5540 | CVE-2026-27136 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `golang.org/x/net` | `v0.49.0` | `0.55.0` | `770d48eac638ba0a` |
| `#4352` | 5548 | CVE-2026-27145 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `stdlib` | `v1.26.3` | `1.25.11, 1.26.4` | `f7705c66f59b11b5` |
| `#4353` | 5541 | CVE-2026-33814 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `golang.org/x/net` | `v0.49.0` | `0.53.0` | `945d6efdac69e714` |
| `#4354` | 5542 | CVE-2026-39821 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `golang.org/x/net` | `v0.49.0` | `0.55.0` | `dc15b05faedce243` |
| `#4355` | 5555 | CVE-2026-39822 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `stdlib` | `v1.26.3` | `1.25.12, 1.26.5, 1.27.0-rc.2` | `c7c0700b54dd4247` |
| `#4356` | 5558 | CVE-2026-42504 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `stdlib` | `v1.26.3` | `1.25.11, 1.26.4` | `bc5498d4bd0877d8` |
| `#4357` | 5601 | CVE-2026-56852 | `usr/share/grafana/bin/grafana` | `golang.org/x/text` | `v0.37.0` | `0.39.0` | `a1f0fd9ec5ada7c9` |
| `#4358` | 5603 | CVE-2026-56852 | `.../elasticsearch/gpx_grafana_elasticsearch_datasource_linux_amd64` | `golang.org/x/text` | `v0.37.0` | `0.39.0` | `60635624058c73e7` |
| `#4359` | 5696 | CVE-2026-56852 | `.../zipkin/gpx_grafana-zipkin-datasource_linux_amd64` | `golang.org/x/text` | `v0.33.0` | `0.39.0` | `8a70b82a5a2364ab` |

Origin of the wave: alerts were surfaced by the "Security Alert Readout"
GitHub Actions workflow (`workflow_run` `30990577816`, readout head
`ca27adeee28d7d63ba457ee627274704e89da990`), which reads Code Scanning
alert state. The alerts themselves were generated by an earlier scheduled
"Security Scan" against the on-`main` Grafana pin
`grafana/grafana:13.1.1-ubuntu@sha256:5a9df011...` at scan-commit
`71900c6302bb96ba523a56affd64912d9d736a29`. All ten alert paths and
installed-versions match exactly what the local baseline Trivy scan
produces against that same digest, so the on-`main` Grafana pin is the
verified source of every wave alert (no rescan needed to attribute
origin).

Pin-alignment note (no blind alignment): the plan hint mentioning
`13.0.3-ubuntu@sha256:7c1acd...` for `security-scan.yml`/`base.yml`
reflects an older workflow revision that no longer exists on `origin/main`
after PR `#4162`. As of `2026-08-05` all four canonical Grafana pin
surfaces on `main` were already aligned on `13.1.1-ubuntu` before this
wave:

- `infrastructure/compose/base.yml`
- `infrastructure/compose/compose.red.yml`
- `.github/workflows/security-scan.yml`
- `knowledge/governance/SERVICE_CATALOG.md`

This wave bumps all four in lockstep to `13.1.2-ubuntu` on the same
verified manifest-list digest; the pin bump is the entire runtime change
in this PR.

## 6. Baseline vs Candidate (Trivy 0.73.0, same severity gate, same DB)

- Baseline pin (still on `origin/main`):
  `grafana/grafana:13.1.1-ubuntu@sha256:5a9df011defa8384ee01fc9b393854daecc6afb98132c66e2e658b3f564830e8`
  — verified as manifest-list digest via `docker buildx imagetools inspect`.
- Candidate pin (this PR proposes):
  `grafana/grafana:13.1.2-ubuntu@sha256:dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45`
  — verified as manifest-list digest via `docker buildx imagetools inspect`;
  amd64 platform digest is
  `sha256:1098ce10e68b3e331389258075351d2d05df00c132a2897c276045766bbd0918`
  for cross-checking.
- Trivy version: `0.73.0` local (GitHub-hosted scan ran `0.70.0`; both use
  the same DB source; results align on the exact CVE IDs and package
  versions for the wave paths).
- Severity gate: `HIGH,CRITICAL`.

Baseline scan of `13.1.1-ubuntu`: **18 HIGH + 1 CRITICAL**, 13 target-CVE
hits including all 10 wave paths. Raw output at
`artifacts/security-alerts-4350-4359/trivy-baseline-13.1.1-5a9df011.json`.

Candidate scan of `13.1.2-ubuntu`: **14 HIGH + 0 CRITICAL**, 11 target-CVE
hits. Raw output at
`artifacts/security-alerts-4350-4359/trivy-candidate-13.1.2.json`.

Delta from baseline to candidate:

- HIGH reduced by 4, CRITICAL reduced by 1.
- Two wave issues cleared: `#4357` (grafana bin, CVE-2026-56852) and
  `#4358` (elasticsearch plugin, CVE-2026-56852). Both packages moved from
  `golang.org/x/text v0.37.0` (vulnerable) to `>= 0.39.0` in the 13.1.2
  rebuild.
- Eight wave issues unchanged and confirmed still HIGH on the candidate:
  `#4350`, `#4351`, `#4352`, `#4353`, `#4354`, `#4355`, `#4356`, `#4359`.
  All are on the bundled Zipkin datasource path
  `usr/share/grafana/data/plugins-bundled/zipkin/gpx_grafana-zipkin-datasource_linux_amd64`.
- Zipkin plugin still ships `stdlib v1.26.3`, `golang.org/x/net v0.49.0`,
  `golang.org/x/text v0.33.0` in 13.1.2. Upstream Grafana rebuild of the
  zipkin plugin against newer Go transitive modules is required to clear
  the remaining eight issues; no in-scope repo change can safely clear
  them, and vendoring / plugin-only patching is explicitly out of scope.

## 7. CVE-family analysis

- CVE-2026-56852 (all three wave hits `#4357`/`#4358`/`#4359`) has a
  single upstream origin: `golang.org/x/text` prior to `0.39.0`. In
  `13.1.1` the grafana server binary and the elasticsearch bundled plugin
  ship `v0.37.0` and the zipkin bundled plugin ships the older `v0.33.0`.
  `13.1.2` rebuilds the grafana bin and the elasticsearch plugin against
  `>= 0.39.0` but does NOT rebuild the zipkin plugin, so `#4359`
  remains HIGH.
- CVE-2026-42504 and CVE-2026-27145 (zipkin plugin: `#4352`, `#4356`) are
  the same Go stdlib class already documented in
  `CDB_SECURITY_BATCH_MATRIX_3065-3070-CVE-42504_2026-06-08.md` as
  UPSTREAM_BLOCKED: they require a Go stdlib rebuild by upstream. The
  current candidate scan re-confirms this against the fresh 13.1.2 digest
  — no change in status.
- All four Zipkin `golang.org/x/net` hits (`#4350`, `#4351`, `#4353`,
  `#4354`) are also upstream-only: the plugin binary embeds
  `golang.org/x/net v0.49.0` statically, and no Grafana release earlier
  than the next security respin can bump that.
- The Zipkin `stdlib` hits (`#4352`, `#4355`, `#4356`) additionally share
  the same statically-embedded Go stdlib `v1.26.3` and clear together on
  any future upstream rebuild.

## 8. Per-issue verdict matrix

Verdicts allowed by the wave contract: `FIX_READY`,
`HOLD_UPSTREAM_NO_FIXED_VERSION`, `DUPLICATE_TRACKING`,
`FALSE_POSITIVE_WITH_EVIDENCE`, `NEEDS_EVIDENCE`. This wave uses only the
first three.

| Issue | Verdict | Canonical tracker | Closure gate |
|---|---|---|---|
| `#4350` | `HOLD_UPSTREAM_NO_FIXED_VERSION` | `#2933` | Upstream Grafana rebuilds zipkin plugin against `golang.org/x/net >= 0.55.0`; alert `5539` fixed/absent on next `main`-tip scan |
| `#4351` | `DUPLICATE_TRACKING` | `#2933` | Same upstream x/net rebuild in zipkin plugin clears alert `5540` |
| `#4352` | `DUPLICATE_TRACKING` | `#2933` | Same upstream Go-stdlib rebuild in zipkin plugin clears alert `5548` |
| `#4353` | `DUPLICATE_TRACKING` | `#2933` | Same upstream x/net rebuild in zipkin plugin clears alert `5541` |
| `#4354` | `DUPLICATE_TRACKING` | `#2933` | Same upstream x/net rebuild in zipkin plugin clears alert `5542` |
| `#4355` | `DUPLICATE_TRACKING` | `#2933` | Same upstream Go-stdlib rebuild in zipkin plugin clears alert `5555` |
| `#4356` | `DUPLICATE_TRACKING` | `#2933` | Same upstream Go-stdlib rebuild in zipkin plugin clears alert `5558` (extends CVE-2026-42504 batch #3065-#3070 lineage to zipkin path) |
| `#4357` | `FIX_READY` | `#4357` | Post-merge `main`-tip Trivy / Code-Scanning recount shows alert `5601` fixed/absent for CVE-2026-56852 on `usr/share/grafana/bin/grafana` |
| `#4358` | `FIX_READY` | `#4358` | Post-merge `main`-tip Trivy / Code-Scanning recount shows alert `5603` fixed/absent for CVE-2026-56852 on the elasticsearch bundled plugin path |
| `#4359` | `DUPLICATE_TRACKING` | `#2933` | Upstream Grafana rebuild bumps zipkin plugin `golang.org/x/text` from `v0.33.0` to `>= 0.39.0`; alert `5696` fixed/absent on next `main`-tip scan |

- `#4350` carries the wave-primary `HOLD_UPSTREAM_NO_FIXED_VERSION` verdict
  because it opens the zipkin upstream cluster; `#4351`–`#4356` and
  `#4359` deduplicate into that same upstream root cause under `#2933`.
- `#4357` and `#4358` are `FIX_READY` because 13.1.2 provably rebuilds the
  affected binaries against a patched `golang.org/x/text`. Neither will be
  closed inside this delivery slice; both stay open until the post-merge
  scan on `main` clears alerts `5601` and `5603` respectively.

## 9. Implemented changes

Forbidden and not used in this delivery: no alert dismissal, no security
exception, no `.trivyignore` growth, no admin-merge bypass, no plugin-only
patch, no vendoring of Grafana source.

- Grafana pin bumped from
  `13.1.1-ubuntu@sha256:5a9df011...` to
  `13.1.2-ubuntu@sha256:dbbf39af...` in lockstep across all four canonical
  surfaces (see §5).
- Wave evidence added:
  - `docs/evidence/security/CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.md`
    (this file)
  - `docs/evidence/security/CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.json`
    (machine-readable mirror; validated by contract test)
- Contract test:
  `tests/unit/security/test_security_alert_wave_4350_4359_contract.py`
  enforces schema, pin-consistency across the four surfaces, cluster
  invariants, prior-evidence linkage, forbidden-actions negation, and
  safety-boundary defaults.

No runtime services were touched. No secrets, `.trivyignore`, plugin
sources, or Grafana source paths were modified. No live/echtgeld or LR
scope was changed.

## 10. Files changed

- `infrastructure/compose/base.yml`
- `infrastructure/compose/compose.red.yml`
- `.github/workflows/security-scan.yml`
- `knowledge/governance/SERVICE_CATALOG.md`
- `docs/evidence/security/CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.md`
- `docs/evidence/security/CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.json`
- `tests/unit/security/test_security_alert_wave_4350_4359_contract.py`

## 11. Tests and scan evidence pointers

- Local Trivy raw scans (attached under
  `artifacts/security-alerts-4350-4359/` for reproducibility):
  - `trivy-baseline-13.1.1-5a9df011.json` (baseline, 18H/1C)
  - `trivy-baseline-13.1.1-matched.json` (13 target-CVE hits filtered)
  - `trivy-candidate-13.1.2.json` (candidate, 14H/0C)
  - `trivy-candidate-13.1.2-matched.json` (11 target-CVE hits filtered)
- `trivy-alerts-raw.json` and `trivy-alerts-matched.json` mirror the live
  GitHub Code-Scanning alerts used to cross-check the ten wave fingerprints.
- Contract test:
  `pytest -q tests/unit/security/test_security_alert_wave_4350_4359_contract.py`
- Compose config validation, `ruff check`, `black --check` and repo-scope
  `gitleaks detect` run at PR time in the targeted-validation step.

## 12. Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
 - GetMcpTools project-0-Claire_de_Binare-cdb_context
 - cdb_context_briefing task_id=cdb-briefing-4350-4359-security-wave
 - gh api code-scanning/alerts (tool_name=Trivy,state=open)
 - gh issue view 4350..4359,2513,2933,2292
 - gh run view 30990577816
 - trivy image (0.73.0) baseline 5a9df011 + candidate dbbf39af
records_or_results:
 - code-scanning: 965 open Trivy alerts on main; 17 hits for target CVE set; 10 exact wave matches by fingerprint
 - trivy baseline 13.1.1: 18 HIGH + 1 CRITICAL, 13 target-CVE hits including 10 wave paths
 - trivy candidate 13.1.2: 14 HIGH + 0 CRITICAL, 11 target-CVE hits; wave issues 4357 + 4358 cleared, others unchanged
repo_crosscheck:
 - agents/AGENTS.md Read Order
 - docs/security/TRIAGE_RUNBOOK.md
 - docs/runbooks/merge_policy_ci_gate.md
 - docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3065-3070-CVE-42504_2026-06-08.md
 - docs/evidence/security/CDB_SECURITY_GRAFANA_3764_CVE-42504_VERIFY_2026-07-06.md
 - docs/evidence/security/CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.md
 - infrastructure/compose/base.yml, compose.red.yml
 - .github/workflows/security-scan.yml
 - knowledge/governance/SERVICE_CATALOG.md
impact_on_plan:
 - Two wave issues (4357, 4358) become FIX_READY and are unblocked by the 13.1.2 rebuild; both stay open until the post-merge main-tip scan clears alerts 5601 and 5603.
 - Eight remaining wave issues (4350, 4351, 4352, 4353, 4354, 4355, 4356, 4359) are consolidated under existing Grafana upstream tracker #2933 with HOLD/DUPLICATE_TRACKING and no in-scope remediation.
 - Consolidating under #2933 avoids ten separate open-forever HOLDs while keeping every finding auditable and reversible.
limitations:
 - Local Trivy 0.73.0 vs GitHub Code Scanning 0.70.0; results align on the wave paths but a small delta on non-wave finds is possible.
 - Post-merge Code-Scanning recount is the true FIX_READY closure gate; without a fresh main-tip scan, #4357 and #4358 stay open.
 - CDB context briefing returned no evidence/claim/decision/memory records for this task ID; repo-only fallback is used with reason=insufficient_evidence.
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

## 13. Restunsicherheit

- Local Trivy DB and version differ from the GitHub-hosted scanner
  (`0.73.0` vs `0.70.0`) — cross-verified on wave paths only. A single-day
  DB drift on non-wave findings is acceptable and does not change the
  wave verdicts.
- `#4357` and `#4358` depend on the post-merge Code-Scanning recount on
  the exact `main` tip after the pin bump lands. Until that recount is
  observed, both issues stay open under a documented
  `HOLD_POST_MERGE_SCAN_PENDING` sub-state.
- The consolidation of `#4351`–`#4356` and `#4359` under `#2933` assumes
  the tracker remains the canonical Grafana upstream cluster. If a future
  session splits `#2933`, the consolidation pointer in `§8` must be
  updated in the follow-up.
