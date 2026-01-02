
# Requires: GitHub CLI (gh) authenticated
# Lists open issues without milestones and suggests mapping based on "Phase N" in title.
param(
  [string]$Repo = "$(gh repo view --json nameWithOwner -q .nameWithOwner)"
)

Write-Host "Repo: $Repo"

$issues = gh issue list --repo $Repo --state open --limit 200 --json number,title,milestone | ConvertFrom-Json
$noMilestone = $issues | Where-Object { -not $_.milestone }

Write-Host "`nOpen issues without milestone:"
$noMilestone | ForEach-Object { "{0}`t{1}" -f $_.number, $_.title } | Write-Output

Write-Host "`nMapping hint (Phase -> M#): 0->M1, 1->M2, 2->M3, 3->M4, 4->M7, 5->M8, 6->M6, Final->M9"
