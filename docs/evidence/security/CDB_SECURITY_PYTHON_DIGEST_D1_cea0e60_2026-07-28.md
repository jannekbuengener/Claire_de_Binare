# Python base digest D1 — `b877e50` → `cea0e60`

**Date:** 2026-07-28  
**Scope:** `python:3.14-slim-trixie` digest bump in service Dockerfiles  
**Supersedes Dependabot:** #4134 #4136 #4137 #4138 #4139 #4140 #4142 #4143  
**Tool:** Trivy 0.72.0 (DB refreshed 2026-07-28), severity HIGH+CRITICAL  

## Images compared

| Role | Ref |
|---|---|
| Old | `python:3.14-slim-trixie@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1` |
| New | `python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6` |

Tag semantic unchanged: `python:3.14-slim-trixie` (no Python major/minor change).

## Vulnerability delta (HIGH/CRITICAL)

| Metric | Count |
|---|---|
| Old HIGH/CRITICAL findings | 23 |
| New HIGH/CRITICAL findings | 23 |
| Cleared | **0** |
| Introduced | **0** |
| Unchanged residual set | 23 |

Residual set includes known upstream-blocked clusters (e.g. `perl-base` CVE-2026-13221 / related, `gzip` CVE-2026-41992, `util-linux` CVE-2026-53615). Tracked under existing security residual issues (#4106, #2932, #3802, …). **No new HIGH/CRITICAL introduced by this digest move.**

## Artifacts (local evidence dir)

- `trivy-d1-old-b877e50.json` / `.txt`
- `trivy-d1-new-cea0e60.json` / `.txt`

## Boundaries

- No BLUE/RED start, no image push, no productive DB mutation.
- SKIPPED heavy security stage alone is **not** used as merge evidence; this targeted Trivy delta is the required image proof.
