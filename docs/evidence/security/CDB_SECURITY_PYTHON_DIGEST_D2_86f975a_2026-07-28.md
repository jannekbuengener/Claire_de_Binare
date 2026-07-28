# Python base digest D2 — `4ff4b92` → `86f975a`

**Date:** 2026-07-28  
**Scope:** `python:3.14-slim-bookworm` digest bump (candles, reports, compose Dockerfile.test)  
**Supersedes Dependabot:** #4133 #4135 #4141  
**Tool:** Trivy 0.72.0, severity HIGH+CRITICAL, scanners=vuln  

## Images compared

| Role | Ref |
|---|---|
| Old | `python:3.14-slim-bookworm@sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9` |
| New | `python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30` |

OS note: Debian 12.14 → 12.15 under same tag family. Tag semantic unchanged (`python:3.14-slim-bookworm`).

## Vulnerability delta (HIGH/CRITICAL CVE IDs)

| Metric | Count |
|---|---|
| Old | 14 |
| New | 14 |
| Cleared | **0** |
| Introduced | **0** |

Neutral digest rebuild; no new HIGH/CRITICAL CVE IDs introduced.

## Boundaries

- No BLUE/RED start, no image push.
- Targeted Trivy delta is merge evidence (not SKIPPED security stage alone).
