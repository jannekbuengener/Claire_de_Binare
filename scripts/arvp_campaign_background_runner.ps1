#Requires -Version 5.1
<#
.SYNOPSIS
    Start, stop, or check status of an ARVP Campaign Supervisor background process.

.DESCRIPTION
    Wraps tools/arvp_campaign_supervisor.py for unattended 8h paper-window
    campaigns on Windows.  All campaign artifacts are written to
    artifacts/campaigns/<campaign_id>/.

    This script does NOT:
      - Modify Windows power settings (powercfg /change)
      - Create scheduled tasks
      - Run the GitHub reporter automatically
      - Modify supervisor, runtime, Docker, or DB configuration
      - Require admin privileges

.PARAMETER Start
    Start a new campaign supervisor in the background.

.PARAMETER Stop
    Stop a running campaign supervisor by PID file.

.PARAMETER Status
    Show status of a running or completed campaign.

.PARAMETER Manifest
    Path to campaign manifest (YAML or JSON).  Required for -Start.

.PARAMETER CampaignId
    Campaign identifier.  If omitted with -Start, derived from manifest
    campaign_id field.

.PARAMETER PollSeconds
    Polling interval in seconds (default 900 = 15 min).  Passed through
    to the supervisor --poll-seconds argument.

.PARAMETER Python
    Path to Python executable (default: python).

.PARAMETER OutputDir
    Override the default output directory under artifacts/campaigns/.

.EXAMPLE
    .\scripts\arvp_campaign_background_runner.ps1 -Start -Manifest manifests\campaign_3.yaml

.EXAMPLE
    .\scripts\arvp_campaign_background_runner.ps1 -Status

.EXAMPLE
    .\scripts\arvp_campaign_background_runner.ps1 -Status -CampaignId arvp_3095_vol_window_3

.EXAMPLE
    .\scripts\arvp_campaign_background_runner.ps1 -Stop -CampaignId arvp_3095_vol_window_3

.NOTES
    LR remains NO-GO.  No live trading.  No Echtgeld.
#>
param(
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [string]$Manifest = "",
    [string]$CampaignId = "",
    [int]$PollSeconds = 900,
    [string]$Python = "python",
    [string]$OutputDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$SCRIPT_NAME = "arvp_campaign_background_runner.ps1"
$SUPERVISOR_REL = "tools\arvp_campaign_supervisor.py"
$ARTIFACTS_ROOT = "artifacts\campaigns"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Info  ($t) { Write-Host "[INFO]  $t" -ForegroundColor Cyan }
function Write-Ok    ($t) { Write-Host "[OK]    $t" -ForegroundColor Green }
function Write-Warn  ($t) { Write-Host "[WARN]  $t" -ForegroundColor Yellow }
function Write-Err   ($t) { Write-Host "[ERROR] $t" -ForegroundColor Red }

function Show-Help {
    @"

ARVP Campaign Background Runner

USAGE:
  $SCRIPT_NAME -Start   -Manifest <path> [-CampaignId <id>] [-PollSeconds <n>] [-Python <path>]
  $SCRIPT_NAME -Status  [-CampaignId <id>]
  $SCRIPT_NAME -Stop    [-CampaignId <id>]
  $SCRIPT_NAME -Help

OPTIONS:
  -Start              Start a new campaign supervisor in the background.
  -Status             Show campaign status (PID, evidence log, status.md).
  -Stop               Stop a running campaign supervisor.
  -Help               Show this help.

  -Manifest <path>    Campaign manifest YAML or JSON (required for -Start).
  -CampaignId <id>    Campaign identifier (derived from manifest if omitted).
  -PollSeconds <n>    Polling interval (default 900 = 15 min).
  -Python <path>      Python executable (default: python).
  -OutputDir <path>   Override output directory under artifacts/campaigns/.

EXAMPLES:
  # Start campaign
  $SCRIPT_NAME -Start -Manifest manifests\campaign_3.yaml

  # Check status
  $SCRIPT_NAME -Status

  # Stop campaign
  $SCRIPT_NAME -Stop

SAFETY:
  LR remains NO-GO.  No live trading.  No Echtgeld.
  No system policy changes.  No auto-restart after reboot.

"@
}

function Get-CampaignDir {
    param([string]$Id)
    if ($OutputDir) {
        return $OutputDir
    }
    $base = Join-Path -Path $ARTIFACTS_ROOT -ChildPath $Id
    return $base
}

function Resolve-CampaignId {
    param([string]$ManifestPath)
    $ext = [System.IO.Path]::GetExtension($ManifestPath)
    $raw = $null
    if ($ext -in ".yaml", ".yml") {
        $raw = Get-Content -Path $ManifestPath -Raw -Encoding UTF8
        $obj = ConvertFrom-Yaml $raw
        return $obj.campaign_id
    } else {
        $raw = Get-Content -Path $ManifestPath -Raw -Encoding UTF8
        $obj = $raw | ConvertFrom-Json
        return $obj.campaign_id
    }
}

function Get-CampaignIdFromManifest {
    param([string]$ManifestPath)
    if (-not (Test-Path -LiteralPath $ManifestPath)) {
        throw "Manifest not found: $ManifestPath"
    }
    try {
        return Resolve-CampaignId -ManifestPath $ManifestPath
    } catch {
        throw "Cannot parse manifest or extract campaign_id from: $ManifestPath"
    }
}

function Read-PidFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $content = Get-Content -Path $Path -Encoding UTF8 -TotalCount 1
    $content = $content.Trim()
    if ([string]::IsNullOrWhiteSpace($content)) {
        return $null
    }
    try {
        return [int]$content
    } catch {
        return $null
    }
}

function Write-PidFile {
    param([string]$Path, [int]$Pid)
    $parent = Split-Path -Path $Path -Parent
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $Pid | Out-File -FilePath $Path -Encoding UTF8
}

function Assert-ProcessRunning {
    param([int]$Pid)
    try {
        $proc = Get-Process -Id $Pid -ErrorAction Stop
        return $proc.HasExited -eq $false
    } catch {
        return $false
    }
}

function Find-CampaignPidFile {
    $pidCandidates = @()
    if ($CampaignId) {
        $campDir = Get-CampaignDir -Id $CampaignId
        $pidFile = Join-Path -Path $campDir -ChildPath "campaign.pid"
        if (Test-Path -LiteralPath $pidFile) {
            $pidCandidates += $pidFile
        }
    } else {
        $items = Get-ChildItem -Path $ARTIFACTS_ROOT -Directory -ErrorAction SilentlyContinue
        foreach ($item in $items) {
            $pidFile = Join-Path -Path $item.FullName -ChildPath "campaign.pid"
            if (Test-Path -LiteralPath $pidFile) {
                $pidCandidates += $pidFile
            }
        }
    }
    return $pidCandidates
}

# ---------------------------------------------------------------------------
# Action: Start
# ---------------------------------------------------------------------------

function Invoke-StartCampaign {
    if (-not $Manifest) {
        throw "-Manifest is required for -Start"
    }
    if (-not (Test-Path -LiteralPath $Manifest)) {
        throw "Manifest file not found: $Manifest"
    }

    $resolvedId = $CampaignId
    if (-not $resolvedId) {
        Write-Info "Deriving campaign_id from manifest..."
        $resolvedId = Get-CampaignIdFromManifest -ManifestPath $Manifest
    }

    $rep = Get-CampaignDir -Id $resolvedId
    $pidFile = Join-Path -Path $rep -ChildPath "campaign.pid"
    $jsonl   = Join-Path -Path $rep -ChildPath "evidence_log.jsonl"
    $md      = Join-Path -Path $rep -ChildPath "status.md"
    $stdout  = Join-Path -Path $rep -ChildPath "stdout.log"
    $stderr  = Join-Path -Path $rep -ChildPath "stderr.log"

    # Check existing PID
    $existingPid = Read-PidFile -Path $pidFile
    if ($existingPid -and (Assert-ProcessRunning -Pid $existingPid)) {
        throw "Campaign already running (PID $existingPid). Stop it first or use -Stop."
    }

    # Create output directory
    if (-not (Test-Path -LiteralPath $rep)) {
        New-Item -ItemType Directory -Path $rep -Force | Out-Null
        Write-Info "Created output directory: $rep"
    }

    # Verify Python + supervisor script
    $pythonCheck = & $Python -c "import sys; print(sys.executable)" 2>$null
    if (-not $pythonCheck) {
        throw "Python not found at '$Python'. Use -Python to specify path."
    }

    $supervisorPath = Join-Path -Path (Get-Location) -ChildPath $SUPERVISOR_REL
    if (-not (Test-Path -LiteralPath $supervisorPath)) {
        throw "Supervisor script not found: $supervisorPath (run from repo root)"
    }

    # Build argument list
    $argList = @(
        $SUPERVISOR_REL
        "--manifest", $Manifest
        "--poll-seconds", $PollSeconds
        "--output-jsonl", $jsonl
        "--status-md", $md
    )

    Write-Info "Starting campaign: $resolvedId"
    Write-Info "  Python:    $pythonCheck"
    Write-Info "  Manifest:  $Manifest"
    Write-Info "  Poll:      ${PollSeconds}s"
    Write-Info "  JSONL:     $jsonl"
    Write-Info "  Status MD: $md"
    Write-Info "  Stdout:    $stdout"
    Write-Info "  Stderr:    $stderr"

    $process = Start-Process -FilePath $Python -ArgumentList $argList -NoNewWindow -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    Start-Sleep -Milliseconds 500

    if ($process.HasExited) {
        $exitCode = $process.ExitCode
        $errContent = ""
        if (Test-Path -LiteralPath $stderr) {
            $errContent = Get-Content -Path $stderr -Encoding UTF8 -Raw
        }
        throw "Supervisor exited immediately (exit code $exitCode). Stderr: $errContent"
    }

    Write-PidFile -Path $pidFile -Pid $process.Id
    Write-Ok "Campaign started (PID $($process.Id))"
    Write-Info "Output directory: $rep"
}

# ---------------------------------------------------------------------------
# Action: Status
# ---------------------------------------------------------------------------

function Invoke-ShowStatus {
    $pidFiles = Find-CampaignPidFile

    if (-not $pidFiles) {
        if ($CampaignId) {
            $campDir = Get-CampaignDir -Id $CampaignId
            $mdFile = Join-Path -Path $campDir -ChildPath "status.md"
            $jsonlFile = Join-Path -Path $campDir -ChildPath "evidence_log.jsonl"
            if (Test-Path -LiteralPath $mdFile) {
                Write-Info "Campaign directory found (no PID file): $campDir"
                Write-Info "Last status.md:"
                Get-Content -Path $mdFile -Encoding UTF8 | Select-Object -First 20
                return
            }
            if (Test-Path -LiteralPath $jsonlFile) {
                Write-Info "Evidence log found but no status.md (campaign may have been interrupted)."
                Write-Info "Last JSONL entry:"
                Get-Content -Path $jsonlFile -Encoding UTF8 | Select-Object -Last 1 | ForEach-Object { $_ | ConvertFrom-Json | ConvertTo-Json -Depth 5 }
                return
            }
            Write-Warn "No campaign artifacts found for: $CampaignId"
            return
        }

        Write-Warn "No running campaigns found. Use -CampaignId to specify a completed campaign."
        return
    }

    foreach ($pf in $pidFiles) {
        $pid = Read-PidFile -Path $pf
        $campDir = Split-Path -Path $pf -Parent
        $campId = Split-Path -Path $campDir -Leaf
        $mdFile = Join-Path -Path $campDir -ChildPath "status.md"
        $jsonlFile = Join-Path -Path $campDir -ChildPath "evidence_log.jsonl"

        Write-Host ""
        Write-Host "=== Campaign: $campId ===" -ForegroundColor Blue

        if (-not $pid) {
            Write-Warn "PID file is empty or invalid: $pf"
            continue
        }

        $running = Assert-ProcessRunning -Pid $pid
        if ($running) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            $elapsed = ""
            if ($proc) {
                $elapsed = " (running since $($proc.StartTime.ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')) UTC)"
            }
            Write-Ok "Process running (PID $pid)$elapsed"
        } else {
            Write-Warn "Process NOT running (PID $pid). Campaign may have completed or crashed."
        }

        if (Test-Path -LiteralPath $mdFile) {
            Write-Info "Last status.md:"
            Get-Content -Path $mdFile -Encoding UTF8 | Select-Object -First 20
        }

        if (Test-Path -LiteralPath $jsonlFile) {
            $lastLine = Get-Content -Path $jsonlFile -Encoding UTF8 | Select-Object -Last 1
            if ($lastLine) {
                Write-Info "Last evidence log entry:"
                $lastLine | ConvertFrom-Json | ConvertTo-Json -Depth 3
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Action: Stop
# ---------------------------------------------------------------------------

function Invoke-StopCampaign {
    $pidFiles = Find-CampaignPidFile

    if (-not $pidFiles) {
        if ($CampaignId) {
            $campDir = Get-CampaignDir -Id $CampaignId
            $pidFile = Join-Path -Path $campDir -ChildPath "campaign.pid"
            if (Test-Path -LiteralPath $pidFile) {
                $pidFiles += $pidFile
            }
            if (-not $pidFiles) {
                $mdFile = Join-Path -Path $campDir -ChildPath "status.md"
                if (Test-Path -LiteralPath $mdFile) {
                    Write-Warn "Campaign artifacts found but no PID file (already stopped or interrupted)."
                    Write-Info "Evidence log is at: $(Join-Path -Path $campDir -ChildPath 'evidence_log.jsonl')"
                    Write-Info "Status (last known):"
                    Get-Content -Path $mdFile -Encoding UTF8 | Select-Object -First 5
                    return
                }
                throw "No campaign found for: $CampaignId"
            }
        } else {
            throw "No running campaigns found. Specify -CampaignId or check artifacts/campaigns/."
        }
    }

    $stoppedAny = $false
    foreach ($pf in $pidFiles) {
        $pid = Read-PidFile -Path $pf
        $campDir = Split-Path -Path $pf -Parent
        $campId = Split-Path -Path $campDir -Leaf

        if (-not $pid) {
            Write-Warn "Empty or invalid PID file: $pf (removing marker)"
            Remove-Item -Path $pf -Force -ErrorAction SilentlyContinue
            continue
        }

        $running = Assert-ProcessRunning -Pid $pid
        if (-not $running) {
            Write-Warn "Campaign $campId (PID $pid) is not running. Removing PID file."
            Remove-Item -Path $pf -Force -ErrorAction SilentlyContinue
            continue
        }

        Write-Info "Stopping campaign $campId (PID $pid)..."
        try {
            Stop-Process -Id $pid -Force
            Start-Sleep -Seconds 1
            $stillRunning = Assert-ProcessRunning -Pid $pid
            if (-not $stillRunning) {
                Write-Ok "Campaign $campId stopped (PID $pid)."
                $stoppedAny = $true
            } else {
                Write-Warn "Could not stop PID $pid. Try manual kill."
            }
        } catch {
            $errMsg = $_.Exception.Message
            Write-Err "Failed to stop PID ${pid}: $errMsg"
        }
    }

    if (-not $stoppedAny) {
        Write-Warn "No processes were stopped."
    }
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

$actionCount = @($Start, $Stop, $Status).Where({ $_ -eq $true }).Count

if ($actionCount -eq 0) {
    Show-Help
    exit 0
}

if ($actionCount -gt 1) {
    Write-Err "Only one action allowed: -Start, -Stop, or -Status."
    exit 1
}

try {
    if ($Start) {
        Invoke-StartCampaign
    } elseif ($Status) {
        Invoke-ShowStatus
    } elseif ($Stop) {
        Invoke-StopCampaign
    }
} catch {
    Write-Err $_.Exception.Message
    exit 1
}
