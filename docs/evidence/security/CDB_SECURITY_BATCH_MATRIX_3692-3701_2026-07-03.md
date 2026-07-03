# Security Batch Matrix — Issues #3692–#3701 / CVE-2026-27145 + CVE-2026-39827/28/29

**Stand:** 2026-07-03 (UTC)  
**Parent epic:** [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289)  
**Related trackers:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513), [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933)  
**Branch:** `fix/3692-prometheus-v3.13.0`  
**Scope guard:** Image-pin bump only. Kein LR-Go, keine Alert-Dismissals, keine Grafana/Postgres/Redis-Änderung.

---

## Executive summary

| Gruppe | Issues | CVEs | Package / Layer | Vulnerable pin | Target pin | Verdict |
|--------|--------|------|-----------------|----------------|------------|---------|
| Prometheus / promtool | #3692–#3701 (8) | CVE-2026-27145, CVE-2026-39827, CVE-2026-39828, CVE-2026-39829 | Go stdlib + `golang.org/x/crypto` in `bin/prometheus`, `bin/promtool` | `prom/prometheus:v3.12.0@sha256:69f524…` | `v3.13.0@sha256:c6b27ea…` | **FIXABLE_NOW** |

**Out of scope (separate upstream-blocked tracking under #2933):** #3694 (gosu/postgres), #3695 (Grafana bundled elasticsearch plugin).

---

## Batch matrix

| Issue | Component | Fingerprint | CVE | Verdict |
|-------|-----------|-------------|-----|---------|
| [#3692](https://github.com/jannekbuengener/Claire_de_Binare/issues/3692) | `bin/prometheus` | `015cd9342c37aed6` | CVE-2026-27145 | FIXED_BY_PIN |
| [#3693](https://github.com/jannekbuengener/Claire_de_Binare/issues/3693) | `bin/promtool` | `d5a63d2033384ecd` | CVE-2026-27145 | FIXED_BY_PIN |
| [#3696](https://github.com/jannekbuengener/Claire_de_Binare/issues/3696) | `bin/prometheus` | `666cca4c30cf10ac` | CVE-2026-39827 | FIXED_BY_PIN |
| [#3697](https://github.com/jannekbuengener/Claire_de_Binare/issues/3697) | `bin/promtool` | `1019d04986b6c3f8` | CVE-2026-39827 | FIXED_BY_PIN |
| [#3698](https://github.com/jannekbuengener/Claire_de_Binare/issues/3698) | `bin/prometheus` | `a3048f2b8c69923e` | CVE-2026-39828 | FIXED_BY_PIN |
| [#3699](https://github.com/jannekbuengener/Claire_de_Binare/issues/3699) | `bin/promtool` | `8061de20942c9469` | CVE-2026-39828 | FIXED_BY_PIN |
| [#3700](https://github.com/jannekbuengener/Claire_de_Binare/issues/3700) | `bin/prometheus` | `94426d7b1c253c5e` | CVE-2026-39829 | FIXED_BY_PIN |
| [#3701](https://github.com/jannekbuengener/Claire_de_Binare/issues/3701) | `bin/promtool` | `52ea2da1064f885a` | CVE-2026-39829 | FIXED_BY_PIN |

Readout source: Security Alert Readout `2026-07-03T07:24:19Z`.

---

## Root-cause / fixability evidence

### CVE-2026-27145 (Go stdlib `crypto/x509` DoS)

| Probe | Result |
|-------|--------|
| Vulnerable pin `v3.12.0@69f524…` | stdlib **v1.26.3** in prometheus + promtool; FixedVersion **1.25.11, 1.26.4** |
| Target pin `v3.13.0@c6b27ea…` | **0 hits** for CVE-2026-27145 |

### CVE-2026-39827 / CVE-2026-39828 / CVE-2026-39829 (`golang.org/x/crypto`)

| Probe | Result |
|-------|--------|
| Vulnerable pin `v3.12.0@69f524…` | `golang.org/x/crypto` **v0.51.0**; FixedVersion **0.52.0** in prometheus + promtool |
| Target pin `v3.13.0@c6b27ea…` | **0 hits** for all three CVEs |

### Trivy local rescan (0.72.0, 2026-07-03)

```text
trivy image prom/prometheus:v3.13.0@sha256:c6b27ea434f8389bfe233fbc7be381cf50587c286e871bc842008f5a1b1908a7
→ HIGH/CRITICAL total: 0
→ Target CVEs (27145, 39827, 39828, 39829): absent
```

**Conclusion:** `UPSTREAM_BLOCKED` **rejected** — scan-verified upstream release clears all eight alert fingerprints via single digest pin.

---

## Changed files (this slice)

| File | Change |
|------|--------|
| `infrastructure/compose/compose.red.yml` | Prometheus image → v3.13.0 |
| `infrastructure/compose/base.yml` | Prometheus image → v3.13.0 |
| `.github/workflows/security-scan.yml` | `trivy-scan-base` prometheus matrix → v3.13.0 |
| `infrastructure/compose/compose.prometheus-v3.yml` | Canary comment + image aligned |
| `knowledge/governance/SERVICE_CATALOG.md` | Prometheus catalog line aligned |

**Not changed:** Grafana, Redis, Postgres pins; no runtime recreate; no alert dismissals.

---

## Post-merge verification

Code Scanning alerts for fingerprints `015cd9342c37aed6` … `52ea2da1064f885a` close after next successful `security-scan.yml` SARIF upload on `main` with updated matrix pin. No manual dismissals.

---

## Safety boundaries

- No alert dismissals without separate Human-GO.
- No LR / live-readiness / Echtgeld implication.
- #3694 / #3695 remain **UPSTREAM_BLOCKED** under [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933).

---

## Validation commands

```bash
git diff --check
rg 69f5241418838263316593f7274a304b095c40bcf22e57272865da91bd60a8ac
rg c6b27ea434f8389bfe233fbc7be381cf50587c286e871bc842008f5a1b1908a7
trivy image prom/prometheus:v3.13.0@sha256:c6b27ea434f8389bfe233fbc7be381cf50587c286e871bc842008f5a1b1908a7
```
