Param(
  [string]$MapPath = "docs\MIGRATION_MAP.md",
  [string]$SourceRoot = "..\claire_de_binare",
  [string]$TargetRoot = ".",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $MapPath)) { throw "Map not found: $MapPath" }
if (-not (Test-Path $SourceRoot)) { throw "SourceRoot not found: $SourceRoot" }
if (-not (Test-Path $TargetRoot)) { throw "TargetRoot not found: $TargetRoot" }

$pattern = '^\s*(?!#)(?<src>[^>\n]+?)\s*->\s*(?<dst>[^#\n]+?)\s*$'
$lines = Get-Content -Path $MapPath -Encoding UTF8
$entries = foreach ($ln in $lines) {
  if ($ln -match $pattern) {
    [PSCustomObject]@{
      Src = ($Matches['src'].Trim())
      Dst = ($Matches['dst'].Trim())
    }
  }
}

if (-not $entries) { Write-Warning "No mapping lines found (format: 'source -> target')"; exit 0 }

$report = New-Object System.Collections.Generic.List[string]
foreach ($e in $entries) {
  $src = Join-Path $SourceRoot $e.Src
  $dst = Join-Path $TargetRoot $e.Dst
  if ($DryRun) {
    $state = if (Test-Path $src) { "EXIST" } else { "MISS " }
    $report.Add("{0} {1} -> {2}" -f $state, $e.Src, $e.Dst)
    continue
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
  if (Test-Path $src -PathType Container) {
    Copy-Item $src $dst -Recurse -Force
    $report.Add("DIR  {0} -> {1}" -f $e.Src, $e.Dst)
  } elseif (Test-Path $src -PathType Leaf) {
    Copy-Item $src $dst -Force
    $report.Add("FILE {0} -> {1}" -f $e.Src, $e.Dst)
  } else {
    $report.Add("MISS {0} (not found)" -f $e.Src)
  }
}
$report | Out-Host
