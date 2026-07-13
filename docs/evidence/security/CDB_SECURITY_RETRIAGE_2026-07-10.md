# Security Re-Triage — Open Residual Clusters & Alert Children

**Stand:** 2026-07-10 (UTC+2)  
**Mode:** Analysis (superseded for compression by [`CDB_SECURITY_ALERT_COMPRESSION_3945-3954_2026-07-10.md`](CDB_SECURITY_ALERT_COMPRESSION_3945-3954_2026-07-10.md))  
**Parent meta:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Runtime gate:** [#3982](https://github.com/jannekbuengener/Claire_de_Binare/issues/3982) OPEN — 4h ARVP run active since `2026-07-10T17:20:00Z`  
**LR:** NO-GO (unchanged)  
**Main @ analysis:** `63d73734422652acd2c494c0823fa9a8281888e2`

---

## Executive verdict

| Category | Count | Action |
|----------|-------|--------|
| Meta tracker | 1 (#2513) | Watch / index maintenance |
| Residual cluster parents | 6 (#2932, #2933, #3705, #3802, #3803, #3936) | UPSTREAM_BLOCKED — watch Debian/upstream rebuilds |
| Alert children #3945–#3954 | 10 | **Compressed** 2026-07-10 → #2932 / #3803 (see compression doc) |
| Dependabot security PR | 1 (#3755) | HOLD — not a security fix |
| CodeQL Python | 0 open | No action |
| Actionable CDB fixes now | **0** | All open Trivy clusters upstream-blocked on current pins |

**Status:** `ANALYSIS_READY_FOR_DECISION` → compression executed in follow-up slice (docs-only)

---

## Live snapshot (GitHub)

- Open security issues (scoped): **17** (`type:security` + alert readout children)
- Open security PRs: **1** (#3755 Grafana)
- #3982: OPEN, RUNTIME-GO received, observation window until `2026-07-10T21:20:00Z`

---

## Cluster map

```
#2513 (meta index)
├── #2932 perl-base CVEs (incl. new readout CVE-2026-53615 → #3945–#3952)
├── #2933 Grafana / Prometheus / Postgres / gosu / bundled plugins
├── #3705 libsqlite3 CVE-2026-11824 (8× python:3.14-slim-trixie)
├── #3802 gzip CVE-2026-41992 (8× python:3.14-slim-trixie)
├── #3803 libacl1 CVE-2026-54369 (all Trixie services; #3953–#3954 = new readout)
└── #3936 libcurl4t64 CVE-2026-12064 (7× python:3.14-slim-trixie; NOT postgres alpine)
```

**Note:** Postgres alpine `libcurl` CVE-2026-12064 cleared by digest refresh PR #3921 (`384de27b`); GitHub alert delta pending next `security-scan.yml` on main. Trixie `libcurl4t64` is a **separate** cluster (#3936).

---

## Repo surface (static)

| Surface | Pin / evidence |
|---------|----------------|
| 8 BLUE Trixie Dockerfiles | `python:3.14-slim-trixie@sha256:b877e50…` |
| Grafana (main) | `grafana/grafana:13.0.3-ubuntu@sha256:7c1acd41…` |
| Postgres (main) | `postgres:18.4-alpine@sha256:ecafd342…` (post-#3921) |
| Prometheus (main) | `prom/prometheus:v3.13.0@sha256:c6b27ea4…` |
| CodeQL | 0 open alerts (cyclic-import fix #3940 merged) |

---

## PR #3755

| Field | Value |
|-------|-------|
| Change | Grafana 13.0.3 → 13.1.0 in `compose.red.yml` |
| CI | All required checks SUCCESS (2026-07-08) |
| Security verdict | **HOLD** — CVE-2026-42504 still present on bundled ES plugin (Go stdlib 1.26.3) |
| Merge as security fix | **NO** |
| Covers | Optional semver hygiene only; does **not** close #2933 Grafana sub-clusters |

Evidence: `docs/evidence/security/CDB_SECURITY_GRAFANA_3764_CVE-42504_VERIFY_2026-07-06.md`

---

## Recommended remediation batches (post-#3982)

### Batch 1 — Docs-only alert compression (P0, low risk)

- Link #3945–#3952 → #2932 (CVE-2026-53615; package probe recommended before close)
- Link #3953–#3954 → #3803 (CVE-2026-54369)
- Update #2513 cluster table to include #3936
- No alert dismissals; Code Scanning stays open

### Batch 2 — Digest-watch automation (P1, no action until upstream)

- Single coordinated probe when Debian Trixie publishes fixes for gzip, libacl1, libsqlite3, libcurl4t64, perl-base
- One digest pin refresh across 8 Dockerfiles + rebuild + Trivy/Code Scanning recheck

### Batch 3 — Monitoring image watch (P2)

- #2933: gosu, Grafana bundled plugins, Prometheus Go stdlib — upstream rebuild only
- #3755: merge only under explicit non-security hygiene GO

### Batch 4 — Human-GO dismissal batches (P3, not authorized)

- Historical batches A–G2 per `docs/security/TRIAGE_RUNBOOK.md` — requires separate Human-GO

---

## Do-not-touch while #3982 runs

- Docker build / image rebuild / digest refresh on BLUE services
- `docker compose up|down|restart`
- PR #3755 merge (RED/Grafana — avoid monitoring churn during ARVP window)
- Any dependency bump or security remediation PR

**Safe now:** read-only analysis, issue comments, evidence docs, label recommendations.

---

## Open questions

1. **CVE-2026-53615 package:** No repo Trivy matrix yet — confirm `perl-base` via representative `cdb_risk` image probe after #3982.
2. **Postgres libcurl alert delta:** Confirm GitHub Code Scanning clears after next weekly `security-scan.yml` (digest already on main).
3. **#2513 drift:** Meta body lists 5 clusters; #3936 libcurl missing from index table.
