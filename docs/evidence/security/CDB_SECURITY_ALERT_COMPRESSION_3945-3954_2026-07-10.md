# Security Alert Compression — Issues #3945–#3954

**Stand:** 2026-07-10 (UTC+2)  
**Mode:** Docs-only board compression — **not remediation**  
**Parent meta:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Prior analysis:** [`CDB_SECURITY_RETRIAGE_2026-07-10.md`](CDB_SECURITY_RETRIAGE_2026-07-10.md)  
**Runtime gate:** [#3982](https://github.com/jannekbuengener/Claire_de_Binare/issues/3982) OPEN during slice (docs-only; no runtime/image action)  
**LR:** NO-GO (unchanged)

---

## Executive summary

| Action | Result |
|--------|--------|
| Compress #3945–#3952 | Parent [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932) (perl-base / shared Trixie OS cluster) |
| Compress #3953–#3954 | Parent [#3803](https://github.com/jannekbuengener/Claire_de_Binare/issues/3803) (libacl1 CVE-2026-54369) |
| Update #2513 index | Comment + this doc (includes [#3936](https://github.com/jannekbuengener/Claire_de_Binare/issues/3936) libcurl cluster) |
| Code Scanning alerts | **Remain OPEN** — no dismissals |
| Parent clusters | **Remain OPEN** — upstream-blocked |

**Verdict:** `TRACKING_COMPRESSED` — GitHub issue dedupe only.

---

## Explicit boundaries

- **Not remediated:** No Dockerfile, digest, dependency, or runtime change.
- **Not fixed:** Code Scanning / Trivy alerts stay open until scan-verified upstream fix.
- **Not dismissed:** No SARIF hiding, no alert dismissal, no Human-GO batch.
- **PR #3755:** Remains **HOLD** (no security gain for Grafana CVE-2026-42504).

---

## Cluster A — CVE-2026-53615 → #2932

**Parent:** [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932) — perl-base upstream-blocked CVEs across CDB service images  
**Readout:** `2026-07-10T07:26:37Z`  
**Package confidence:** **Likely** shared Debian Trixie OS layer under [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932) lineage (8/8 `library/cdb_*` services, same pattern as prior perl-base readouts). **No Trivy package probe in this slice** — do not treat `perl-base` as scan-proven for CVE-2026-53615.

| Issue | Service | Fingerprint | Verdict |
|-------|---------|-------------|---------|
| [#3945](https://github.com/jannekbuengener/Claire_de_Binare/issues/3945) | `library/cdb_allocation` | `f53ad0318d81b41c` | Child → #2932 |
| [#3946](https://github.com/jannekbuengener/Claire_de_Binare/issues/3946) | `library/cdb_db_writer` | `ef1b06eacef158d5` | Child → #2932 |
| [#3947](https://github.com/jannekbuengener/Claire_de_Binare/issues/3947) | `library/cdb_execution` | `f53be0bb4e6d6fb6` | Child → #2932 |
| [#3948](https://github.com/jannekbuengener/Claire_de_Binare/issues/3948) | `library/cdb_market` | `c779065ef9b964cf` | Child → #2932 |
| [#3949](https://github.com/jannekbuengener/Claire_de_Binare/issues/3949) | `library/cdb_regime` | `47fe72960a14dc84` | Child → #2932 |
| [#3950](https://github.com/jannekbuengener/Claire_de_Binare/issues/3950) | `library/cdb_risk` | `a9d1aa8a42124c96` | Child → #2932 |
| [#3951](https://github.com/jannekbuengener/Claire_de_Binare/issues/3951) | `library/cdb_signal` | `b92d2761e79b057c` | Child → #2932 |
| [#3952](https://github.com/jannekbuengener/Claire_de_Binare/issues/3952) | `library/cdb_ws` | `6a50fbdfdd8ba187` | Child → #2932 |

**Operational tracking:** UPSTREAM_BLOCKED (inherits #2932). Re-triage when Trivy `FixedVersion` non-empty on representative `python:3.14-slim-trixie` service image.

---

## Cluster B — CVE-2026-54369 → #3803

**Parent:** [#3803](https://github.com/jannekbuengener/Claire_de_Binare/issues/3803) — Debian Trixie `libacl1` CVE-2026-54369  
**Package confidence:** **High** — `libacl1@2.3.2-2+b1`, FixedVersion empty (evidence: [`CDB_SECURITY_OS_LAYER_3756-3765_CVE-41992_CVE-54369_VERIFY_2026-07-06.md`](CDB_SECURITY_OS_LAYER_3756-3765_CVE-41992_CVE-54369_VERIFY_2026-07-06.md))

| Issue | Service | Fingerprint | Verdict |
|-------|---------|-------------|---------|
| [#3953](https://github.com/jannekbuengener/Claire_de_Binare/issues/3953) | `library/cdb_regime` | `693fcc81ad04225c` | Child → #3803 |
| [#3954](https://github.com/jannekbuengener/Claire_de_Binare/issues/3954) | `library/cdb_risk` | `05c11356f8f3164c` | Child → #3803 |

Prior compression in #3803: #3765, #3933–#3935. These two issues are additional readout deltas on the same OS layer.

---

## #2513 meta index (2026-07-10)

Operational cluster units under parent [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513):

| Cluster | Issue | CVE / package | Scope |
|---------|-------|---------------|-------|
| perl-base (+ readout deltas) | [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932) | multiple + **CVE-2026-53615** (#3945–#3952) | 8× `python:3.14-slim-trixie` |
| Monitoring images | [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933) | Grafana/Prometheus/gosu/libxml2 | base images |
| libsqlite3 | [#3705](https://github.com/jannekbuengener/Claire_de_Binare/issues/3705) | CVE-2026-11824 | 8× Trixie |
| gzip | [#3802](https://github.com/jannekbuengener/Claire_de_Binare/issues/3802) | CVE-2026-41992 | 8× Trixie |
| libacl1 | [#3803](https://github.com/jannekbuengener/Claire_de_Binare/issues/3803) | CVE-2026-54369 (#3953–#3954 new) | all Trixie services |
| libcurl4t64 | [#3936](https://github.com/jannekbuengener/Claire_de_Binare/issues/3936) | CVE-2026-12064 | 7× Trixie cdb (not postgres alpine) |

**Open GitHub security tracking after this compression:** #2513 + **6 cluster parents** (no per-fingerprint child issues for #3945–#3954).

---

## Child closure rationale

Issues #3945–#3954 closed as **duplicate/child tracking compressed into parent cluster** — same convention as prior compressions (#3756–#3763 → #3802, #3926–#3932 → #3936). Closure does **not** imply fix, dismiss, or LR change.
