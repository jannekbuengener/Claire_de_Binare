# ARVP Vacation Autopilot MVP — Windows Background Runner

Version: 1.0
Issue: #3986
Parent: #1900

## Purpose

Run the offline ARVP vacation job queue without keeping a chat/agent session open.
No paper runtime, no Docker start, no live-go.

## Preflight

```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
git rev-parse HEAD
python -m tools.arvp_vacation.coordinator --manifest config/arvp/vacation/vacation_autopilot_mvp.yaml --preflight-only
```

Resolve `source_sha` in the manifest before departure (replace `RUNTIME_RESOLVE` with current `main` SHA).

## Foreground (debug)

```powershell
python -m tools.arvp_vacation.coordinator `
  --manifest config/arvp/vacation/vacation_autopilot_mvp.yaml `
  --run-until-complete
```

## Background start

```powershell
.\scripts\arvp_vacation_background_runner.ps1 -Start `
  -ManifestPath config/arvp/vacation/vacation_autopilot_mvp.yaml
```

## Status / stop

```powershell
.\scripts\arvp_vacation_background_runner.ps1 -Status -CampaignId arvp_vacation_mvp_20260713
.\scripts\arvp_vacation_background_runner.ps1 -Stop -CampaignId arvp_vacation_mvp_20260713
```

## Resume after coordinator crash

```powershell
python -m tools.arvp_vacation.coordinator `
  --manifest config/arvp/vacation/vacation_autopilot_mvp.yaml `
  --run-until-complete `
  --resume
```

Or restart background runner (same command as start; resume is automatic when state exists).

## Artifacts

```text
artifacts/arvp_vacation/<campaign_id>/
  queue_state.json
  queue_events.jsonl
  heartbeat.json
  vacation_summary.json
  vacation_summary.md
  jobs/<job_id>/
```

## Boundaries

- LR **NO-GO** — no live/echtgeld
- `controlled_lab_evidence` only
- `allow_paper_jobs=false` — manifest with paper jobs fails closed
- Host reboot: manual resume required (no autostart)
- Explicit **OPERATIONS-GO** phrase required before first production run:

```text
OPERATIONS-GO #3986 vacation MVP offline queue start
```

Do not start automatically from this runbook alone.
