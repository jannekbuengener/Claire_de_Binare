# integrations/cdb-stack-adapter.ps1
<#
Purpose:
  Legacy bridge for experimental test_pack drills against older CDB stack scripts.

Status:
  - experimental / secondary — NOT a canonical discovery or runtime entrypoint
  - not the canonical repo-wide 431C drill source of truth
  - LEGACY BRIDGE: references `scripts\stack_up.ps1` / `scripts\stack_down.ps1` which no longer exist
  - DO NOT USE for normal stack operations; canonical runtime is BLUE+RED via `tools\cdb.ps1 runtime up`

How:
  - points to the working repo root
  - attempts to call scripts/stack_up.ps1 and scripts/stack_down.ps1 (legacy paths, no longer present)
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
