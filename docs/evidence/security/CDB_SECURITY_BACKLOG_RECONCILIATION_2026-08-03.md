# Security Backlog Reconciliation — 2026-08-03

**Anchor:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Machine snapshot:** [`CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.json`](CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.json)  
**Base:** `origin/main` @ `abf997d5fec97c4d4da139ae0fb9c1fe28773e89`  
**Branch:** `dedicated/security-backlog-reconciliation-2513`  
**Routing:** `CREATE_DEDICATED_PR` (unrelated open PR #4302 excluded)  
**LR:** NO-GO · Board stage `trade-capable` (orthogonal)  
**Slice policy:** no merge · no issue close · no alert dismissal · no `.trivyignore` growth · no Full Fast-CI · no `cdb-local-ci`

---

## Executive summary

All **20** open `type:security` issues were live-inventoried and assigned exactly one disposition. This slice delivers a reconciliation evidence pack + contract test. No suite-native FixedVersion remediations were available for residual OS-layer findings; pip alerts for `CVE-2026-8643` are scan-verified fixed.

| Disposition | Issues |
|-------------|--------|
| `CANONICAL_TRACKER_ACTIVE` | #2513, #2932, #2933, #3705, #3802, #3803, #3936, #4080 |
| `DUPLICATE_TRACKING_PENDING_CLOSE_AFTER_MERGE` | #4089–#4093, #4096–#4098 → canonical **#4080** |
| `FIXED_SCAN_VERIFIED` | #4094 (alert **5527**), #4095 (alert **5526**) |
| `HOLD_UPSTREAM_NO_FIXED_VERSION` | #4106 (`CVE-2026-13221`), #4114 (`CVE-2026-57432`) |
| `REMEDIATED_SCAN_VERIFIED` | none |
| `BLOCKED_INSUFFICIENT_EVIDENCE` | none |

---

## Live inventory (2026-08-03)

| Check | Result |
|-------|--------|
| Open `type:security` count | **20** (matches plan snapshot) |
| Dependabot vulnerability alerts OPEN | 0 |
| Code Scanning pip `CVE-2026-8643` | alerts 5526/5527 `state=fixed`, `fixed_at` set, `dismissed_at=null` |
| Dedicated branch pre-existence | none (created clean from `abf997d5`) |

---

## Role map

### Meta
- **#2513** — active meta tracker for upstream-blocked Trivy residuals.

### Canonical residual clusters
- **#2932** perl-base family · **#2933** Grafana/Prometheus/Postgres · **#3705** libsqlite3 · **#3802** gzip · **#3803** libacl1 · **#3936** libcurl4t64 (Trixie cdb).

### Canonical curl + component duplicates
- **#4080** canonical for `CVE-2026-8286` (+ adjacent `CVE-2026-8927` package floor).
- Component trackers **#4089–#4093** (8286) and **#4096–#4098** (8927) are `DUPLICATE_TRACKING_PENDING_CLOSE_AFTER_MERGE`.

### pip fixed (scan-verified)
| Issue | Path | Alert | state | fixed_at | dismissed_at |
|-------|------|-------|-------|----------|--------------|
| #4094 | `usr/local/.../pip-26.1` | **5527** | fixed | 2026-07-31T12:51:29Z | null |
| #4095 | `venv/.../pip-26.1` | **5526** | fixed | 2026-07-31T12:51:44Z | null |

Evidence: [`CDB_SECURITY_PIP_CVE-2026-8643_4095_2026-07-31.md`](CDB_SECURITY_PIP_CVE-2026-8643_4095_2026-07-31.md). Pin `pip==26.1.2` already on main; this slice only reconciles issue disposition.

### perl CVE HOLDs
| Issue | CVE | Scope | Verdict |
|-------|-----|-------|---------|
| #4106 | `CVE-2026-13221` | eight Trixie service images | `HOLD_UPSTREAM_NO_FIXED_VERSION` |
| #4114 | `CVE-2026-57432` | **only** `cdb_allocation` + `cdb_db_writer` | `HOLD_UPSTREAM_NO_FIXED_VERSION` |

**#4114 scope-drift correction:** Issue title previously implied active “Remediation”. Operative truth is Upstream HOLD for the shared `perl-base` finding on allocation/db_writer only — not the eight-image #4106 scope, and not a silent suite migration to forky glibc. Title corrected in this delivery session.

---

## Remediations this slice

**None.** Conditional remediation requires suite-native FixedVersion. Residual OS findings remain `HOLD_UPSTREAM_NO_FIXED_VERSION` / canonical trackers. Forbidden: alert dismiss, `.trivyignore` expand, cross-suite package pins.

---

## Duplicate consolidation

After this dedicated PR merges (separate merge session):

1. Close #4089–#4093, #4096–#4098 as duplicate trackers under #4080 (HOLD remains open).
2. Close #4094/#4095 after confirming FIXED_SCAN_VERIFIED remains true on main tip.
3. Keep #2513 / residual clusters / #4106 / #4114 open until their closure conditions fire.

---

## Contract coverage

| Artifact | Role |
|----------|------|
| `tests/unit/security/test_security_backlog_reconciliation_contract.py` | Snapshot schema + disposition uniqueness + role invariants |
| `tests/unit/security/test_cve_2026_8286_image_contract.py` | Curl HOLD |
| `tests/unit/security/test_cve_2026_13221_image_contract.py` | perl-base eight-image HOLD |
| `tests/unit/security/test_cve_2026_57432_image_contract.py` | perl-base allocation/db_writer HOLD (extended) |
| `tests/unit/infra/test_dockerfile_pip_pin_contract.py` | pip floor pins (existing) |

---

## Boundaries

- Shadow/Paper-first; LR remains NO-GO.
- No Live/Echtgeld, secrets, productive DB writes, MCP mutations, BLUE/RED runtime changes.
- No merge / issue close / alert dismissal in this delivery slice.
- PR #4302 untouched.

---

## Brain Evidence (delivery)

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

GitHub live + repo evidence govern this reconciliation.
