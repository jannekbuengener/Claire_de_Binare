# integrations/cdb-stack-adapter.ps1
<#
Purpose:
  Bridge for experimental test_pack drills against the CDB BLUE+RED stack.

Status:
  - experimental / secondary
  - not the canonical repo-wide 431C drill source of truth

How:
  - points to the working repo root
  - up:   calls tools\cdb.ps1 runtime up (canonical dispatcher)
  - down: calls docker compose down for RED then BLUE (matches make docker-down)
  - returns the compose invocation output into the evidence pack

This keeps the Test Pack generic while still "clicking" into CDB with minimal friction.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$CdbRepoRoot,
  [Parameter(Mandatory=$true)][string]$EvidenceDir
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

# --- Up: canonical dispatcher ---
$dispatcher = Join-Path $CdbRepoRoot "tools\cdb.ps1"
if (!(Test-Path $dispatcher)) { throw "Missing dispatcher: $dispatcher" }

& pwsh -NoProfile -File $dispatcher runtime up 2>&1 |
  Tee-Object -FilePath (Join-Path $EvidenceDir "stack_up.log") | Out-Null

# --- Down: docker compose RED then BLUE (no runtime down in dispatcher yet) ---
$composeDir = Join-Path $CdbRepoRoot "infrastructure\compose"
$redCompose  = Join-Path $composeDir "compose.red.yml"
$blueCompose = Join-Path $composeDir "compose.blue.yml"

if (!(Test-Path $redCompose))  { throw "Missing: $redCompose" }
if (!(Test-Path $blueCompose)) { throw "Missing: $blueCompose" }

& docker compose -f $redCompose down 2>&1 |
  Tee-Object -FilePath (Join-Path $EvidenceDir "stack_down.log") | Out-Null
& docker compose -f $blueCompose down 2>&1 |
  Tee-Object -FilePath (Join-Path $EvidenceDir "stack_down.log") -Append | Out-Null
