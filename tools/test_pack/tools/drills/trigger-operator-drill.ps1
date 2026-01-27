\
    # tools/drills/trigger-operator-drill.ps1
    <#
    Skeleton operator drill trigger:
      - writes a timeline.json with stamps
      - TODO: triggers a real alert (email/alertmanager/webhook)
      - TODO: verifies kill-switch state and "order flow stopped"
      - captures docker compose logs (if applicable)
    #>

    [CmdletBinding()]
    param(
      [Parameter(Mandatory=$true)][string]$EvidenceDir,
      [string]$ComposeFile = "docker-compose.yml"
    )

    $ErrorActionPreference = "Stop"

    function Stamp([System.Collections.ArrayList]$Timeline, [string]$Event) {
      $null = $Timeline.Add([pscustomobject]@{
        ts = (Get-Date).ToString("o")
        event = $Event
      })
    }

    New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceDir "screenshots") | Out-Null

    $timeline = New-Object System.Collections.ArrayList
    Stamp $timeline "DRILL_START"

    Stamp $timeline "ALERT_TRIGGERED_TODO"
    @"
    TODO: Implement a real trigger.

    Pick ONE:
      A) Alertmanager webhook (recommended)
      B) Email notifier from a local script
      C) Synthetic 'DRILL ALERT' to your paging channel

    Output requirement:
      - record the alert payload or message in evidence pack
    "@ | Out-File -FilePath (Join-Path $EvidenceDir "trigger.todo.txt") -Encoding utf8

    Stamp $timeline "VERIFY_KILL_SWITCH_TODO"
    @"
    TODO: Implement verification that:
      - kill switch is active
      - order flow is stopped (no new orders, cancels/freeze per design)

    Verification options:
      - query an admin endpoint
      - query DB state
      - grep logs for a canonical marker
      - query Prometheus metric (e.g., orders_sent_total not increasing)
    "@ | Out-File -FilePath (Join-Path $EvidenceDir "verify.todo.txt") -Encoding utf8

    try {
      Stamp $timeline "CAPTURE_STACK_LOGS"
      docker compose -f $ComposeFile logs --no-color > (Join-Path $EvidenceDir "stack.log")
    } catch {
      Stamp $timeline "CAPTURE_STACK_LOGS_FAILED"
      $_.Exception.Message | Out-File -FilePath (Join-Path $EvidenceDir "stack_logs_error.txt") -Encoding utf8
    }

    Stamp $timeline "DRILL_END"
    $timeline | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "timeline.json") -Encoding utf8
