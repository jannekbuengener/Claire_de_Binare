param(
  [Parameter(Mandatory=$true)][string]$Proposal,
  [string]$Preset = "quick",
  [switch]$CreateIssue
)

$ErrorActionPreference = "Stop"

$repo = "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare"
$pipeline = Join-Path $repo "scripts\discussion_pipeline\run_discussion.py"

if (-not $env:DOCS_HUB_PATH) {
  $env:DOCS_HUB_PATH = "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs"
}

$proposalPath = $Proposal
if (-not (Test-Path $proposalPath)) {
  $proposalPath = Join-Path $env:DOCS_HUB_PATH $Proposal
}

$cmd = @("python", $pipeline, $proposalPath, "--preset", $Preset)
if ($CreateIssue) { $cmd += "--create-issue" }

Write-Host ("Running: " + ($cmd -join " "))
& $cmd[0] $cmd[1..($cmd.Length-1)]
