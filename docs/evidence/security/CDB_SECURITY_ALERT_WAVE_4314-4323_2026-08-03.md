# CDB Security Alert Wave #4314–#4323 (2026-08-03)

Machine-readable twin: [`CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.json`](./CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.json)

## Scope

Triage and bounded remediation for the ten Security Alert Readout issues created
2026-08-03 (`#4314`–`#4323`). Merge mode is **false**. No alert dismissal, no
`trivyignore` growth, no LR/live/echtgeld implication.

| Field | Value |
| --- | --- |
| `origin/main` base | `a52a0e90b702cd2758736bfa4ed25e2b9fd382ab` |
| Readout run | [30803956049](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/30803956049) (SUCCESS on same SHA) |
| Routing | `CREATE_DEDICATED_PR` (preferred objective `security-alert-wave-2026-08-03`) |
| Branch | `dedicated/security-alert-wave-2026-08-03` |
| Cap-45 candidates | **OUT OF SCOPE** (documented only) |

## Brain Evidence (session)

- `brain_source`: repo-only
- `brain_status`: not-used
- `context_brain_attempted`: true
- `context_brain_used`: false
- `context_available`: false
- `repo_fallback_used`: true
- `repo_fallback_reason`: insufficient_evidence
- `context_tool_status`: available
- `context_trust_level`: none
- `records_found`: none

## Live alert inventory (revalidated)

| Issue | Alert | Rule | Component | Installed | FixedVersion | State |
| --- | --- | --- | --- | --- | --- | --- |
| #4314 | 5580 | CVE-2026-57433 | library/cdb_allocation | perl-base 5.40.1-6 | *(empty)* | open |
| #4315 | 5571 | CVE-2026-57433 | library/cdb_db_writer | perl-base 5.40.1-6 | *(empty)* | open |
| #4316 | 5583 | CVE-2026-57433 | library/cdb_execution | perl-base 5.40.1-6 | *(empty)* | open |
| #4317 | 5574 | CVE-2026-57433 | library/cdb_market | perl-base 5.40.1-6 | *(empty)* | open |
| #4318 | 5536 | CVE-2026-57433 | library/cdb_regime | perl-base 5.40.1-6 | *(empty)* | open |
| #4319 | 5530 | CVE-2026-57433 | library/cdb_risk | perl-base 5.40.1-6 | *(empty)* | open |
| #4320 | 5533 | CVE-2026-57433 | library/cdb_signal | perl-base 5.40.1-6 | *(empty)* | open |
| #4321 | 5577 | CVE-2026-57433 | library/cdb_ws | perl-base 5.40.1-6 | *(empty)* | open |
| #4322 | 5677 | GHSA-r277-6w6q-xmqw | usr/share/grafana/bin/grafana | kin-openapi v0.133.0 | 0.144.0 | open |
| #4323 | 5585 | CVE-2026-56852 | bin/prometheus | golang.org/x/text v0.38.0 | 0.39.0 | open |

Alert create dates are historical (2026-07-14/15/31); issues were generated 2026-08-03.

## Clusterbildung (after per-issue triage)

1. **perl-storable-cve-2026-57433** — `#4314`–`#4321` → HOLD under canonical `#2932`
2. **grafana-kin-openapi-ghsa-r277** — `#4322` → HOLD under canonical `#2933`
3. **prometheus-x-text-cve-2026-56852** — `#4323` → FIX_READY (pin wiring complete)

## Prometheus remediation (#4323)

PR [#4310](https://github.com/jannekbuengener/Claire_de_Binare/pull/4310) already moved
`compose.red.yml` and `compose.prometheus-v3.yml` to
`prom/prometheus:v3.13.2@sha256:508729e0e2d18e11fd742a5a5ca70e557b940a93948c3c95fd0123a6fd538b69`.
Stale surfaces on `origin/main` before this wave:

- `infrastructure/compose/base.yml` still `v3.13.1`
- `.github/workflows/security-scan.yml` still `v3.13.1`
- `knowledge/governance/SERVICE_CATALOG.md` still `v3.13.1`

This wave syncs stale Prometheus pins in `base.yml`, `security-scan.yml`, and
`SERVICE_CATALOG.md` to the verified `v3.13.2` digest. `compose.red.yml` and
the prometheus-v3 overlay image were already current after #4310; the overlay
comment was updated to say `v3.13.2`. Grafana `base.yml` / scan / catalog pins
are aligned to the already-merged RED `13.1.1` digest for consistency only
(not a GHSA fix).

### Scan evidence

| Image | CVE-2026-56852 | HIGH/CRITICAL total |
| --- | --- | --- |
| `prom/prometheus:v3.13.1@sha256:3c42b892…` | **2** (`bin/prometheus`, `bin/promtool`, x/text v0.38.0) | present |
| `prom/prometheus:v3.13.2@sha256:508729e0…` | **0** | **0** |

`promtool check config` / `check rules` against repo monitoring configs: SUCCESS.

**Closure for #4323:** only after this PR merges **and** post-merge recount shows
alert `5585` cleared. No `Closes #4323` in the PR body.

## Perl HOLD (#4314–#4321 → #2932)

- Trivy FixedVersion empty on all eight alerts.
- Debian Security Tracker: **trixie** `perl` 5.40.1-6 remains **vulnerable** for
  CVE-2026-57433; fix present in **forky/sid** (`5.42.2-3`) only.
- Forbidden: forky/sid mix into Trixie, Alpine migration, unsupported perl
  backport, `trivyignore`, alert dismissal.
- Repo search: no CDB service call path uses Perl `Storable` thaw/retrieve.
- Package remains present via `python:*-slim-trixie` base images.
- Canonical tracker: [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932)
- Absolute re-eval date: **2026-09-03**
- Duplicates marked; **issues stay open** until suite-native FixedVersion + scan clear.

## Grafana HOLD (#4322 → #2933)

- Alert `5677` (scanned against older `13.0.3` path) reports kin-openapi `v0.133.0`,
  Fixed `0.144.0`.
- Local Trivy on repo RED digest
  `grafana/grafana:13.1.1-ubuntu@sha256:5a9df011…` still reports
  **GHSA-r277-6w6q-xmqw** with kin-openapi **v0.140.0** (still < 0.144.0).
- Also still has CVE-2026-56852 on Grafana binaries (x/text < 0.39.0).
- Docker Hub: no newer supported `13.1.x` / `13.2.x-ubuntu` release beyond
  `13.1.1-ubuntu` found at triage time that claims kin-openapi ≥ 0.144.0.
- Pin sync of `base.yml` / `security-scan.yml` / catalog to the already-merged
  RED `13.1.1` digest is **consistency only**, not a GHSA fix claim.
- Forbidden: Grafana source patch / vendoring.
- Canonical tracker: [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933)
- Absolute re-eval date: **2026-09-03**

## Related merged work (do not reuse)

- PR [#4303](https://github.com/jannekbuengener/Claire_de_Binare/pull/4303) merged;
  branch `dedicated/security-backlog-reconciliation-2513` must not be re-pushed.
- Meta residual trackers remain open: [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513),
  [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932),
  [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933).

## Safety boundaries

- LR = **NO-GO**
- No live / Echtgeld / productive deploy
- No alert dismissal / mutation
- No merge / no `cdb-local-ci` publish in this delivery wave
- No productive DB / MCP mutations
- Cap-45 readout candidates untouched
