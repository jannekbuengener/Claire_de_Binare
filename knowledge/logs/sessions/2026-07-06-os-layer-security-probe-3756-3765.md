# Session: OS-layer Security Probe #3756–#3765

**Date:** 2026-07-06  
**Branch:** `docs/security-probe-3756-3765-os-layer`  
**Merge:** PR #3804 @ `8e6ab1001ae04222b5400c7eda1cd05b017731d8`  
**Status:** DONE_EVIDENCE_MERGED_UPSTREAM_BLOCKED

## Scope

Trivy probe + evidence documentation for CVE-2026-41992 (gzip) and CVE-2026-54369 (libacl1) on `python:3.14-slim-trixie` service images. No remediation, no alert dismissals, no issue closures.

## Delivered

- Evidence: `docs/evidence/security/CDB_SECURITY_OS_LAYER_3756-3765_CVE-41992_CVE-54369_VERIFY_2026-07-06.md`
- Parent clusters: #3802 (gzip), #3803 (libacl1)
- Comments on #3756–#3765
- PR #3804 merged (required checks green)

## Scanner evidence

- Trivy `0.72.0`, vuln DB `2026-07-06T08:09:55Z`
- `cdb-risk-probe:3756-3765`: gzip `1.13-1`, libacl1 `2.3.2-2+b1`, both `FixedVersion` null
- Base `python:3.14-slim-trixie@sha256:b877e50…`: same findings

## Decision

UPSTREAM_BLOCKED — observe under #2513, #3802, #3803 until Debian Trixie security updates.

## Boundaries

- LR NO-GO unchanged
- PR #3755 untouched
- No runtime/BLUE/RED changes

## Restunsicherheiten

- `cdb_allocation` full image build blocked locally (Docker context `.tmp/pytest-cdb`); OS-layer confirmed via `cdb_risk` probe + base scan.

## Ledger follow-up

- `CURRENT_STATUS.md` 2026-07-06 block: OS-layer probe verdict `DONE_EVIDENCE_MERGED_UPSTREAM_BLOCKED` recorded (Refs #3802, #3803, #3804; alerts #3756–#3765 stay OPEN).
