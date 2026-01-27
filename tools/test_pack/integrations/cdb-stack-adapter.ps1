# integrations/cdb-stack-adapter.ps1
<#
Purpose:
  Run pack drills against the real CDB stack scripts if they exist.

How:
  - points to the working repo root
  - calls scripts/stack_up.ps1 and scripts/stack_down.ps1
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

$up = Join-Path $CdbRepoRoot "scripts\stack_up.ps1"
$down = Join-Path $CdbRepoRoot "scripts\stack_down.ps1"

if (!(Test-Path $up)) { throw "Missing: $up" }
if (!(Test-Path $down)) { throw "Missing: $down" }

& pwsh -NoProfile -File $up 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "stack_up.log") | Out-Null
& pwsh -NoProfile -File $down 2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "stack_down.log") | Out-Null
