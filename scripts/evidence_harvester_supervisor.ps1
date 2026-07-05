param(
    [ValidateSet('plan', 'status', 'supervise', 'record-pid')]
    [string]$Action = 'plan',
    [string]$ArtifactDir,
    [string]$Fixture,
    [int]$Iterations = 0,
    [int]$CadenceSeconds = 900,
    [int]$MaxRestartCount = 3,
    [int]$RestartBackoffSeconds = 30,
    [int]$MaxRelaunchCount = 5,
    [int]$PollSeconds = 60,
    [int]$MaxPolls = 0,
    [int]$Pid = 0,
    [string]$PythonExecutable = 'python',
    [switch]$UsePidProbe,
    [switch]$AssumeProcessAlive,
    [switch]$Explicit,
    [switch]$Pretty
)

$moduleArgs = @('-m', 'tools.evidence_harvester.supervisor')

if ($Pretty) {
    $moduleArgs += '--pretty'
}

switch ($Action) {
    'plan' {
        if (-not $ArtifactDir -or -not $Fixture -or $Iterations -le 0) {
            throw 'plan requires -ArtifactDir, -Fixture, and -Iterations.'
        }
        $moduleArgs += @(
            'plan-external',
            '--artifact-dir', $ArtifactDir,
            '--fixture', $Fixture,
            '--iterations', $Iterations,
            '--cadence-seconds', $CadenceSeconds,
            '--max-restart-count', $MaxRestartCount,
            '--restart-backoff-seconds', $RestartBackoffSeconds,
            '--max-relaunch-count', $MaxRelaunchCount,
            '--poll-seconds', $PollSeconds
        )
        if ($Explicit) {
            $moduleArgs += '--explicit'
        }
    }
    'status' {
        if (-not $ArtifactDir) {
            throw 'status requires -ArtifactDir.'
        }
        $moduleArgs += @('status', '--artifact-dir', $ArtifactDir)
        if ($UsePidProbe) {
            $moduleArgs += '--use-pid-probe'
        }
        if ($AssumeProcessAlive) {
            $moduleArgs += '--assume-process-alive'
        }
        $moduleArgs += @('--max-relaunch-count', $MaxRelaunchCount)
    }
    'supervise' {
        if (-not $ArtifactDir -or -not $Fixture -or $Iterations -le 0) {
            throw 'supervise requires -ArtifactDir, -Fixture, and -Iterations.'
        }
        if (-not $Explicit) {
            throw 'supervise requires -Explicit. Default mode remains plan-only.'
        }
        $moduleArgs += @(
            'supervise-external',
            '--artifact-dir', $ArtifactDir,
            '--fixture', $Fixture,
            '--iterations', $Iterations,
            '--cadence-seconds', $CadenceSeconds,
            '--max-restart-count', $MaxRestartCount,
            '--restart-backoff-seconds', $RestartBackoffSeconds,
            '--max-relaunch-count', $MaxRelaunchCount,
            '--poll-seconds', $PollSeconds,
            '--python-executable', $PythonExecutable,
            '--explicit'
        )
        if ($MaxPolls -gt 0) {
            $moduleArgs += @('--max-polls', $MaxPolls)
        }
    }
    'record-pid' {
        if (-not $ArtifactDir -or $Pid -le 0) {
            throw 'record-pid requires -ArtifactDir and -Pid.'
        }
        $moduleArgs += @(
            'record-coordinator-pid',
            '--artifact-dir', $ArtifactDir,
            '--pid', $Pid
        )
    }
}

& $PythonExecutable @moduleArgs
exit $LASTEXITCODE
