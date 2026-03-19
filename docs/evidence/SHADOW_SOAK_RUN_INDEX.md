# Shadow + Soak Run Index

- Scope: `#706`
- Focus run: `21411382144`
- Last updated: `2026-03-10`

This file is a navigation index for shadow/soak workflow evidence. It does not
reconstruct missing run artifacts.

## 1. Repo Finding for Run 21411382144

- No direct repo-local reference to `21411382144` is committed today.
- No unpacked evidence directory for that run is committed under `evidence-*`.
- Because of that, this file documents the canonical audit path and the
  committed example snapshots only. It does not claim a run verdict for
  `21411382144`.

## 2. Canonical Audit Path

### Canonical Source of Truth

1. Workflow contract: `.github/workflows/shadow-soak-evidence.yml`
   - writes `run_summary.json` with `run_id = ${GITHUB_RUN_ID}`
   - uploads the run evidence artifact via
     `shadow-soak-evidence-${{ github.run_id }}`
2. In an unpacked run artifact, start at `package_manifest.json`
   - this is the root-level pointer file
3. Follow `canonical_package_root`
   - canonical run manifest:
     `packages/<package_id>/manifest.json`
4. Audit the copied package files referenced from that canonical manifest

### Derived or Convenience Views

- `package_manifest.json`
  - root-level pointer copy of the canonical manifest
- `run_summary.md`
  - human-readable summary view

### Supporting Raw Sources

- `run_summary.json`
- `shadow_block_probe.json`
- `evidence_index.json`
- `soak_gate_eval.json`
- `endpoints/*`
- `logs_tail.txt`
- `logs_grep.txt`
- `compose_ps.txt`
- `container_inspect.json`

## 3. Committed Repo-Local Snapshot Directories

These directories are real repo artifacts, but they are convenience snapshots,
not canonical packaged evidence roots.

| Path | Run ID | Mode | Soak | What is present | What is missing |
| --- | --- | --- | --- | --- | --- |
| `evidence-run/` | `22836460825` | `lean` | `5m` | `run_summary.*`, logs, `endpoints/*` | `shadow_block_probe.json`, `evidence_index.json`, `soak_gate_eval.json`, `package_manifest.json` |
| `evidence-full-run/` | `22847310859` | `full` | `20m` | `run_summary.*`, logs, `endpoints/*` | `shadow_block_probe.json`, `evidence_index.json`, `soak_gate_eval.json`, `package_manifest.json` |
| `evidence-full-run-30m/` | `22849784682` | `full` | `30m` | `run_summary.*`, logs, `endpoints/*` | `shadow_block_probe.json`, `evidence_index.json`, `soak_gate_eval.json`, `package_manifest.json` |

## 4. Control-Level Context

These documents explain the control semantics and expected evidence chain. They
are not run-specific verdict files.

- `docs/evidence/LR-030.md`
- `docs/evidence/LR-031.md`
- `docs/evidence/LR-040.md`
- `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`
- `docs/operations/72H_SOAK_TEST_RUNBOOK.md`

## 5. Maintainer Rules

- Do not reconstruct missing files for a run that is not committed in the repo.
- If a real run artifact is unpacked into the repo later, keep
  `package_manifest.json` and `packages/<package_id>/manifest.json` intact and
  add only a pointer entry to this index.
- Treat repo-local `evidence-*` directories without `package_manifest.json` as
  convenience snapshots, not canonical evidence packages.
