# Label Rename Audit: `pipeline:generated` -> `ci:generated`

Date: 2026-02-19
Branch: `ci/rename-generated-label`

## Scope
- Label/workflow metadata and audit docs only.
- No Docker/Compose/Dockerfile changes.
- No trading logic changes.

## Discovery Result
- No repository references to `pipeline:generated` were found in:
  - `.github/workflows/**`
  - `.github/ISSUE_TEMPLATE/**`
  - `.github/pull_request_template.md`
  - `docs/**`
  - `docs/evidence/reports/**`

## Change Applied
- Added `ci:generated` to `.github/workflows/labels.json` with canonical metadata:
  - name: `ci:generated`
  - color: `0e8a16`
  - description: `Auto-created by CI`

## Compatibility Decision
- Migration mode: complete in-repo migration (no in-repo `pipeline:generated` usages existed).
- No alias entry was added because there were no old references to preserve in repository files.

## Audit Note
- This documents the rename intent from `pipeline:generated` to `ci:generated`.
