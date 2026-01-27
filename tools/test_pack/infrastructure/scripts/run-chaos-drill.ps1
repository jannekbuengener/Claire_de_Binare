# infrastructure/scripts/run-chaos-drill.ps1
<#!
Chaos Drill Harness (upgradeable)

What it does:
  - prepares an evidence pack folder
  - (optional) brings up a stack (generic docker-compose.yml OR via integrations/cdb-stack-adapter.ps1)
  - records the scenario used
  - ingests the scenario into CDB (Redis market_data)
  - captures a metrics snapshot + evaluates assertions
  - collects logs
  - (optional) brings the stack down

Rule:
  Evidence pack is a first-class artifact. If it doesn't exist, the drill didn't happen.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ScenarioFile,
  [Parameter(Mandatory=$true)][string]$EvidenceDir,

  # Generic mode (fallback):
  [string]$ComposeFile = "docker-compose.yml",

  # CDB mode (preferred when you have the repo locally):
  [string]$CdbRepoRoot = "",

  # Ingestion config
  [string]$RedisHost = "localhost",
  [int]$RedisPort = 6379,
  [int]$RedisDb = 0,
  [string]$RedisPassword = "",
  [string]$Symbol = "BTCUSDT",
  [string]$TradeQty = "1",
  [int]$TickDelayMs = 0,
  [switch]$DryRunIngestion,

  # Metrics
  [string]$PromUrl = "http://127.0.0.1:19090",
  [switch]$RunMetricsSmoke
)

$ErrorActionPreference = "Stop"

function New-EvidenceDir([string]$Path) {
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $Path "service_logs") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $Path "reports") | Out-Null
}

function Write-Stamp([string]$Dir, [string]$Message) {
  $line = "{0} {1}" -f (Get-Date).ToString("o"), $Message
  Add-Content -Path (Join-Path $Dir "timeline.log") -Value $line
}

function Stack-Up([string]$Dir) {
  if ($CdbRepoRoot -and (Test-Path (Join-Path $PSScriptRoot "..\..\integrations\cdb-stack-adapter.ps1"))) {
    Write-Stamp $Dir "STACK_UP_CDB"
    & pwsh -NoProfile -File (Join-Path $PSScriptRoot "..\..\integrations\cdb-stack-adapter.ps1") `
      -CdbRepoRoot $CdbRepoRoot -EvidenceDir (Join-Path $Dir "stack") 2>&1 | Out-Null
    return
  }

  Write-Stamp $Dir "STACK_UP_COMPOSE"
  docker compose -f $ComposeFile up -d --build 2>&1 | Tee-Object -FilePath (Join-Path $Dir "compose_up.log") | Out-Null
}

function Stack-Down([string]$Dir) {
  if ($CdbRepoRoot -and (Test-Path (Join-Path $PSScriptRoot "..\..\integrations\cdb-stack-adapter.ps1"))) {
    Write-Stamp $Dir "STACK_DOWN_CDB"
    # adapter does up+down together today; keep placeholder for future split
    return
  }

  Write-Stamp $Dir "STACK_DOWN_COMPOSE"
  docker compose -f $ComposeFile down 2>&1 | Tee-Object -FilePath (Join-Path $Dir "compose_down.log") | Out-Null
}

$PackRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$IngestScript = Join-Path $PackRoot "tools\ingestion\ingest_scenario.py"
$SnapshotScript = Join-Path $PackRoot "tools\metrics\metrics_snapshot.py"
$AssertionsScript = Join-Path $PackRoot "tools\assertions\evaluate_assertions.py"
$MetricsSmokeScript = Join-Path $PackRoot "tools\metrics\metrics-smoke.ps1"
$ReadmeTemplate = Join-Path $PackRoot "templates\evidence_pack_README.md"

New-EvidenceDir -Path $EvidenceDir
Copy-Item -Force $ScenarioFile (Join-Path $EvidenceDir "scenario.jsonl")

if (Test-Path $ReadmeTemplate) {
  Copy-Item -Force $ReadmeTemplate (Join-Path $EvidenceDir "README.md")
}

$runConfig = [ordered]@{
  ts_utc = (Get-Date).ToString("o")
  scenario_file = $ScenarioFile
  evidence_dir = $EvidenceDir
  redis = @{
    host = $RedisHost
    port = $RedisPort
    db = $RedisDb
    symbol = $Symbol
    trade_qty = $TradeQty
    tick_delay_ms = $TickDelayMs
    dry_run = [bool]$DryRunIngestion
  }
  prometheus = @{ url = $PromUrl }
}
$runConfig | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "run_config.json") -Encoding utf8

$sources = @()
if (Test-Path $ScenarioFile) { $sources += @{ path = $ScenarioFile; sha256 = (Get-FileHash $ScenarioFile).Hash } }
if (Test-Path $IngestScript) { $sources += @{ path = $IngestScript; sha256 = (Get-FileHash $IngestScript).Hash } }
if (Test-Path $SnapshotScript) { $sources += @{ path = $SnapshotScript; sha256 = (Get-FileHash $SnapshotScript).Hash } }
if (Test-Path $AssertionsScript) { $sources += @{ path = $AssertionsScript; sha256 = (Get-FileHash $AssertionsScript).Hash } }
$sources | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "sources_manifest.txt") -Encoding utf8

Write-Stamp $EvidenceDir "CHAOS_DRILL_START"

Stack-Up -Dir $EvidenceDir

$failed = $false

# Ingestion
Write-Stamp $EvidenceDir "INGEST_SCENARIO"
$ingestReport = Join-Path $EvidenceDir "reports\ingestion_report.json"
$ingestArgs = @(
  $IngestScript,
  "--scenario", $ScenarioFile,
  "--out", $ingestReport,
  "--redis-host", $RedisHost,
  "--redis-port", $RedisPort,
  "--redis-db", $RedisDb,
  "--symbol", $Symbol,
  "--trade-qty", $TradeQty
)
if ($RedisPassword) { $ingestArgs += @("--redis-password", $RedisPassword) }
if ($TickDelayMs -gt 0) { $ingestArgs += @("--tick-delay-ms", $TickDelayMs) }
if ($DryRunIngestion) { $ingestArgs += "--dry-run" }

& python @ingestArgs
if ($LASTEXITCODE -ne 0) {
  Write-Stamp $EvidenceDir "INGESTION_FAIL"
  $failed = $true
}

# Optional quick smoke
if ($RunMetricsSmoke) {
  Write-Stamp $EvidenceDir "METRICS_SMOKE"
  try {
    & pwsh -NoProfile -File $MetricsSmokeScript -PromUrl $PromUrl -OutDir (Join-Path $EvidenceDir "reports\metrics_smoke") | Out-Null
  } catch {
    $_.Exception.Message | Out-File -FilePath (Join-Path $EvidenceDir "reports\metrics_smoke_error.txt") -Encoding utf8
  }
}

# Metrics snapshot
Write-Stamp $EvidenceDir "METRICS_SNAPSHOT"
$metricsSnapshot = Join-Path $EvidenceDir "reports\metrics_snapshot.json"
& python $SnapshotScript --prom-url $PromUrl --out $metricsSnapshot

# Assertions
Write-Stamp $EvidenceDir "ASSERTIONS_EVAL"
$assertionsResult = Join-Path $EvidenceDir "reports\assertions_result.json"
& python $AssertionsScript --snapshot $metricsSnapshot --out $assertionsResult
if ($LASTEXITCODE -ne 0) {
  $failed = $true
}

Write-Stamp $EvidenceDir "COLLECT_LOGS"
try {
  docker compose -f $ComposeFile logs --no-color > (Join-Path $EvidenceDir "service_logs\stack.log")
} catch {
  $_.Exception.Message | Out-File -FilePath (Join-Path $EvidenceDir "service_logs\stack_logs_error.txt") -Encoding utf8
}

Stack-Down -Dir $EvidenceDir
Write-Stamp $EvidenceDir "CHAOS_DRILL_END"

if ($failed) { exit 1 }