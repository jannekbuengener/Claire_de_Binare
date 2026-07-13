# Read-only preflight for D:\Dev\Tools\npm-cache (#4001)
$ErrorActionPreference = 'Continue'
$TargetPath = 'D:\Dev\Tools\npm-cache'
$ScopeIssue = '#4001'
$ScanAsOfUtc = [DateTime]::UtcNow.ToString('o')

function Normalize-FullPath([string]$p) {
    return [IO.Path]::GetFullPath($p.TrimEnd('\', '/'))
}

function Get-NpmCacheConfig {
    $result = [ordered]@{
        npm_version = $null
        cache_config = $null
        cache_config_normalized = $null
        npm_exit_code = $null
        npm_stderr = $null
    }
    try {
        $ver = & npm --version 2>&1
        $result.npm_version = [string]$ver.Trim()
    } catch {
        $result.npm_stderr = $_.Exception.Message
    }
    try {
        $cache = & npm config get cache 2>&1
        $result.npm_exit_code = $LASTEXITCODE
        $cacheStr = [string]$cache.Trim()
        if ($cacheStr -eq 'undefined' -or [string]::IsNullOrWhiteSpace($cacheStr)) {
            $cacheStr = $null
        }
        $result.cache_config = $cacheStr
        if ($null -ne $cacheStr) {
            $result.cache_config_normalized = Normalize-FullPath $cacheStr
        }
    } catch {
        $result.npm_stderr = $_.Exception.Message
    }
    return [pscustomobject]$result
}

function Measure-ScopedPath {
    param(
        [string]$RootPath,
        [int]$MaxAccessErrors = 50
    )
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
        skipped_reparse_points = @($skippedReparse)
        skipped_reparse_points_count = $skippedReparse.Count
    }
}

$normalizedTarget = Normalize-FullPath $TargetPath
$pathExists = Test-Path -LiteralPath $normalizedTarget
$targetAttrs = $null
$isReparse = $false
$reparseTarget = $null
if ($pathExists) {
    try {
        $targetAttrs = [IO.File]::GetAttributes($normalizedTarget)
        $isReparse = [bool]($targetAttrs -band [IO.FileAttributes]::ReparsePoint)
        if ($isReparse) {
            try {
                $item = Get-Item -LiteralPath $normalizedTarget -Force
                $reparseTarget = $item.Target
            } catch { $reparseTarget = 'unresolved' }
        }
    } catch {
        $targetAttrs = 'unreadable'
    }
}

$npmInfo = Get-NpmCacheConfig
$cacheMatch = $false
$cacheMismatchReason = $null
if ($npmInfo.cache_config_normalized) {
    $cacheMatch = ($npmInfo.cache_config_normalized -eq $normalizedTarget)
    if (-not $cacheMatch) {
        $cacheMismatchReason = "npm cache config points to $($npmInfo.cache_config_normalized), not $normalizedTarget"
    }
} else {
    $cacheMismatchReason = 'npm config get cache returned empty or undefined'
}

$measurement = $null
if ($pathExists -and -not $isReparse) {
    $measurement = Measure-ScopedPath -RootPath $normalizedTarget
}

$issue3999EstimateGb = 58.714
$preflightVerdict = 'READY_FOR_HUMAN_APPLY_GO'
$holdReasons = [Collections.Generic.List[string]]::new()

if (-not $pathExists) { $holdReasons.Add('target_path_missing') | Out-Null }
if ($isReparse) { $holdReasons.Add('target_is_reparse_point') | Out-Null }
if (-not $cacheMatch) { $holdReasons.Add('npm_cache_config_mismatch') | Out-Null }
if ($measurement -and $measurement.scan_status -ne 'complete') {
    $holdReasons.Add('partial_scan_access_errors') | Out-Null
}
# Internal npm cache hardlinks (@@@suffix) are expected; not a scope violation.
$internalReparseCount = 0
if ($measurement) { $internalReparseCount = $measurement.skipped_reparse_points_count }

if ($holdReasons.Count -gt 0) { $preflightVerdict = 'HOLD_PREFLIGHT_MISMATCH' }

$recovery = @{
    classification = 'REGENERABLE'
    methods = @(
        'npm cache clean --force'
        'npm install or npm ci repopulates cache on demand'
        'npm cache verify after rebuild'
    )
    risk_if_deleted = 'low'
    no_impact_on = @('git repos', 'node_modules', 'lockfiles', 'source code')
}

$payload = [ordered]@{
    schema_version = 'npm_cache_cleanup_preflight.v1'
    issue = $ScopeIssue
    parent_issue = '#3999'
    scan_as_of_utc = $ScanAsOfUtc
    scope_path = $normalizedTarget
    scope_exclusive = $true
    excluded_paths = @('D:\Dev\Tools\npm', 'D:\Dev\AI', 'D:\Dev\Backups', 'D:\Dev\Workspaces\Repos')
    path_exists = $pathExists
    is_reparse_point = $isReparse
    reparse_target = $reparseTarget
    npm = $npmInfo
    cache_config_matches_scope = $cacheMatch
    cache_mismatch_reason = $cacheMismatchReason
    measurement = $measurement
    issue_3999_estimate_gb = $issue3999EstimateGb
    internal_reparse_points_count = $internalReparseCount
    internal_reparse_note = 'npm cache uses hardlinks/reparse entries (e.g. @@@1); apply via npm cache clean, not manual traversal'
    preflight_verdict = $preflightVerdict
    hold_reasons = @($holdReasons)
    recovery = $recovery
    apply_gate = 'blocked_until_human_go_apply_approved'
}

$outDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'artifacts\local-dev-hygiene\npm-cache-cleanup'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$outFile = Join-Path $outDir 'preflight.json'
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($outFile, ($payload | ConvertTo-Json -Depth 10), $utf8NoBom)

Write-Host "preflight_verdict=$preflightVerdict"
Write-Host "path=$normalizedTarget exists=$pathExists"
Write-Host "cache_match=$cacheMatch"
if ($measurement) {
    Write-Host "size_gb=$($measurement.size_gb) files=$($measurement.file_count) dirs=$($measurement.directory_count) duration_s=$($measurement.scan_duration_seconds)"
}
Write-Host "written=$outFile"
