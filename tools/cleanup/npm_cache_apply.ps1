# Apply + post-verify for D:\Dev\Tools\npm-cache (#4001)
$ErrorActionPreference = 'Continue'
$TargetPath = 'D:\Dev\Tools\npm-cache'
$PreflightBaselineBytes = 63043419766
$OutDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'artifacts\local-dev-hygiene\npm-cache-cleanup'
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Normalize-FullPath([string]$p) {
    return [IO.Path]::GetFullPath($p.TrimEnd('\', '/'))
}

function Measure-ScopedPath {
    param([string]$RootPath, [int]$MaxAccessErrors = 50)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $fileCount = 0L
    $dirCount = 0L
    $sizeBytes = 0L
    $accessErrors = [Collections.Generic.List[object]]::new()
    $skippedReparse = [Collections.Generic.List[object]]::new()
    $scanStatus = 'complete'
    $stack = [Collections.Stack]::new()
    $stack.Push($RootPath)
    while ($stack.Count -gt 0) {
        $current = [string]$stack.Pop()
        try {
            foreach ($entry in [IO.Directory]::EnumerateFileSystemEntries($current)) {
                try {
                    $attrs = [IO.File]::GetAttributes($entry)
                    if ($attrs -band [IO.FileAttributes]::ReparsePoint) {
                        if ($skippedReparse.Count -lt 30) {
                            $skippedReparse.Add([pscustomobject]@{
                                path = $entry
                                kind = $(if ($attrs -band [IO.FileAttributes]::Directory) { 'directory' } else { 'file' })
                            }) | Out-Null
                        }
                        continue
                    }
                    if ($attrs -band [IO.FileAttributes]::Directory) {
                        $dirCount++
                        $stack.Push($entry)
                        continue
                    }
                    $info = [IO.FileInfo]::new($entry)
                    $fileCount++
                    $sizeBytes += [long]$info.Length
                } catch {
                    $scanStatus = 'partial'
                    if ($accessErrors.Count -lt $MaxAccessErrors) {
                        $accessErrors.Add([pscustomobject]@{
                            path = $entry
                            error = $_.Exception.GetType().Name
                        }) | Out-Null
                    }
                }
            }
        } catch {
            $scanStatus = 'partial'
            if ($accessErrors.Count -lt $MaxAccessErrors) {
                $accessErrors.Add([pscustomobject]@{
                    path = $current
                    error = $_.Exception.GetType().Name
                }) | Out-Null
            }
        }
    }
    $sw.Stop()
    return [pscustomobject]@{
        scan_status = $scanStatus
        file_count = $fileCount
        directory_count = $dirCount
        size_bytes = $sizeBytes
        size_gb = [math]::Round($sizeBytes / 1GB, 3)
        scan_duration_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        access_errors = @($accessErrors)
        skipped_reparse_points_count = $skippedReparse.Count
    }
}

function Test-ProtectedPaths {
    $checks = [ordered]@{
        'D:\Dev\Tools\npm' = Test-Path -LiteralPath 'D:\Dev\Tools\npm'
        'D:\Dev\AI' = Test-Path -LiteralPath 'D:\Dev\AI'
        'D:\Dev\Backups' = Test-Path -LiteralPath 'D:\Dev\Backups'
        'D:\Dev\Workspaces\Repos' = Test-Path -LiteralPath 'D:\Dev\Workspaces\Repos'
    }
    return $checks
}

$normalizedTarget = Normalize-FullPath $TargetPath
$applyStart = [DateTime]::UtcNow
$swApply = [Diagnostics.Stopwatch]::StartNew()
$applyOut = & npm cache clean --force 2>&1
$applyExit = $LASTEXITCODE
$swApply.Stop()
$applyEnd = [DateTime]::UtcNow

$afterMeasurement = Measure-ScopedPath -RootPath $normalizedTarget
$protected = Test-ProtectedPaths

$verifyStart = [DateTime]::UtcNow
$verifyOut = & npm cache verify 2>&1
$verifyExit = $LASTEXITCODE
$verifyEnd = [DateTime]::UtcNow

$reclaimedVsBaseline = $PreflightBaselineBytes - $afterMeasurement.size_bytes
$reclaimedGb = [math]::Round($reclaimedVsBaseline / 1GB, 3)

$applyResult = [ordered]@{
    schema_version = 'npm_cache_cleanup_apply.v1'
    issue = '#4001'
    parent_issue = '#3999'
    scope_path = $normalizedTarget
    preflight_baseline_bytes = $PreflightBaselineBytes
    apply = @{
        command = 'npm cache clean --force'
        started_utc = $applyStart.ToString('o')
        finished_utc = $applyEnd.ToString('o')
        duration_seconds = [math]::Round($swApply.Elapsed.TotalSeconds, 2)
        exit_code = $applyExit
        output = ($applyOut | Out-String).Trim()
    }
    post_apply_measurement = $afterMeasurement
    reclaim = @{
        bytes_vs_preflight_baseline = $reclaimedVsBaseline
        gb_vs_preflight_baseline = $reclaimedGb
        preflight_baseline_bytes = $PreflightBaselineBytes
        post_apply_bytes = $afterMeasurement.size_bytes
    }
    verify = @{
        command = 'npm cache verify'
        started_utc = $verifyStart.ToString('o')
        finished_utc = $verifyEnd.ToString('o')
        exit_code = $verifyExit
        output = ($verifyOut | Out-String).Trim()
    }
    protected_paths_unchanged = $protected
    apply_verdict = $(if ($applyExit -eq 0) { 'APPLY_OK' } else { 'HOLD_APPLY_FAILED' })
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$applyFile = Join-Path $OutDir 'apply_result.json'
[System.IO.File]::WriteAllText($applyFile, ($applyResult | ConvertTo-Json -Depth 10), $utf8NoBom)

$beforeAfter = @"
# npm-cache cleanup before/after (#4001)

## Apply
- Command: ``npm cache clean --force``
- Started (UTC): $($applyStart.ToString('o'))
- Finished (UTC): $($applyEnd.ToString('o'))
- Duration (s): $([math]::Round($swApply.Elapsed.TotalSeconds, 2))
- Exit code: $applyExit

## Before (preflight baseline)
- Bytes: $PreflightBaselineBytes
- GB: 58.714
- Files: 57,958
- Directories: 17,461

## After (post-apply measurement)
- Bytes: $($afterMeasurement.size_bytes)
- GB: $($afterMeasurement.size_gb)
- Files: $($afterMeasurement.file_count)
- Directories: $($afterMeasurement.directory_count)
- Access errors: $($afterMeasurement.access_errors.Count)
- Scan duration (s): $($afterMeasurement.scan_duration_seconds)

## Reclaim vs preflight baseline
- Bytes freed: $reclaimedVsBaseline
- GB freed: $reclaimedGb

## npm cache verify
- Exit code: $verifyExit

## Protected paths (existence check)
$(($protected.GetEnumerator() | ForEach-Object { "- $($_.Key): $($_.Value)" }) -join "`n")

## Verdict
$($applyResult.apply_verdict)
"@
$baFile = Join-Path $OutDir 'before_after.md'
[System.IO.File]::WriteAllText($baFile, $beforeAfter, $utf8NoBom)

Write-Host "apply_exit=$applyExit verify_exit=$verifyExit"
Write-Host "reclaimed_bytes=$reclaimedVsBaseline reclaimed_gb=$reclaimedGb"
Write-Host "post_size_gb=$($afterMeasurement.size_gb) post_files=$($afterMeasurement.file_count)"
Write-Host "written=$applyFile"
Write-Host "written=$baFile"
