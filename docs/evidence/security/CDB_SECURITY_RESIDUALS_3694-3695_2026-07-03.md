# Security Residuals — Issues #3694 / #3695 (CVE-2026-27145)

**Stand:** 2026-07-03 (UTC)  
**Readout source:** Security Alert Readout `2026-07-03T07:24:19Z`  
**Parent residual program:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Cluster tracker:** [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933)  
**Related fix slice:** PR [#3702](https://github.com/jannekbuengener/Claire_de_Binare/pull/3702) (Prometheus v3.13.0 — closes #3692, #3693, #3696–#3701)  
**Scope guard:** Documentation-only residual tracking. Kein LR-Go, keine Alert-Dismissals, keine Runtime-/Image-Pin-Aktion in diesem Slice.

---

## Executive summary

| Issue | Component | Fingerprint | CVE | Base image / service | Verdict |
|-------|-----------|-------------|-----|----------------------|---------|
| [#3694](https://github.com/jannekbuengener/Claire_de_Binare/issues/3694) | `usr/local/bin/gosu` | `7aad46e90ac8aa27` | CVE-2026-27145 | `postgres:18.4-alpine` (`cdb_postgres`) | **UPSTREAM_BLOCKED** |
| [#3695](https://github.com/jannekbuengener/Claire_de_Binare/issues/3695) | `usr/share/grafana/data/plugins-bundled/elasticsearch/gpx_grafana_elasticsearch_datasource_linux_amd64` | `134e6d69275a8c4b` | CVE-2026-27145 | `grafana/grafana:13.0.3-ubuntu` (`cdb_grafana`) | **UPSTREAM_BLOCKED** |

**Batch context:** Nach dem Prometheus/Promtool-Fix (#3692–#3701 via PR #3702) bleiben diese zwei Alerts als einzige nicht direkt fixbare HIGH-Befunde aus dem CVE-2026-27145-Readout offen.

---

## #3694 — gosu in Postgres base image

### Finding

- **Alert path:** `usr/local/bin/gosu`
- **Scanner:** Trivy Code Scanning (`code_scanning`, band `high`)
- **CVE:** CVE-2026-27145 — Go stdlib `crypto/x509` algorithmic DoS
- **Fixed in:** Go 1.25.11 / 1.26.4 (per advisory metadata; same class as prior gosu stdlib CVEs)

### CDB layer analysis

| Layer | Detail |
|-------|--------|
| **Service** | `cdb_postgres` (BLUE core) |
| **Image pin** | `postgres:18.4-alpine@sha256:1b1689b20d16a014a3d195653381cf2caa75a41a92d93b255a9d6ea29fd353aa` |
| **Compose** | `infrastructure/compose/base.yml`, `infrastructure/compose/compose.blue.yml` |
| **Trivy matrix** | `.github/workflows/security-scan.yml` (`trivy-scan-base`, `scan_name: postgres`) |
| **CDB code fix** | **None available** — gosu is embedded by upstream `docker-library/postgres`; CDB does not build or patch this binary |

### Risk posture (accepted, documented)

gosu is a **startup-only privilege-drop helper** inside the Postgres/Redis base images. It runs at container init to drop root, then exits. It has **no network listener** and no runtime attack surface after startup.

Prior accepted-risk documentation:

- `docs/security/TRIAGE_RUNBOOK.md` — Cluster `gosu-base-image` (§4)
- `.github/workflows/security-scan.yml` — Known Issues summary (gosu Go stdlib CVEs, incl. CVE-2026-42504)
- `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3065-3070-CVE-42504_2026-06-08.md` — gosu sub-cluster under #2933 (#3067)

CVE-2026-27145 is another Go-stdlib CVE in the **same gosu binary class**. No separate CDB mitigation is warranted beyond upstream image rebuild tracking.

### Fixability

| Probe | Result |
|-------|--------|
| CDB Dockerfile / patch path | None — consume-only base image |
| Upstream rebuild with Go ≥1.25.11/≥1.26.4 in gosu | **Not scan-verified** as of 2026-07-03 |
| Postgres semver bump alone | Does not clear gosu stdlib CVE without upstream gosu rebuild |

**Conclusion:** **UPSTREAM_BLOCKED** — tracked under [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933) gosu sub-cluster (extends prior #3067 lineage).

---

## #3695 — Grafana bundled Elasticsearch plugin

### Finding

- **Alert path:** `usr/share/grafana/data/plugins-bundled/elasticsearch/gpx_grafana_elasticsearch_datasource_linux_amd64`
- **Scanner:** Trivy Code Scanning (`code_scanning`, band `high`)
- **CVE:** CVE-2026-27145 — Go stdlib `crypto/x509` algorithmic DoS
- **Refs in alert body:** #2289, #2292

### CDB layer analysis

| Layer | Detail |
|-------|--------|
| **Service** | `cdb_grafana` (RED monitoring) |
| **Image pin** | `grafana/grafana:13.0.3-ubuntu@sha256:7c1acd41225a05af53fa2af32a044a2a96cdef2540f2c415ee5b1e98fae99084` |
| **Compose** | `infrastructure/compose/base.yml`, `infrastructure/compose/compose.red.yml` |
| **Trivy matrix** | `.github/workflows/security-scan.yml` (`trivy-scan-base`, `scan_name: grafana`) |
| **CDB usage** | CDB provisions Prometheus/Postgres datasources only; **Elasticsearch bundled plugin is not enabled or provisioned** in CDB Grafana config |
| **Main Grafana binaries** | `usr/share/grafana/bin/grafana`, `grafana-cli`, `grafana-server` — separate scan targets; cleared or tracked in prior #2933 sub-clusters |

### Risk posture

The vulnerable artifact is a **bundled but unused** Elasticsearch datasource plugin shipped inside the upstream Grafana image. CDB does not mount, enable, or route traffic through this plugin. Primary Grafana server binaries are the operational surface; this plugin binary is dead weight from upstream packaging.

### Fixability

| Probe | Result |
|-------|--------|
| CDB code fix (remove plugin from image) | **Not available** — CDB consumes upstream image as-is |
| Grafana security rebuild clearing bundled plugin | **Not scan-verified** as of 2026-07-03 |
| Blind Grafana semver bump | Out of scope without scan-verified upstream fix |

**Conclusion:** **UPSTREAM_BLOCKED** — tracked under [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933) Grafana sub-cluster (new fingerprint; bundled-plugin layer distinct from main `bin/grafana` targets).

---

## Tracker consolidation

| Role | Issue | Action in this slice |
|------|-------|----------------------|
| Parent program | [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513) | Index only — no body change |
| Monitoring/postgres cluster | [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933) | #3694 → gosu sub-cluster; #3695 → Grafana bundled-plugin sub-cluster |
| Per-fingerprint alerts | #3694, #3695 | GitHub issue comments; dedupe closure per #2933 convention if unambiguous |

**Code Scanning alerts remain OPEN** — no dismissals, no SARIF hiding, no false-resolved claims.

---

## Re-triage triggers

| Component | Trigger |
|-----------|---------|
| gosu / Postgres | `docker-library/postgres` publishes base image with gosu rebuilt on Go ≥1.25.11/≥1.26.4; Trivy scan on pinned digest shows CVE-2026-27145 absent |
| gosu / Redis | Same for `docker-library/redis` (gosu also embedded; postgres alert is the reported fingerprint for this readout) |
| Grafana bundled ES plugin | New `grafana/grafana` security build scan-verified clear for fingerprint `134e6d69275a8c4b` |
| Grafana main binaries | Covered by existing #2933 Grafana sub-cluster re-triage rules |

Monitor upstream:

- https://github.com/docker-library/postgres/issues
- https://github.com/docker-library/redis/issues
- https://github.com/grafana/grafana/releases

---

## Safety boundaries

- No alert dismissals without separate Human-GO.
- No runtime recreate, Docker pull, Compose up/down, or image pin changes in this slice.
- No LR / live-readiness / Echtgeld implication.
- LR remains **NO-GO**.

---

## Validation commands

```bash
git diff --check
rg "3694|3695|27145|gosu|elasticsearch" docs/evidence/security docs/runbooks/CONTROL_REGISTER.md
gh issue view 3694
gh issue view 3695
gh issue view 2933
gh issue view 2513
```
