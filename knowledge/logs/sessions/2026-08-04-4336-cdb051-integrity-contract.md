# Session: CDB-051 integrity contract forward-fix (#4336)

Date: 2026-08-04  
Branch: `batch/validation-research-issue-4336-cdb051`  
Base: `origin/main` @ `9468e4c1` (CDB-050 merged)

## Delivered
- `IntegrityError` + `DatasetLoadError.code` / runner / adapter `.code` propagation
- Deterministic `ROOT_CAUSE_PRIORITY` + `primary_reason_code`
- Spec-window bind after CDB-049 exact-window (order preserves CDB-049 edge messages)
- Executable Replay-vs-Runtime asymmetry test (no runtime mutation)
- Parameter-control CDB-051 → `CORRECTNESS_FIX_ONLY`, `blocked_by_issues: [4336]`

## Readiness Preflight Grenze
`run_repo_preflight` → `READY_FOR_REPLAY_SENSITIVITY` trotz CDB-051=`CORRECTNESS_FIX_ONLY`.
Preflight modelliert kein CDB-051-Gate (kein Match in `tools/arvp_vacation`).
Dokumentiert; kein Preflight-Umbau; keine Kampagne.

## Non-goals held
No merge, no `cdb-local-ci`, no campaign, no CDB-052, LR NO-GO.
