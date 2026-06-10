# ARVP Windows Background Runner

**Version:** 1.0
**Issue:** #3114
**Parent:** #3102 (Campaign Supervisor Umbrella)
**Depends on:** #3111 (Supervisor CLI), #3112 (Chain Detector), #3113 (GitHub Reporter)
**Design:** #3094 (Deterministic Window Production)
**Manifest Contract:** docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md

---

## 1. Purpose

Replace manual 8h agent babysitting with an unattended background process.

Each ARVP volatility-window campaign currently requires an agent or human operator
to check correlation_ledger, Docker health, regimes, and candle data every 15-30
minutes for 8 hours.  This runbook documents how to run those campaigns as a
background PowerShell process with persistent evidence logging, so no chat or
agent window needs to stay open.

### 1.1 How It Works

```
┌──────────────────────────────────────────────┐
│         PowerShell Background Process         │
│  Start-Process -WindowStyle Hidden            │
│                                               │
│  python tools/arvp_campaign_supervisor.py     │
│    --manifest manifests/campaign_N.yaml       │
│    --poll-seconds 900                         │
│    --output-jsonl evidence_log.jsonl          │
│    --status-md status.md                      │
├──────────────────────────────────────────────┤
│  Writes:                                      │
│  artifacts/campaigns/<campaign_id>/           │
│    ├── evidence_log.jsonl   (append-only)     │
│    ├── status.md            (overwritten)    │
│    ├── stdout.log          (process stdout)   │
│    ├── stderr.log          (process stderr)   │
│    └── campaign.pid       (PID tracking)     │
└──────────────────────────────────────────────┘
```

The supervisor runs pre-defined cycles (probes → evaluate → write evidence →
sleep 15 min → repeat) until a terminal state is reached.

### 1.2 What This Runbook Does NOT Cover

| Out of Scope | Reason |
|-------------|--------|
| Auto-restart after reboot | T15 requires fresh preflight + explicit Start-Go |
| GitHub Reporter automation | gh auth may not be available in hidden process |
| Windows Scheduled Task setup | Optional manual variant only |
| Docker, runtime, or DB changes | Supervisor is read-only |
| Windows power policy changes | Read-only checks only |
| Ctrl+C handling in supervisor | Would require tools/ code change (#3115 or follow-up) |

---

## 2. Preflight — Host-Availability Read-Only Check

### 2.1 Why This Matters

Campaign #1 and #2 (documented in #3094 evidence) were interrupted by host sleep
or reboot.  Before starting an 8h campaign, verify the host can stay awake.

### 2.2 Checks (Read-Only — No System Changes)

**Uptime and sleep events** — already included in supervisor probe cycle:

```powershell
# Last boot time
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime

# Uptime in seconds
$uptime = [int]((Get-Date).ToUniversalTime() - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()).TotalSeconds
"Uptime: $uptime seconds"

# Sleep/wake events since last boot
powercfg /lastwake
```

**Expected result:** Uptime > 1 hour, no recent wake events.
If uptime < 1 hour: reboot was recent.  Consider waiting or restarting Docker
stack first.  If powercfg /lastwake shows events: investigate sleep settings.

**Power settings informational check** (no change):

```powershell
# Current sleep timeout
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBY

# Lid close action
powercfg /query SCHEME_CURRENT SUB_BUTTONS LIDACTION
```

### 2.3 Operator Recommendations (Manual Steps)

| Setting | Recommended | How to Set (Manual) |
|---------|------------|-------------------|
| Sleep after | Never (AC + DC) | `powercfg /change standby-timeout-ac 0` and `...-dc 0` |
| Lid close | Do nothing | `powercfg /change lid-action-ac 0` |
| Display off | 15 min (AC) | Does not affect campaign operation |
| Hibernate | Off | `powercfg /h off` |

**Hard rule:** The helper script (scripts/arvp_campaign_background_runner.ps1)
NEVER runs `powercfg /change`.  These are documented manual steps for the operator.

---

## 3. Start a Campaign

### 3.1 Prerequisites

- Repo root is current working directory
- Campaign manifest exists (YAML or JSON per #3109 contract)
- Docker BLUE+RED stack is running (`make docker-up`)
- `gh` CLI is authenticated if you plan to use the reporter later
- Python 3.12+ with dependencies (`pip install -r requirements.txt`)

### 3.2 Using the Helper Script (Recommended)

```powershell
# From repo root:
.\scripts\arvp_campaign_background_runner.ps1 -Start -Manifest manifests\campaign_3.yaml
```

Optional parameters:

```powershell
# Custom polling interval
.\scripts\arvp_campaign_background_runner.ps1 -Start -Manifest manifests\campaign_3.yaml -PollSeconds 600

# Custom Python path (e.g. venv)
.\scripts\arvp_campaign_background_runner.ps1 -Start -Manifest manifests\campaign_3.yaml -Python .venv\Scripts\python.exe
```

**What happens:**
1. Manifest is validated and campaign_id extracted
2. Python availability is verified
3. Output directory `artifacts/campaigns/<campaign_id>/` is created
4. Supervisor starts as hidden background process with evidence writing
5. PID file `campaign.pid` is written for later Stop/Status

### 3.3 Manual Equivalent

```powershell
$id = "arvp_3095_vol_window_3"
$dir = "artifacts\campaigns\$id"
New-Item -ItemType Directory -Path $dir -Force | Out-Null

Start-Process -NoNewWindow -WindowStyle Hidden `
  -FilePath "python" `
  -ArgumentList "tools/arvp_campaign_supervisor.py --manifest manifests\campaign_3.yaml --poll-seconds 900 --output-jsonl $dir\evidence_log.jsonl --status-md $dir\status.md" `
  -RedirectStandardOutput "$dir\stdout.log" `
  -RedirectStandardError "$dir\stderr.log"
```

### 3.4 Optional: Windows Scheduled Task (Manual, Admin Required)

For reboot survival without operator intervention, create a scheduled task:

```powershell
schtasks /Create /SC ONCE /ST 08:00 /TN "ARVP_Campaign_3" /TR "powershell -ExecutionPolicy Bypass -File \"D:\Dev\Workspaces\Repos\Claire_de_Binare\scripts\arvp_campaign_background_runner.ps1\" -Start -Manifest manifests\campaign_3.yaml" /RL HIGHEST
```

**Important:** Even with a scheduled task, a fresh campaign after reboot requires
a new manifest with fresh preflight + Start-Go (see Section 6).  The task is
only for the initial launch timing.

---

## 4. Status and Logs

### 4.1 Using the Helper Script

```powershell
# Status of the most recent campaign
.\scripts\arvp_campaign_background_runner.ps1 -Status

# Status of a specific campaign
.\scripts\arvp_campaign_background_runner.ps1 -Status -CampaignId arvp_3095_vol_window_3

# Status of a completed campaign (no PID file)
.\scripts\arvp_campaign_background_runner.ps1 -Status -CampaignId arvp_3095_vol_window_2r
```

**Output:** PID, process running time, last status.md preview, last JSONL entry.

### 4.2 Manual Status

```powershell
# Find supervisor process by command line
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object CommandLine -like "*campaign_supervisor*" |
  Select-Object ProcessId, CommandLine, CreationDate, @{
    Name="ElapsedMinutes"
    Expression={[int]((Get-Date) - $_.CreationDate).TotalMinutes}
  }

# Read latest status overview
Get-Content artifacts\campaigns\<campaign_id>\status.md

# Read last evidence log entry
Get-Content artifacts\campaigns\<campaign_id>\evidence_log.jsonl |
  Select-Object -Last 1 | ConvertFrom-Json | ConvertTo-Json -Depth 3
```

### 4.3 Output Structure

```
artifacts/campaigns/<campaign_id>/
├── evidence_log.jsonl     # Append-only: one JSON line per cycle + terminal state
├── status.md              # Overwritten each cycle with latest snapshot
├── stdout.log             # Raw stdout from supervisor process
├── stderr.log             # Raw stderr from supervisor process
└── campaign.pid           # PID file (stopped campaigns may lack this)
```

**Why two output files?**
- `evidence_log.jsonl`: machine-readable evidence, append-only, survives restart
- `status.md`: human-readable snapshot, always shows latest state

If the campaign is interrupted, `evidence_log.jsonl` contains all prior cycles.
`status.md` contains the last successfully written cycle (may be stale if the
interrupt hit mid-cycle).

---

## 5. Stop a Campaign

### 5.1 Using the Helper Script

```powershell
.\scripts\arvp_campaign_background_runner.ps1 -Stop

# Stop a specific campaign
.\scripts\arvp_campaign_background_runner.ps1 -Stop -CampaignId arvp_3095_vol_window_3
```

**What happens:**
1. PID file is read
2. Process is stopped via Stop-Process -Force
3. PID file is removed
4. Evidence artifacts remain in the output directory

### 5.2 Manual Stop

```powershell
# Find PID
$pid = (Get-Content artifacts\campaigns\<campaign_id>\campaign.pid).Trim()
Stop-Process -Id $pid -Force
```

### 5.3 What Happens to Evidence on Stop

- `evidence_log.jsonl` — preserved (the last cycle was written before stop)
- `status.md` — preserved (last good snapshot)
- `stdout.log` / `stderr.log` — preserved
- No DB writes, no Docker state changes, no runtime mutation

The supervisor is read-only (`no_mutation: True` on all probes).
Forced termination is safe.

---

## 6. Resume After Reboot or Interrupt

### 6.1 State Machine Context (T15)

Per the manifest state machine (§5, transition T15):

> **T15**: interrupted → planned
> Trigger: Host/stack restored + fresh start-go
> Required Evidence: Fresh preflight evidence
> Allowed Action: Re-plan as replacement campaign (N+1R)
> Forbidden Action: Auto-restart without fresh start-go

**No auto-restart.** Every resume requires operator evaluation.

### 6.2 Resume Procedure

**Step 1: Determine last state**

```powershell
# Check if PID file exists and process was running
Get-Content artifacts\campaigns\<campaign_id>\campaign.pid

# Read last evidence log entry
Get-Content artifacts\campaigns\<campaign_id>\evidence_log.jsonl |
  Select-Object -Last 1 | ConvertFrom-Json | Select-Object state, observed_at_utc, cycle

# Read status.md for human-readable summary
Get-Content artifacts\campaigns\<campaign_id>\status.md
```

**Step 2: Classify the interruption**

| Evidence | Classification | Action |
|----------|---------------|--------|
| status.md shows STATE_RUNNING, then host reboot (uptime < 1h) | INTERRUPTED | Does not count as failure. Create replacement campaign. |
| status.md shows TIMEOUT_NO_CHAIN | Full observation, no chain | Counts as failure. Plan next campaign. |
| status.md shows CHAIN_FOUND | Success | Campaign complete. Proceed to evidence extraction. |
| status.md shows BLOCKED_* | Infrastructure issue | Does not count as failure. Fix root cause, re-plan. |

**Step 3: Create replacement manifest**

Create a new manifest with:
- Same campaign base ID + `_r` suffix (e.g., `campaign_3` → `campaign_3_r`)
- Fresh start_utc and timeout_utc (now + 8h)
- Fresh pre-documented start criteria (volatility check)
- Reference to the interrupted campaign in `related_issues`

**Step 4: Verify host and stack**

```powershell
# Host uptime check (WMI)
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime

# Docker health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Health}}"

# Safety flags
docker inspect cdb_execution --format '{{json .Config.Env}}' | ConvertFrom-Json
```

**Step 5: Start replacement campaign**

```powershell
.\scripts\arvp_campaign_background_runner.ps1 -Start -Manifest manifests\campaign_3_r.yaml
```

### 6.3 Evidence Log Survival

The `evidence_log.jsonl` file is **append-only**.  Even after reboot:
- All prior cycle data is intact
- The interrupted campaign's last state is readable
- The replacement campaign appends to its own new log

Example: After Campaign #3 is interrupted at cycle 12, the log contains
12 entries.  Campaign #3R starts fresh with its own log.

---

## 7. GitHub Reporter — Separate Explicit Step

The GitHub Reporter (`tools/arvp_github_reporter.py`) is NOT run in the background.
After a campaign reaches a terminal state:

### 7.1 Determine Terminal State

```powershell
# From the last evidence log entry
Get-Content artifacts\campaigns\<campaign_id>\evidence_log.jsonl |
  Select-Object -Last 1 | ConvertFrom-Json | Select-Object state
```

### 7.2 Run Reporter Manually

```powershell
# Dry run (no GitHub writes)
python tools/arvp_github_reporter.py \
  --manifest manifests\campaign_3.yaml \
  --cycle-entry-file artifacts\campaigns\<campaign_id>\evidence_log.jsonl \
  --state CHAIN_FOUND

# Live run with comment + PR creation
python tools/arvp_github_reporter.py \
  --manifest manifests\campaign_3.yaml \
  --cycle-entry-file artifacts\campaigns\<campaign_id>\evidence_log.jsonl \
  --github-write --create-pr
```

### 7.3 When to Report

| Terminal State | Report to #3095? | Report to #3087? | Create PR? |
|---------------|-----------------|-----------------|------------|
| CHAIN_FOUND | Yes | Yes | Yes |
| TIMEOUT_NO_CHAIN | Yes | Only after ≥3 failures | No |
| INTERRUPTED | Yes (as interruption record) | No | No |
| BLOCKED_* | Yes (as blocker record) | No | No |

---

## 8. Troubleshooting

### 8.1 "Supervisor exited immediately"

**Symptoms:** Background process starts, stdout.log is empty, PID file exists
but process is gone.

**Causes and fixes:**

| Cause | Check | Fix |
|-------|-------|-----|
| Manifest invalid | `stderr.log` contains parsing error | Fix manifest syntax |
| Python not found | `python --version` from repo root fails | Set `-Python` parameter to full path |
| Supervisor import error | `stderr.log` contains ModuleNotFoundError | Run `pip install -r requirements.txt` |
| Working directory wrong | Script was not run from repo root | Always run from the repo root |

### 8.2 "Process not found" on Status

The campaign may have:
- Completed successfully (check `evidence_log.jsonl` for terminal state)
- Crashed without writing final state (check `stderr.log`)
- Been interrupted by reboot (check host uptime)

```powershell
# Read the evidence log to find last state
Get-Content artifacts\campaigns\<campaign_id>\evidence_log.jsonl |
  Select-Object -Last 1 | ConvertFrom-Json
```

### 8.3 "PID file exists but no process"

The campaign process was killed externally (reboot, crash, manual kill without
using -Stop).  The PID file is stale.

**Action:** Remove the stale PID file manually or use -Stop to clean up.
Evidence artifacts are intact.

### 8.4 "Campaign already running" on Start

A PID file exists and the process is still alive.  Stop it first:

```powershell
.\scripts\arvp_campaign_background_runner.ps1 -Stop
.\scripts\arvp_campaign_background_runner.ps1 -Start -Manifest manifests\campaign_N.yaml
```

### 8.5 Evidence Log Has Gaps

If the host went to sleep and woke up, there may be gaps in `evidence_log.jsonl`
timestamps.  This is normal — the `INTERRUPTED` classification handles this.
Check `probe_statuses.host` in the last successfully written cycle for
sleep/wake indicators.

---

## 9. Safety Boundaries

| Boundary | Status | How Enforced |
|----------|--------|-------------|
| LR remains **NO-GO** | Confirmed | Verdict per LR-AUDIT-STATUS-2026-03-05.md; no live trading |
| No Echtgeld-Go | Confirmed | No real capital or exchange orders |
| No strategy parameter changes | Confirmed | `primary_breakout_v1` unchanged |
| No runtime/config mutation | Confirmed | Supervisor is read-only (`no_mutation: True`) |
| No Docker/compose changes | Confirmed | No docker commands beyond inspect |
| No DB migration | Confirmed | SELECT only on correlation_ledger and candles_1m |
| No productive DB writes | Confirmed | Never INSERT/UPDATE/DELETE |
| No Windows system policy changes | Confirmed | Read-only checks; no powercfg /change in script |
| No auto-restart after reboot | Confirmed | T15 requires fresh preflight + Start-Go |
| No auto-GitHub reporting in background | Confirmed | GitHub reporter is explicit separate step |
| No secrets in logs | Confirmed | Supervisor never reads secrets; script never writes secrets |
| Board stage `trade-capable` ≠ Live-Go | Confirmed | Orthogonal to LR system |

---

## 10. References

| Document | Link |
|----------|------|
| Campaign Manifest + State Machine | docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md |
| Probe Layer Spec | docs/runbooks/ARVP_PROBE_LAYER_SPEC.md |
| Operator Runbook | docs/runbooks/ARVP_OPERATOR_RUNBOOK.md |
| Design: Deterministic Window Production | docs/evidence/arvp_deterministic_window_production_3094.md |
| LR Audit (NO-GO) | docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md |
| Control Register | docs/runbooks/CONTROL_REGISTER.md |
| Helper Script | scripts/arvp_campaign_background_runner.ps1 |

| Issue | Title | Status |
|-------|-------|--------|
| #3102 | Campaign Watchdog Umbrella | OPEN |
| #3111 | Supervisor CLI Polling Loop | CLOSED |
| #3112 | Chain Detector + Export Trigger | CLOSED |
| #3113 | GitHub Reporter | CLOSED |
| #3114 | Windows Background Runner (this doc) | OPEN |
| #3115 | Test + Failure Simulation Pack | OPEN |
| #3095 | Campaign Execution | OPEN |
| #3087 | Reference Window Production | OPEN |
