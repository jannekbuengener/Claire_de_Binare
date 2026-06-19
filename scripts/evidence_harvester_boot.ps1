param(
    [ValidateSet('status', 'preflight', 'install-plan', 'render-operator-handoff')]
    [string]$Action = 'status',
    [string]$JsonOutput,
    [string]$MarkdownOutput,
    [string]$EvaluatedAtUtc,
    [switch]$Pretty
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$moduleArgs = @('-m', 'tools.evidence_harvester.boot', $Action)

if ($JsonOutput) {
    $moduleArgs += @('--json-output', $JsonOutput)
}
if ($MarkdownOutput) {
    $moduleArgs += @('--markdown-output', $MarkdownOutput)
}
if ($EvaluatedAtUtc) {
    $moduleArgs += @('--evaluated-at-utc', $EvaluatedAtUtc)
}
if ($Pretty) {
    $moduleArgs += '--pretty'
}

python @moduleArgs
exit $LASTEXITCODE
