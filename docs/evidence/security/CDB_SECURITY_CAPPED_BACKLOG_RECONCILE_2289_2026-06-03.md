# Capped Security Alert Backlog Reconciliation — #2289

**Stand:** 2026-06-03 (UTC)  
**Parent epic:** [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289)  
**Prior matrix (perl-base batch):** [#2877](https://github.com/jannekbuengener/Claire_de_Binare/pull/2877) → `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_2860-2869_2026-06-03.md`  
**Source readout run:** [Actions #26871768632](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/26871768632)  
**Artifact:** `security-alert-readout-21` (`security_alert_delta.json`, 2026-06-03)

**Scope guard:** Issue materialization + evidence only. No alert dismissals, no Dockerfile/base-image remediation, no runtime mutation.

---

## Run 26871768632 baseline (automation)

| Counter | Value |
|---------|------:|
| total_candidates | 59 |
| eligible (high band) | 51 |
| created (cap slot) | 10 → #2860–#2869 |
| deduped | 0 |
| skipped (below threshold / comparison) | 8 |
| capped (deferred) | 41 |
| failed | 0 |

---

## Reconciliation slice (manual drain, 2026-06-03)

Re-ranked eligible candidates from artifact delta using `scripts/audit/security_alert_issue_candidates.py` + same sort order as `security_issue_automation.py` (`MAX_NEW_ISSUES_PER_RUN=10` already consumed in run).

| Counter | Value |
|---------|------:|
| capped candidates re-evaluated | 41 |
| dedupe hits (pre-create) | 0 |
| **created (this slice)** | **41 → #2880–#2920** |
| failed | 0 |
| remaining capped after slice | 0 |

**Evidence source:** downloaded workflow artifact via `gh run download 26871768632`; fingerprints verified with `gh_check_dedupe` before each `gh issue create`.

---

## Capped candidate matrix (reconciled)

Dedupe marker format: `<!-- cdb-security-alert-group:{fingerprint} -->`.  
`candidate_action`: `CREATE_ISSUE` (this slice) unless noted.

| CVE / subject | Package / rule | Affected component | Branch | Severity | Existing issue | Fingerprint | Action | Evidence |
|---------------|----------------|-------------------|--------|----------|----------------|-------------|--------|----------|
| CVE-2026-8376 | perl-base (Trivy) | library/cdb_execution | main | critical | — | `8f299fcf5533800d` | CREATE → [#2880](https://github.com/jannekbuengener/Claire_de_Binare/issues/2880) | run log + delta |
| CVE-2026-8376 | perl-base | library/cdb_market | main | critical | — | `5b35b8dfcf2e6572` | CREATE → [#2881](https://github.com/jannekbuengener/Claire_de_Binare/issues/2881) | idem |
| CVE-2026-8376 | perl-base | library/cdb_regime | main | critical | — | `633199f7120177f5` | CREATE → [#2882](https://github.com/jannekbuengener/Claire_de_Binare/issues/2882) | idem |
| CVE-2026-8376 | perl-base | library/cdb_risk | main | critical | — | `b087649838701a35` | CREATE → [#2883](https://github.com/jannekbuengener/Claire_de_Binare/issues/2883) | idem |
| CVE-2026-8376 | perl-base | library/cdb_signal | main | critical | — | `756bd2eb9c1e6025` | CREATE → [#2884](https://github.com/jannekbuengener/Claire_de_Binare/issues/2884) | idem |
| CVE-2026-8376 | perl-base | library/cdb_ws | main | critical | — | `9508e44a8e00357f` | CREATE → [#2885](https://github.com/jannekbuengener/Claire_de_Binare/issues/2885) | idem |
| CVE-2026-8376 | perl-base | library/cdb_allocation | main | critical | [#2868](https://github.com/jannekbuengener/Claire_de_Binare/issues/2868) | `64a88b366843863f` | DEDUPE (run 26871768632) | matrix #2877 |
| CVE-2026-8376 | perl-base | library/cdb_db_writer | main | critical | [#2869](https://github.com/jannekbuengener/Claire_de_Binare/issues/2869) | `a17110bafd6b986a` | DEDUPE (run 26871768632) | matrix #2877 |
| CVE-2026-34040 | grafana | usr/share/grafana/bin/grafana | main | high | — | `000e39e438dca786` | CREATE → [#2886](https://github.com/jannekbuengener/Claire_de_Binare/issues/2886) | delta |
| CVE-2026-41567 | prometheus | bin/prometheus | main | high | — | `6bd10cd107e98482` | CREATE → [#2887](https://github.com/jannekbuengener/Claire_de_Binare/issues/2887) | delta |
| CVE-2026-41567 | prometheus | bin/promtool | main | high | — | `2815609d580739b9` | CREATE → [#2888](https://github.com/jannekbuengener/Claire_de_Binare/issues/2888) | delta |
| CVE-2026-41567 | prometheus | usr/share/grafana/bin/grafana | main | high | — | `0fb3720c0ceeeb7e` | CREATE → [#2889](https://github.com/jannekbuengener/Claire_de_Binare/issues/2889) | delta |
| CVE-2026-42306 | prometheus | bin/prometheus | main | high | — | `6c8bb263fefa55a0` | CREATE → [#2890](https://github.com/jannekbuengener/Claire_de_Binare/issues/2890) | delta |
| CVE-2026-42306 | prometheus | bin/promtool | main | high | — | `3cdab6351bf316a3` | CREATE → [#2891](https://github.com/jannekbuengener/Claire_de_Binare/issues/2891) | delta |
| CVE-2026-42306 | prometheus | usr/share/grafana/bin/grafana | main | high | — | `a065c87bf2c00e81` | CREATE → [#2892](https://github.com/jannekbuengener/Claire_de_Binare/issues/2892) | delta |
| CVE-2026-42497 | perl-base (Trivy) | library/cdb_allocation | main | high | — | `b803ce0823a8643c` | CREATE → [#2893](https://github.com/jannekbuengener/Claire_de_Binare/issues/2893) | delta |
| CVE-2026-42497 | perl-base | library/cdb_db_writer | main | high | — | `0994fcf8e72a8f0e` | CREATE → [#2894](https://github.com/jannekbuengener/Claire_de_Binare/issues/2894) | delta |
| CVE-2026-42497 | perl-base | library/cdb_execution | main | high | — | `7247fb8f9ecc53b2` | CREATE → [#2895](https://github.com/jannekbuengener/Claire_de_Binare/issues/2895) | delta |
| CVE-2026-42497 | perl-base | library/cdb_market | main | high | — | `15e042bc9611a3a6` | CREATE → [#2896](https://github.com/jannekbuengener/Claire_de_Binare/issues/2896) | delta |
| CVE-2026-42497 | perl-base | library/cdb_regime | main | high | — | `83c86e06a60e3ec8` | CREATE → [#2897](https://github.com/jannekbuengener/Claire_de_Binare/issues/2897) | delta |
| CVE-2026-42497 | perl-base | library/cdb_risk | main | high | — | `2e409ea4744de3a8` | CREATE → [#2898](https://github.com/jannekbuengener/Claire_de_Binare/issues/2898) | delta |
| CVE-2026-42497 | perl-base | library/cdb_signal | main | high | — | `b164677fae90044f` | CREATE → [#2899](https://github.com/jannekbuengener/Claire_de_Binare/issues/2899) | delta |
| CVE-2026-42497 | perl-base | library/cdb_ws | main | high | — | `3b59426dbc4ee7ea` | CREATE → [#2900](https://github.com/jannekbuengener/Claire_de_Binare/issues/2900) | delta |
| CVE-2026-48962 | perl-base (Trivy) | library/cdb_allocation | main | high | — | `9e1379567efc27fe` | CREATE → [#2901](https://github.com/jannekbuengener/Claire_de_Binare/issues/2901) | delta |
| CVE-2026-48962 | perl-base | library/cdb_db_writer | main | high | — | `06e70e275ba92c13` | CREATE → [#2902](https://github.com/jannekbuengener/Claire_de_Binare/issues/2902) | delta |
| CVE-2026-48962 | perl-base | library/cdb_execution | main | high | — | `d425012b132cb703` | CREATE → [#2903](https://github.com/jannekbuengener/Claire_de_Binare/issues/2903) | delta |
| CVE-2026-48962 | perl-base | library/cdb_market | main | high | — | `e048edb43febfb21` | CREATE → [#2904](https://github.com/jannekbuengener/Claire_de_Binare/issues/2904) | delta |
| CVE-2026-48962 | perl-base | library/cdb_regime | main | high | — | `a6b6b2800a8d3d56` | CREATE → [#2905](https://github.com/jannekbuengener/Claire_de_Binare/issues/2905) | delta |
| CVE-2026-48962 | perl-base | library/cdb_risk | main | high | — | `4b890a0af4cdfde7` | CREATE → [#2906](https://github.com/jannekbuengener/Claire_de_Binare/issues/2906) | delta |
| CVE-2026-48962 | perl-base | library/cdb_signal | main | high | — | `0fa8c21dc279500c` | CREATE → [#2907](https://github.com/jannekbuengener/Claire_de_Binare/issues/2907) | delta |
| CVE-2026-48962 | perl-base | library/cdb_ws | main | high | — | `8516c09ce8c01fc6` | CREATE → [#2908](https://github.com/jannekbuengener/Claire_de_Binare/issues/2908) | delta |
| CVE-2026-6732 | postgres image | library/postgres | main | high | — | `a6f89a4ed838c37b` | CREATE → [#2909](https://github.com/jannekbuengener/Claire_de_Binare/issues/2909) | delta |
| CVE-2026-9538 | perl-base (Trivy) | library/cdb_allocation | main | high | — | `424990135de2d4c9` | CREATE → [#2910](https://github.com/jannekbuengener/Claire_de_Binare/issues/2910) | delta |
| CVE-2026-9538 | perl-base | library/cdb_db_writer | main | high | — | `4a01a204b63500ad` | CREATE → [#2911](https://github.com/jannekbuengener/Claire_de_Binare/issues/2911) | delta |
| CVE-2026-9538 | perl-base | library/cdb_execution | main | high | — | `eb15ff7aab23cb2e` | CREATE → [#2912](https://github.com/jannekbuengener/Claire_de_Binare/issues/2912) | delta |
| CVE-2026-9538 | perl-base | library/cdb_market | main | high | — | `b433a4d3c29fe36d` | CREATE → [#2913](https://github.com/jannekbuengener/Claire_de_Binare/issues/2913) | delta |
| CVE-2026-9538 | perl-base | library/cdb_regime | main | high | — | `1f4c3add646bbffb` | CREATE → [#2914](https://github.com/jannekbuengener/Claire_de_Binare/issues/2914) | delta |
| CVE-2026-9538 | perl-base | library/cdb_risk | main | high | — | `425d87d9285c131c` | CREATE → [#2915](https://github.com/jannekbuengener/Claire_de_Binare/issues/2915) | delta |
| CVE-2026-9538 | perl-base | library/cdb_signal | main | high | — | `aa700994728801a2` | CREATE → [#2916](https://github.com/jannekbuengener/Claire_de_Binare/issues/2916) | delta |
| CVE-2026-9538 | perl-base | library/cdb_ws | main | high | — | `add9735598d19938` | CREATE → [#2917](https://github.com/jannekbuengener/Claire_de_Binare/issues/2917) | delta |
| py/clear-text-logging-sensitive-data | CodeQL | tools/surrealdb/context_importer.py | main | high | — | `fc8d70af315062ef` | CREATE → [#2918](https://github.com/jannekbuengener/Claire_de_Binare/issues/2918) | delta |
| py/clear-text-logging-sensitive-data | CodeQL | tools/surrealdb/context_onboarding_doctor.py | main | high | — | `8bfbf7b52030cee9` | CREATE → [#2919](https://github.com/jannekbuengener/Claire_de_Binare/issues/2919) | delta |
| py/clear-text-storage-sensitive-data | CodeQL | tools/surrealdb/audit_trail_t3_common.py | main | high | — | `37b4eac1cab845c9` | CREATE → [#2920](https://github.com/jannekbuengener/Claire_de_Binare/issues/2920) | delta |

---

## Dedupe decisions

| Group | Decision |
|-------|----------|
| #2860–#2867 (CVE-2026-42496, 8× cdb_*) | Already created in run 26871768632; **remain OPEN**, UPSTREAM_BLOCKED per #2877 matrix |
| #2868–#2869 (CVE-2026-8376, 2× cdb_*) | Already created in run; **remain OPEN**, UPSTREAM_BLOCKED |
| #2880–#2885 (CVE-2026-8376, 6× remaining cdb_*) | **Created** in this slice; labels include `status:blocked` (Trivy wave) |
| #2893–#2900, #2901–#2908, #2910–#2917 (perl-base family CVEs on cdb_*) | **Created**; `status:blocked` where automation applies Trivy-wave heuristic |
| #2886–#2892 (Grafana/Prometheus CVEs) | **Created**; no `status:blocked` auto-label (monitoring stack upstream) |
| #2909 (CVE-2026-6732 postgres image) | **Created**; triage open |
| #2918–#2920 (CodeQL clear-text) | **Created**; application remediation track (not UPSTREAM_BLOCKED by default) |
| #2290 | Historical context only; not used for auto-close |

---

## #2860–#2869 status (unchanged)

Issues **#2860–#2869 stay OPEN** with UPSTREAM_BLOCKED classification for shared `perl-base` on `python:3.11-slim-trixie` (see #2877 matrix). This reconciliation does **not** close them and does **not** dismiss Code Scanning alerts.

---

## Non-goals (this slice)

- Alert dismissals
- Dockerfile / base-image / digest remediation
- BLUE/RED runtime changes
- LR / live / echtgeld scope

---

## Validation

- `gh run download 26871768632` + delta parse
- `gh issue list` / dedupe GraphQL before create
- Unit tests: `tests/unit/scripts/test_security_alert_issue_candidates.py`, `tests/unit/scripts/test_security_issue_automation.py`
