# Security Batch Matrix — Issues #2860–#2869

**Stand:** 2026-06-03 (UTC)  
**Parent epic:** [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289)  
**Readout run:** [Actions #26871768632](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/26871768632) (`2026-06-03T08:01:51Z`)  
**Scope guard:** Triage/evidence only. Kein LR-Go, keine Alert-Dismissals, keine Runtime-/Stack-Mutation.

---

## Executive summary

| Gruppe | CVE | Paket | Installed | Fixed (Trivy) | Root cause | Verdict |
|--------|-----|-------|-----------|---------------|------------|---------|
| A (#2860–#2867) | CVE-2026-42496 | `perl-base` | `5.40.1-6` | *(leer)* | Shared `python:3.11-slim-trixie` OS layer | **UPSTREAM_BLOCKED** |
| B (#2868–#2869) | CVE-2026-8376 | `perl-base` | `5.40.1-6` | *(leer)* | Shared `python:3.11-slim-trixie` OS layer | **UPSTREAM_BLOCKED** |

Issue automation erzeugte **10** Issues (Cap); weitere offene Code-Scanning-Alerts für CVE-2026-8376 existieren auf weiteren `library/cdb_*`-Images (siehe API-Stichprobe), wurden in diesem Lauf durch `capped=41` nicht materialisiert.

**Empfohlener erster Remediation-Slice:** Kein Dockerfile-/Digest-PR — kein belegter Fix. Beobachtung über #2289 / #2290 bis Debian-Trixie oder Docker-Official-Image `perl-base` patch liefert `Fixed Version`.

---

## Batch matrix

| Issue | CVE | Component | Package | Installed | Fixed version | Source layer | Fingerprint | Verdict | Evidence |
|-------|-----|-----------|---------|-----------|---------------|--------------|-------------|---------|----------|
| [#2860](https://github.com/jannekbuengener/Claire_de_Binare/issues/2860) | CVE-2026-42496 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | `python:3.11-slim-trixie` + `apt-get upgrade` | `e1a4b55dfd1e3fc2` | UPSTREAM_BLOCKED | GH code-scanning alert; Trivy message |
| [#2861](https://github.com/jannekbuengener/Claire_de_Binare/issues/2861) | CVE-2026-42496 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `575aa2f4116d7aaa` | UPSTREAM_BLOCKED | idem |
| [#2862](https://github.com/jannekbuengener/Claire_de_Binare/issues/2862) | CVE-2026-42496 | `library/cdb_execution` | `perl-base` | 5.40.1-6 | — | shared trixie base | `bdd4a47534780ff5` | UPSTREAM_BLOCKED | idem |
| [#2863](https://github.com/jannekbuengener/Claire_de_Binare/issues/2863) | CVE-2026-42496 | `library/cdb_market` | `perl-base` | 5.40.1-6 | — | shared trixie base | `31ce174bae19b62c` | UPSTREAM_BLOCKED | idem |
| [#2864](https://github.com/jannekbuengener/Claire_de_Binare/issues/2864) | CVE-2026-42496 | `library/cdb_regime` | `perl-base` | 5.40.1-6 | — | shared trixie base | `b1a7a18b3b36e18b` | UPSTREAM_BLOCKED | idem |
| [#2865](https://github.com/jannekbuengener/Claire_de_Binare/issues/2865) | CVE-2026-42496 | `library/cdb_risk` | `perl-base` | 5.40.1-6 | — | shared trixie base | `6c702c7a9dab4c6f` | UPSTREAM_BLOCKED | idem |
| [#2866](https://github.com/jannekbuengener/Claire_de_Binare/issues/2866) | CVE-2026-42496 | `library/cdb_signal` | `perl-base` | 5.40.1-6 | — | shared trixie base | `a5491faaf5993772` | UPSTREAM_BLOCKED | idem |
| [#2867](https://github.com/jannekbuengener/Claire_de_Binare/issues/2867) | CVE-2026-42496 | `library/cdb_ws` | `perl-base` | 5.40.1-6 | — | shared trixie base | `c015772b9628972e` | UPSTREAM_BLOCKED | idem |
| [#2868](https://github.com/jannekbuengener/Claire_de_Binare/issues/2868) | CVE-2026-8376 | `library/cdb_allocation` | `perl-base` | 5.40.1-6 | — | shared trixie base | `64a88b366843863f` | UPSTREAM_BLOCKED | idem |
| [#2869](https://github.com/jannekbuengener/Claire_de_Binare/issues/2869) | CVE-2026-8376 | `library/cdb_db_writer` | `perl-base` | 5.40.1-6 | — | shared trixie base | `a17110bafd6b986a` | UPSTREAM_BLOCKED | idem |

---

## Root-cause / fixability evidence

### Shared base layer (repo)

Trixie-pinned services (excerpt):

- `services/regime/Dockerfile`, `services/execution/Dockerfile`, `services/allocation/Dockerfile`, `services/market/Dockerfile`, `services/risk/Dockerfile`, `services/signal/Dockerfile`, `services/ws/Dockerfile`, `services/db_writer/Dockerfile`
- `FROM python:3.11-slim-trixie@sha256:e78299e55776ca065dcb769f80161f48465ad352014240eb5fe4712e22505e9b`
- `RUN apt-get update && apt-get upgrade -y` (bereits in #2510)

Bookworm-pinned (separater Layer, **nicht** in diesem Batch-Issue-Set): `services/candles`, `services/reports`.

### GitHub Code Scanning API (live, 2026-06-03)

Representative open alerts (Trivy rule id = CVE):

- `CVE-2026-42496` / `perl-base` 5.40.1-6 / **Fixed Version:** empty / CRITICAL
- `CVE-2026-8376` / `perl-base` 5.40.1-6 / **Fixed Version:** empty / CRITICAL

Applies across `library/cdb_*` images listed in the matrix.

### Digest refresh probe (local, 2026-06-03)

| Image digest | `perl-base` version | Trivy still reports 42496/8376 |
|--------------|---------------------|--------------------------------|
| Pinned in repo `e78299e5…` | 5.40.1-6 | yes (API + prior scans) |
| Latest Hub amd64 `67e6a605…` | 5.40.1-6 | yes (`trivy image`, no fixed version) |

**Conclusion:** `FIXABLE_NOW_SHARED_BASE` / digest-only refresh **rejected** — no newer safe digest with patched `perl-base`.

### Advisory context (non-fix)

- CVE-2026-42496: Archive::Tar in Perl — symlink extraction (AVD/Trivy text).
- CVE-2026-8376: Perl heap buffer overflow (through 5.43.10 per Trivy summary).

---

## Blast radius

- **Images:** 8× `library/cdb_*` (trixie cluster); alerts duplicate per image.
- **Runtime:** No change in this slice (upstream-blocked).
- **LR / live / echtgeld:** No impact.

---

## Holds / follow-ups

| Item | Action |
|------|--------|
| #2290 | Historical tracker for broader Trixie OS wave; overlap, keep open |
| Uncapped CVE-2026-8376 on execution/market/regime/risk/signal/ws | Next readout or manual epic slice; dedupe by CVE+component |
| `docs/security/readouts/2026-06-03/` | Referenced in #2289 comment; **not** in repo tree at triage time (artifact-only) — limitation |

---

## Validation performed for this document

- `gh issue view` 2860–2869, 2289, 2290
- `gh api …/code-scanning/alerts` filter CVE-2026-42496 / CVE-2026-8376
- `docker` + `trivy image` on current and latest `python:3.11-slim-trixie` digests
- Repo `rg` on Dockerfiles / base pins

No alert dismissals. No issue closes (no merged fix).
