# CDB Security — Epic #2289 Closeout Readiness

**Stand:** 2026-06-03 (UTC)  
**Epic:** [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289) — `[EPIC] Code-Scanning-Alerts regelmäßig auslesen und automatisch beheben`  
**Residual tracker:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513) — upstream-blocked Trivy residuals (stays **OPEN**)  
**Closeout evidence PR:** *(filled post-merge)*  
**Base SHA at audit:** `67cc4df6` (`origin/main`, includes #2927 @ `89a55034`)

**Scope guard:** Closeout assessment and handoff documentation only. No alert dismissals, no Dockerfile/image/runtime changes, no CVE issue closures without fix, no LR/live/echtgeld derivation.

---

## Executive summary

| Field | Value |
|-------|-------|
| **Recommendation** | **CLOSE #2289** |
| **Rationale** | Security-Ops automation scope (readout, delta, dedupe, escalation, issue creation, evidence) is delivered and validated on `main`. Upstream-blocked CVE residuals are tracked in #2513 and 48 open per-fingerprint issues — not Epic closure blockers. |
| **Residual ownership** | #2513 (batch/upstream policy) + individual issues #2860–#2917, #2886–#2909 |
| **LR status** | **NO-GO** (unchanged) |

---

## Delivered PR map

| PR | Merge SHA (short) | Merged (UTC) | Delivered |
|----|-------------------|--------------|-----------|
| [#2421](https://github.com/jannekbuengener/Claire_de_Binare/pull/2421) | `f227aa42` | 2026-05-10 | Scheduled Security Alert Readout workflow + delta comparator |
| [#2424](https://github.com/jannekbuengener/Claire_de_Binare/pull/2424) | `2fbeebaf` | 2026-05-10 | `persist_via_pr` — branch + PR persistence (no direct push) |
| [#2495](https://github.com/jannekbuengener/Claire_de_Binare/pull/2495) | `87827c00` | 2026-05-15 | Issue automation (dry-run default; schedule live) |
| [#2877](https://github.com/jannekbuengener/Claire_de_Binare/pull/2877) | `5dd165c8` | 2026-06-03 | perl-base batch matrix #2860–#2869 (UPSTREAM_BLOCKED) |
| [#2921](https://github.com/jannekbuengener/Claire_de_Binare/pull/2921) | `18684827` | 2026-06-03 | Capped backlog reconciliation (41 issues #2880–#2920) |
| [#2923](https://github.com/jannekbuengener/Claire_de_Binare/pull/2923) | `61d8c4bf` | 2026-06-03 | CodeQL clear-text fix; closes #2918–#2920 |
| [#2925](https://github.com/jannekbuengener/Claire_de_Binare/pull/2925) | `0d994070` | 2026-06-03 | Grafana/Prometheus/Postgres triage matrix |
| [#2927](https://github.com/jannekbuengener/Claire_de_Binare/pull/2927) | `89a55034` | 2026-06-03 | Canonical perl-base upstream watchpoint (40 issues) |

**Automation proof run:** [Actions #26871768632](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/26871768632) — issue-automation **LIVE**, `created=10`, `capped=41` (later reconciled via #2921 manual drain).

---

## #2289 acceptance criteria audit

| # | Criterion (from #2289 body) | Status | Evidence |
|---|----------------------------|--------|----------|
| 1 | Regelmäßiger Job liest offene Code-Scanning-Alerts aus | **DELIVERED** | `.github/workflows/security-alert-readout.yml` — Mo/Mi/Fr 06:15 UTC + `workflow_dispatch` |
| 2 | Report gruppiert nach Package/CVE/Severity/Fixbarkeit | **DELIVERED** | `scripts/audit/github_security_quality_readout.py`, `security_alert_delta.py`; `docs/security/readouts/YYYY-MM-DD/` |
| 3 | Alerts werden dedupliziert | **DELIVERED** | Delta comparator; issue fingerprint `<!-- cdb-security-alert-group:{fingerprint} -->` |
| 4 | Fixbare Findings → Remediation-PRs | **DELIVERED (process)** | `persist_via_pr`; manual fix PRs (e.g. #2923); no auto-Trivy remediation bot (explicit non-goal) |
| 5 | Nach Fix erneuter Trivy/Code-Scanning-Check | **DELIVERED** | CI Trivy/CodeQL on push; #2918–#2920 closed post-#2923 |
| 6 | Neue Critical/High → sichtbare Eskalation | **DELIVERED** | Delta exit 2; workflow warnings; issue automation on schedule |
| 7 | Unknown-Severity separat markiert | **DELIVERED** | `severity_band_from()` in `security_alert_issue_candidates.py`; unknown → low band, visible in readout, skipped by automation |
| 8 | Dismissals: Reason, Kommentar, Re-Evaluation | **DELIVERED (governance)** | `docs/security/TRIAGE_RUNBOOK.md` §4; automation does not dismiss |

**Definition of Done (#2289):**

- Wiederkehrender Alert-Report eingerichtet — **yes**
- Erste Alert-Welle bereinigt oder als Remediation-PRs vorbereitet — **yes** (CodeQL remediated; Trivy triaged to issues)
- Neue Alerts in klaren Fix-/Triage-Prozess — **yes**

---

## Residual inventory (open after Epic close)

**Live count (2026-06-03):** 48 open issues with label `type:security`.

| Cluster | Open issues | CVEs / subject | Verdict | Canonical evidence |
|---------|-------------|----------------|---------|-------------------|
| perl-base / Trixie OS layer | **40** | #2860–#2867, #2868–#2869, #2880–#2885, #2893–#2900, #2901–#2908, #2910–#2917 | **UPSTREAM_BLOCKED** | [`CDB_SECURITY_PERL_BASE_UPSTREAM_BLOCKED_WATCHPOINT_2026-06-03.md`](CDB_SECURITY_PERL_BASE_UPSTREAM_BLOCKED_WATCHPOINT_2026-06-03.md) |
| Grafana / Prometheus / Postgres | **8** | #2886–#2892, #2909 | **UPSTREAM_BLOCKED** | [`CDB_SECURITY_BATCH_MATRIX_2886-2892-2909_2026-06-03.md`](CDB_SECURITY_BATCH_MATRIX_2886-2892-2909_2026-06-03.md) |

**Capped backlog:** fully materialized — see [`CDB_SECURITY_CAPPED_BACKLOG_RECONCILE_2289_2026-06-03.md`](CDB_SECURITY_CAPPED_BACKLOG_RECONCILE_2289_2026-06-03.md).

**Explicit non-action:** Do **not** close these 48 issues or dismiss Code Scanning alerts without upstream fix + Human-GO per `TRIAGE_RUNBOOK.md`.

---

## #2513 residual handoff

After #2289 closes:

- **#2513 remains OPEN** as the upstream-blocked Trivy residual tracker.
- May-2026 body (681 alerts, dismissal batches A–G2) remains historical reference for Human-GO dismissals.
- June-2026 operational handoff: per-fingerprint issues above + cluster evidence docs on `main`.
- **Note:** #2513 body incorrectly stated #2289 was closed 2026-05-17; live GitHub had #2289 **OPEN** until this closeout slice.

**Re-triage triggers:** non-empty Fixed Version in Trivy/Code Scanning for blocked packages; new Security Alert Readout escalation under #2513 / scheduled workflow.

---

## Documented non-blockers (Epic scope)

| Item | Status |
|------|--------|
| `CDB_GH_ALERTS_TOKEN` (Dependabot read scope) | Ops config; readout stays **partial** until set |
| 48 upstream-blocked CVE issues | Operational trackers; owned by #2513 + individual issues |
| Auto-remediation bot for fixable OS CVEs | Out of Epic scope; manual PR path only |

---

## Non-goals

- Alert dismissals
- Dockerfile / base-image / digest changes
- BLUE/RED runtime mutation
- Closing residual CVE issues without fix
- LR / live / echtgeld scope change

---

## Validation (this slice)

- Live GitHub: #2289 OPEN → close after this doc merges; #2513 OPEN
- PR merge states verified via `gh pr view`
- Issue automation: Run 26871768632 + capped reconcile #2921
- Unit tests: `pytest -q tests/unit/scripts/ -k security` (see PR checks)

---

## Close recommendation

**CLOSE #2289** — Security-Ops Epic objectives met. Residual CVE work continues under **#2513** and open per-alert issues; LR remains **NO-GO**.
