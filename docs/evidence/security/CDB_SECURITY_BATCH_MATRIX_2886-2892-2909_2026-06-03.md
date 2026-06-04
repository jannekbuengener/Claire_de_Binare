# Security Batch Matrix — Issues #2886–#2892 / #2909

**Stand:** 2026-06-03 (UTC)  
**Parent epic:** [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289)  
**Prior slice:** [#2877](https://github.com/jannekbuengener/Claire_de_Binare/pull/2877) (perl-base #2860–#2869, UPSTREAM_BLOCKED)  
**Readout run:** [Actions #26871768632](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/26871768632) (`2026-06-03T08:01:51Z`)  
**Scope guard:** Triage/evidence only. Kein LR-Go, keine Alert-Dismissals, keine Runtime-/Stack-Mutation.

---

## Executive summary

| Gruppe | Issues | CVE(s) | Layer | Verdict |
|--------|--------|--------|-------|---------|
| Grafana | #2886, #2889, #2892 | CVE-2026-34040, CVE-2026-41567, CVE-2026-42306 | `grafana/grafana:12.4.3-security-02-ubuntu` binary (`moby`) | **UPSTREAM_BLOCKED** |
| Prometheus / promtool | #2887, #2888, #2890, #2891 | CVE-2026-34040, CVE-2026-41567, CVE-2026-42306 | `prom/prometheus:v3.11.3` binary (`docker/docker`) | **UPSTREAM_BLOCKED** |
| Postgres | #2909 | CVE-2026-6732 | `postgres:15.18-alpine` OS `libxml2` | **UPSTREAM_BLOCKED** |

**Remediation in this slice:** Kein Compose-/Workflow-Digest-PR — kein Image-Nachweis, der die Ziel-CVEs beseitigt. Beobachtung über #2289 bis Upstream-Rebuilds verfügbar sind.

---

## Batch matrix

| Issue | CVE | Component | Package | Installed | Fixed (Trivy) | Image / digest | GH alert | Fingerprint | Verdict |
|-------|-----|-----------|---------|-----------|---------------|----------------|----------|-------------|---------|
| [#2886](https://github.com/jannekbuengener/Claire_de_Binare/issues/2886) | CVE-2026-34040 | `usr/share/grafana/bin/grafana` | `github.com/moby/moby` | v28.0.1+incompatible | 29.3.1 (module) | grafana `…089f9dbb…` | [#4032](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4032) | `000e39e438dca786` | UPSTREAM_BLOCKED |
| [#2889](https://github.com/jannekbuengener/Claire_de_Binare/issues/2889) | CVE-2026-41567 | grafana binary | `github.com/moby/moby` | v28.0.1+incompatible | — | idem | [#4458](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4458) | `0fb3720c0ceeeb7e` | UPSTREAM_BLOCKED |
| [#2892](https://github.com/jannekbuengener/Claire_de_Binare/issues/2892) | CVE-2026-42306 | grafana binary | `github.com/moby/moby` | v28.0.1+incompatible | — | idem | [#4459](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4459) | `a065c87bf2c00e81` | UPSTREAM_BLOCKED |
| [#2887](https://github.com/jannekbuengener/Claire_de_Binare/issues/2887) | CVE-2026-41567 | `bin/prometheus` | `github.com/docker/docker` | v28.5.2+incompatible | — | prom `…e4254400…` | [#4433](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4433) | `6bd10cd107e98482` | UPSTREAM_BLOCKED |
| [#2888](https://github.com/jannekbuengener/Claire_de_Binare/issues/2888) | CVE-2026-41567 | `bin/promtool` | `github.com/docker/docker` | v28.5.2+incompatible | — | idem | [#4436](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4436) | `2815609d580739b9` | UPSTREAM_BLOCKED |
| [#2890](https://github.com/jannekbuengener/Claire_de_Binare/issues/2890) | CVE-2026-42306 | `bin/prometheus` | `github.com/docker/docker` | v28.5.2+incompatible | — | idem | [#4434](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4434) | `6c8bb263fefa55a0` | UPSTREAM_BLOCKED |
| [#2891](https://github.com/jannekbuengener/Claire_de_Binare/issues/2891) | CVE-2026-42306 | `bin/promtool` | `github.com/docker/docker` | v28.5.2+incompatible | — | idem | [#4437](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4437) | `3cdab6351bf316a3` | UPSTREAM_BLOCKED |
| [#2909](https://github.com/jannekbuengener/Claire_de_Binare/issues/2909) | CVE-2026-6732 | `library/postgres` | `libxml2` | 2.13.9-r0 | 2.13.9-r1 | postgres `…df7bca00…` | [#4582](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4582) | `a6f89a4ed838c37b` | UPSTREAM_BLOCKED |

Pinned references (repo @ `61d8c4bf`):

- `postgres:15.18-alpine@sha256:df7bca0066e6f60cc3dd32faa70caddec20e2c22b58932f79498e5704b23854a`
- `prom/prometheus:v3.11.3@sha256:e4254400b85610324913f0dc4acf92603d9984e7519414c5a12811aa6146acc3`
- `grafana/grafana:12.4.3-security-02-ubuntu@sha256:089f9dbbfa3c21e6989aab20f14f1a78cef54c04819af5e9deb2bd9c37966bc5`

Sources: `infrastructure/compose/base.yml`, `compose.blue.yml`, `.github/workflows/security-scan.yml` (`trivy-scan-base`).

---

## Root-cause / fixability evidence

### Grafana / Prometheus (embedded Go modules)

Trivy `trivy-scan-base` classifies findings on **static binaries** inside upstream images, not on a CDB-controlled Dockerfile layer. CVE-2026-41567 and CVE-2026-42306 report **empty** fixed versions in GitHub Code Scanning. CVE-2026-34040 lists module fix `29.3.1` for `moby`/`docker` — requires upstream image rebuild, not a digest-only pin of the current tags.

**Conclusion:** `FIXABLE_NOW_DIGEST_REFRESH` / `FIXABLE_NOW_MINOR_IMAGE_BUMP` **rejected** for this slice — no scanned candidate image clears the alerts without unproven tag migration.

### Postgres (Alpine OS package)

| Probe | Result |
|-------|--------|
| `docker pull postgres:15.18-alpine` (2026-06-03) | Digest unchanged: `sha256:df7bca00…` |
| `apk info libxml2` in image | **2.13.9-r0** |
| `trivy image` (0.71.0) | CVE-2026-6732 HIGH, fixed in **2.13.9-r1**, still present |

**Conclusion:** `FIXABLE_NOW_DIGEST_REFRESH` **rejected** until [docker-library/postgres](https://github.com/docker-library/postgres) publishes `15.18-alpine` with `libxml2>=2.13.9-r1` and a **new** digest is scan-verified.

### GitHub Code Scanning API (live, 2026-06-03)

Filtered Trivy alerts for CVE-2026-34040, CVE-2026-41567, CVE-2026-42306, CVE-2026-6732 — alert numbers in matrix above; all `state: open` on `main`.

---

## Ask-Gordon gate (historical / decommissioned)

| Item | Status |
|------|--------|
| Infra / compose / digest diff in this slice | **None** (docs-only) |
| Ask-Gordon integration in repo | Not found; historical reference only |
| Gate outcome | **N/A** — no infra mutation; documented as repo-only triage |

---

## Re-triage triggers

| Component | Trigger |
|-----------|---------|
| Postgres | New `postgres:15.18-alpine` (or patched minor) digest with `libxml2>=2.13.9-r1` + Trivy clear for CVE-2026-6732 |
| Prometheus | New `prom/prometheus` release rebuild without vulnerable `docker/docker` embedding for CVE-2026-41567 / CVE-2026-42306 / CVE-2026-34040 |
| Grafana | New `grafana/grafana` security build without vulnerable `moby` embedding for same CVE family |

---

## Blast radius

- **Images:** 3 base scan targets (postgres, prometheus, grafana) in `security-scan.yml`; compose pins aligned.
- **Runtime:** No change in this slice.
- **LR / live / echtgeld:** No impact.

---

## Validation performed for this document

- `gh issue view` #2289, #2886–#2892, #2909
- `gh api …/code-scanning/alerts` (Trivy, target CVEs)
- `git rev-parse` @ `61d8c4bf` on branch `security/2886-2892-2909-image-cve-triage`
- `docker pull` + `apk info` + `trivy image` on pinned `postgres:15.18-alpine` digest

No alert dismissals. No issue closes (no merged image fix).
