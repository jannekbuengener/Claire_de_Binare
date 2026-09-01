# CDB Security Alert Wave #4516–#4525 (2026-09-01)

Machine-readable twin: [`CDB_SECURITY_ALERT_WAVE_4516-4525_2026-09-01.json`](./CDB_SECURITY_ALERT_WAVE_4516-4525_2026-09-01.json)

## Scope

Reconcile the ten Security Alert Readout issues from 2026-09-01 (`#4516`–`#4525`).
Both CVE clusters remain **upstream-blocked** on Debian Trixie. No Dockerfile
remediation, no alert dismissal, no `.trivyignore` growth, no LR/live implication.

| Field | Value |
| --- | --- |
| `origin/main` base | `41b5c04aeb4826888e7eff00ccba9d1350cfda84` |
| Readout timestamp | `2026-09-01T06:41:31Z` |
| Routing | `CREATE_DEDICATED_PR` |
| Branch | `cloud-cursor/security-wave-4516-4525-1048` |

## Brain Evidence (session)

- `brain_source`: repo-only
- `brain_status`: not-used
- `context_brain_attempted`: true
- `context_brain_used`: false
- `context_available`: false
- `repo_fallback_used`: true
- `repo_fallback_reason`: unavailable
- `context_tool_status`: absent
- `context_trust_level`: none
- `records_found`: none

## Cluster summary

| Cluster | CVE | Issues | Package | Installed | Trivy FixedVersion | Verdict | Canonical tracker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| perl-base | CVE-2026-57432 | #4516–#4521 | `perl-base` | `5.40.1-6` | empty | UPSTREAM_HOLD | **#2932** |
| curl/libcurl | CVE-2026-8927 | #4522–#4525 | `curl`/`libcurl4t64` | `8.14.1-2+deb13u4` | empty | UPSTREAM_HOLD | **#4080** |

**Scope guard for perl:** Issue #4114 remains intentionally narrow
(allocation + db_writer only). The six new perl alerts (#4516–#4521) consolidate
under the global perl cluster **#2932**, not #4114.

## Live probe evidence (2026-09-01)

**Tool:** Trivy `0.74.0` · **Image:** `cdb_risk:wave4516-probe` (built from
`services/risk/Dockerfile` on pinned `python:3.14-slim-trixie@cea0e604…14a6`)

| CVE | Package | Installed | FixedVersion |
| --- | --- | --- | --- |
| CVE-2026-57432 | perl-base | 5.40.1-6 | null |
| CVE-2026-8927 | curl | 8.14.1-2+deb13u4 | null |
| CVE-2026-8927 | libcurl4t64 | 8.14.1-2+deb13u4 | null |

**Debian Security Tracker (CVE-2026-57432):** trixie `5.40.1-6` **vulnerable**;
forky/sid `5.42.3-1` fixed; trixie note `<no-dsa>` (Minor issue).

**Digest refresh probe:** Latest Hub amd64 `python:3.14-slim-trixie`
(`sha256:810da627…`) still ships `perl-base 5.40.1-6` — no remediation path.

**Fixability probes rejected:**

- `apt-get upgrade -y` (already in Dockerfiles) — no gain
- Digest-only base refresh — still vulnerable
- `perl-base=5.40.1-8` from forky — not in trixie suite
- Cross-suite curl 8.21.0 pin — forbidden without approved suite migration

## Exploitability (CDB runtime)

| CVE | CDB exposure |
| --- | --- |
| CVE-2026-57432 | Essential OS package; Python services do not invoke Perl pack/unpack templates — low direct exploitability |
| CVE-2026-8927 | curl used for HTTP HEALTHCHECK only; advisory states CLI curl unaffected; no proven libcurl env-proxy Digest handle-reuse path — low practical exploitability |

## Issue disposition

| Issue | Component | Disposition | Close after merge |
| --- | --- | --- | --- |
| #4516 | cdb_execution | HOLD (wave rep) → #2932 | duplicate close |
| #4517 | cdb_market | DUPLICATE → #2932 | duplicate close |
| #4518 | cdb_regime | DUPLICATE → #2932 | duplicate close |
| #4519 | cdb_risk | DUPLICATE → #2932 | duplicate close |
| #4520 | cdb_signal | DUPLICATE → #2932 | duplicate close |
| #4521 | cdb_ws | DUPLICATE → #2932 | duplicate close |
| #4522 | cdb_regime | HOLD (wave rep) → #4080 | duplicate close |
| #4523 | cdb_risk | DUPLICATE → #4080 | duplicate close |
| #4524 | cdb_signal | DUPLICATE → #4080 | duplicate close |
| #4525 | cdb_ws | DUPLICATE → #4080 | duplicate close |

**Code Scanning alerts:** All 10 alerts remain **open** after issue closure.
No alert dismissal.

## Re-evaluation trigger (single next probe)

**2026-09-15:** Re-probe Debian Trixie + Trivy FixedVersion for `perl-base`
(#2932) and `curl`/`libcurl4t64` (#4080) on a representative rebuilt
`python:3.14-slim-trixie` service image.

## Non-goals / boundaries

- No fake package pins, no cross-suite installs
- No expansion of #4114 scope
- No BLUE/RED runtime mutation
- LR remains **NO-GO**
