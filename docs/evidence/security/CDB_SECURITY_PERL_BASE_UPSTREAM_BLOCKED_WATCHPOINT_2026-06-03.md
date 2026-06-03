# CDB Security — perl-base Upstream-Blocked Watchpoint

**Stand:** 2026-06-03 (UTC)  
**Parent epic:** [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289)  
**Prior evidence (by reference):**

- [PR #2877](https://github.com/jannekbuengener/Claire_de_Binare/pull/2877) → [`CDB_SECURITY_BATCH_MATRIX_2860-2869_2026-06-03.md`](CDB_SECURITY_BATCH_MATRIX_2860-2869_2026-06-03.md)
- [PR #2921](https://github.com/jannekbuengener/Claire_de_Binare/pull/2921) → [`CDB_SECURITY_CAPPED_BACKLOG_RECONCILE_2289_2026-06-03.md`](CDB_SECURITY_CAPPED_BACKLOG_RECONCILE_2289_2026-06-03.md)

**Scope guard:** Evidence and GitHub triage harmonization only. No Dockerfile/image diff, no alert dismissals, no runtime/stack mutation, no LR-Go, no productive DB writes.

---

## Executive summary

| Cluster | CVE count | Service images | Package | Installed | Fixed (Trivy/Code Scanning) | Verdict |
|---------|-----------|----------------|---------|-----------|------------------------------|---------|
| perl-base OS layer | 5 | 8× `library/cdb_*` | `perl-base` | `5.40.1-6` | *(empty)* | **UPSTREAM_BLOCKED** |

**Open tracker issues:** 40 (#2860–#2867, #2868–#2869, #2880–#2885, #2893–#2900, #2901–#2908, #2910–#2917) — **remain OPEN** after this watchpoint (no mass-close; see dedupe/close safety).

**Root cause:** Shared Debian Trixie OS layer from `python:3.11-slim-trixie` (+ existing `apt-get upgrade` in service Dockerfiles). Not fixable per-service without upstream `perl-base` patch or forbidden base-image migration in this slice.

**Out of scope (separate tracks):** #2886–#2892, #2909 (Grafana/Prometheus/Postgres — [PR #2925](https://github.com/jannekbuengener/Claire_de_Binare/pull/2925)); #2918–#2920 (CodeQL clear-text — [PR #2923](https://github.com/jannekbuengener/Claire_de_Binare/pull/2923)).

---

## Canonical cluster matrix (40 issues)

Dedupe marker: `<!-- cdb-security-alert-group:{fingerprint} -->`  
Labels (live 2026-06-03): `type:security`, `status:blocked`, `triage:offen` on all 40.

| Issue | CVE | Component | Package | Installed | Fixed version | Source layer | Status label | Existing comment evidence | Verdict | Future trigger |
|-------|-----|-----------|---------|-----------|---------------|--------------|--------------|---------------------------|---------|----------------|
| [#2860](https://github.com/jannekbuengener/Claire_de_Binare/issues/2860) | CVE-2026-42496 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | `python:3.11-slim-trixie` + `apt-get upgrade` | `status:blocked` | UPSTREAM_BLOCKED triage 2026-06-03 (#2877) | UPSTREAM_BLOCKED | `perl-base` Fixed Version non-empty → re-readout #2289 |
| [#2861](https://github.com/jannekbuengener/Claire_de_Binare/issues/2861) | CVE-2026-42496 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2862](https://github.com/jannekbuengener/Claire_de_Binare/issues/2862) | CVE-2026-42496 | `library/cdb_execution` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2863](https://github.com/jannekbuengener/Claire_de_Binare/issues/2863) | CVE-2026-42496 | `library/cdb_market` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2864](https://github.com/jannekbuengener/Claire_de_Binare/issues/2864) | CVE-2026-42496 | `library/cdb_regime` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2865](https://github.com/jannekbuengener/Claire_de_Binare/issues/2865) | CVE-2026-42496 | `library/cdb_risk` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2866](https://github.com/jannekbuengener/Claire_de_Binare/issues/2866) | CVE-2026-42496 | `library/cdb_signal` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2867](https://github.com/jannekbuengener/Claire_de_Binare/issues/2867) | CVE-2026-42496 | `library/cdb_ws` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2868](https://github.com/jannekbuengener/Claire_de_Binare/issues/2868) | CVE-2026-8376 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2869](https://github.com/jannekbuengener/Claire_de_Binare/issues/2869) | CVE-2026-8376 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem batch | UPSTREAM_BLOCKED | idem |
| [#2880](https://github.com/jannekbuengener/Claire_de_Binare/issues/2880) | CVE-2026-8376 | `library/cdb_execution` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | watchpoint canonical (#2921 reconcile) | UPSTREAM_BLOCKED | idem |
| [#2881](https://github.com/jannekbuengener/Claire_de_Binare/issues/2881) | CVE-2026-8376 | `library/cdb_market` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2882](https://github.com/jannekbuengener/Claire_de_Binare/issues/2882) | CVE-2026-8376 | `library/cdb_regime` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2883](https://github.com/jannekbuengener/Claire_de_Binare/issues/2883) | CVE-2026-8376 | `library/cdb_risk` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2884](https://github.com/jannekbuengener/Claire_de_Binare/issues/2884) | CVE-2026-8376 | `library/cdb_signal` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2885](https://github.com/jannekbuengener/Claire_de_Binare/issues/2885) | CVE-2026-8376 | `library/cdb_ws` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2893](https://github.com/jannekbuengener/Claire_de_Binare/issues/2893) | CVE-2026-42497 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2894](https://github.com/jannekbuengener/Claire_de_Binare/issues/2894) | CVE-2026-42497 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2895](https://github.com/jannekbuengener/Claire_de_Binare/issues/2895) | CVE-2026-42497 | `library/cdb_execution` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2896](https://github.com/jannekbuengener/Claire_de_Binare/issues/2896) | CVE-2026-42497 | `library/cdb_market` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2897](https://github.com/jannekbuengener/Claire_de_Binare/issues/2897) | CVE-2026-42497 | `library/cdb_regime` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2898](https://github.com/jannekbuengener/Claire_de_Binare/issues/2898) | CVE-2026-42497 | `library/cdb_risk` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2899](https://github.com/jannekbuengener/Claire_de_Binare/issues/2899) | CVE-2026-42497 | `library/cdb_signal` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2900](https://github.com/jannekbuengener/Claire_de_Binare/issues/2900) | CVE-2026-42497 | `library/cdb_ws` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2901](https://github.com/jannekbuengener/Claire_de_Binare/issues/2901) | CVE-2026-48962 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2902](https://github.com/jannekbuengener/Claire_de_Binare/issues/2902) | CVE-2026-48962 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2903](https://github.com/jannekbuengener/Claire_de_Binare/issues/2903) | CVE-2026-48962 | `library/cdb_execution` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2904](https://github.com/jannekbuengener/Claire_de_Binare/issues/2904) | CVE-2026-48962 | `library/cdb_market` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2905](https://github.com/jannekbuengener/Claire_de_Binare/issues/2905) | CVE-2026-48962 | `library/cdb_regime` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2906](https://github.com/jannekbuengener/Claire_de_Binare/issues/2906) | CVE-2026-48962 | `library/cdb_risk` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2907](https://github.com/jannekbuengener/Claire_de_Binare/issues/2907) | CVE-2026-48962 | `library/cdb_signal` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2908](https://github.com/jannekbuengener/Claire_de_Binare/issues/2908) | CVE-2026-48962 | `library/cdb_ws` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2910](https://github.com/jannekbuengener/Claire_de_Binare/issues/2910) | CVE-2026-9538 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2911](https://github.com/jannekbuengener/Claire_de_Binare/issues/2911) | CVE-2026-9538 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2912](https://github.com/jannekbuengener/Claire_de_Binare/issues/2912) | CVE-2026-9538 | `library/cdb_execution` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2913](https://github.com/jannekbuengener/Claire_de_Binare/issues/2913) | CVE-2026-9538 | `library/cdb_market` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2914](https://github.com/jannekbuengener/Claire_de_Binare/issues/2914) | CVE-2026-9538 | `library/cdb_regime` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2915](https://github.com/jannekbuengener/Claire_de_Binare/issues/2915) | CVE-2026-9538 | `library/cdb_risk` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2916](https://github.com/jannekbuengener/Claire_de_Binare/issues/2916) | CVE-2026-9538 | `library/cdb_signal` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |
| [#2917](https://github.com/jannekbuengener/Claire_de_Binare/issues/2917) | CVE-2026-9538 | `library/cdb_ws` | `perl-base` | 5.40.1-6 | — | shared trixie base | `status:blocked` | idem | UPSTREAM_BLOCKED | idem |

Fingerprints: see #2877 matrix (#2860–#2869) and #2921 reconcile table (#2880–#2917); one unique marker per issue (CVE × component × branch).

---

## Root-cause / fixability verdict

**UPSTREAM_BLOCKED** for the full 40-issue cluster.

| Evidence type | Result |
|---------------|--------|
| Repo Dockerfiles | 8 Trixie services: `FROM python:3.11-slim-trixie@sha256:e78299e5…`, `apt-get upgrade` present |
| Code Scanning / Trivy | `perl-base` 5.40.1-6, **Fixed Version** empty for all five CVE rules |
| Digest-only remediation | Rejected in #2877 (pinned + latest Hub amd64 still 5.40.1-6) |

---

## Dedupe / close safety

| Question | Answer |
|----------|--------|
| `gh_check_dedupe` query | `repo:… is:issue "{marker}" in:body` — matches **open and closed** issues |
| Would closing 40 issues recreate duplicates? | **No** — markers remain in closed issue bodies |
| Should we mass-close for consolidation? | **No** — 40 distinct fingerprints (per image × CVE); epic watchpoint + per-service trackers preferred; automation explicitly disclaims auto-close |
| Issue state after this doc | **40 OPEN** |

---

## Label / triage harmonization

| Label | Action |
|-------|--------|
| `status:blocked` | Verified on all 40 (live 2026-06-03); no bulk change |
| `triage:offen` | Retained — only `triage:*` label in repo taxonomy |
| `triage:done` / invented labels | Not used |

---

## Re-triage triggers (watchpoint)

1. Code Scanning or Trivy reports **non-empty Fixed Version** for `perl-base` on `library/cdb_*` images for any of: CVE-2026-42496, CVE-2026-8376, CVE-2026-42497, CVE-2026-48962, CVE-2026-9538.
2. Debian security announcement or Docker Official `python:3.11-slim-trixie` digest change with verified patched `perl-base`.
3. Then: Security Alert Readout under #2289, bounded remediation PR (outside this watchpoint slice), **no** digest-only PR without fix version.

---

## Non-goals (this watchpoint)

- Alert dismissals
- Dockerfile / base image / Compose changes
- `docker compose up|down`, container restart, runtime stack mutation
- Closing #2860–#2917 without a merged fix
- Scope expansion to #2886–#2892, #2909, #2918–#2920

---

## Validation (this document)

- `gh issue view` sample + label audit (40/40 `status:blocked`)
- Repo `services/*/Dockerfile` base pin cross-check
- `scripts/audit/security_issue_automation.py` dedupe query review
- References #2877 / #2921 matrices (not duplicated in full)

No alert dismissals. No issue closures in this slice.
