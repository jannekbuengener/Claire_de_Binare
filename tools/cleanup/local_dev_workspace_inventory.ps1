<#
.SYNOPSIS
    Read-only metadata inventory for D:\Dev local development workspace (#3999).

.DESCRIPTION
    Streaming/incremental aggregation only. Does not follow reparse points (junctions/symlinks).
    Does not read file contents. Raw output is local-only (gitignored).
    Discovers all git repositories and worktrees dynamically.

.PARAMETER ConfigPath
    Path to local_dev_hygiene.json SSOT config.

.PARAMETER OutputPath
    Raw JSON output path (default from config raw_output_dir).

.EXAMPLE
    .\tools\cleanup\local_dev_workspace_inventory.ps1
#>

[CmdletBinding()]
param(
    [string]$ConfigPath = "infrastructure\config\ops\local_dev_hygiene.json",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Get-EnumerationOptions {
    $type = [System.Type]::GetType("System.IO.EnumerationOptions")
    if ($null -eq $type) { return $null }
    try {
        $options = [System.Activator]::CreateInstance($type)
        $type.GetProperty("RecurseSubdirectories").SetValue($options, $false)
        $type.GetProperty("IgnoreInaccessible").SetValue($options, $true)
        $type.GetProperty("AttributesToSkip").SetValue(
            $options,
            [System.IO.FileAttributes]::ReparsePoint
        )
        return $options
    } catch {
        return $null
    }
}

function Get-EnumerationEntries {
    param([string]$DirectoryPath)
    $options = Get-EnumerationOptions
    if ($null -ne $options) {
        return [System.IO.Directory]::EnumerateFileSystemEntries(
            $DirectoryPath,
            "*",
            $options
        )
    }
    return [System.IO.Directory]::EnumerateFileSystemEntries($DirectoryPath)
}

function Get-DirectoryEntriesResilient {
    param(
        [string]$DirectoryPath,
        [System.Collections.Generic.List[object]]$AccessErrors,
        [int]$MaxAccessErrors,
        [string]$Phase
    )
    $entries = [System.Collections.Generic.List[string]]::new()
    try {
        foreach ($entry in Get-EnumerationEntries -DirectoryPath $DirectoryPath) {
            $entries.Add([string]$entry) | Out-Null
        }
        return $entries
    } catch {
        if ($AccessErrors.Count -lt $MaxAccessErrors) {
            $AccessErrors.Add([pscustomobject]@{
                path = $DirectoryPath
                error = $_.Exception.GetType().Name
                phase = $Phase
            }) | Out-Null
        }
        try {
            foreach ($item in Get-ChildItem -LiteralPath $DirectoryPath -Force -ErrorAction SilentlyContinue) {
                $entries.Add($item.FullName) | Out-Null
            }
        } catch {
            if ($AccessErrors.Count -lt $MaxAccessErrors) {
                $AccessErrors.Add([pscustomobject]@{
                    path = $DirectoryPath
                    error = "fallback_failed:$($_.Exception.GetType().Name)"
                    phase = $Phase
                }) | Out-Null
            }
        }
        return $entries
    }
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Config not found: $Path"
    }
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Normalize-FullPath {
    param([string]$PathValue)
    return [System.IO.Path]::GetFullPath($PathValue.TrimEnd('\', '/'))
}

function Get-AgeBucket {
    param(
        [datetime]$LastWriteUtc,
        [datetime]$ScanAsOfUtc,
        [hashtable]$BucketDays
    )
    $age = ($ScanAsOfUtc - $LastWriteUtc).TotalDays
    if ($age -lt $BucketDays.lt_30) { return "lt_30d" }
    if ($age -lt $BucketDays.d30_90) { return "d30_90d" }
    if ($age -lt $BucketDays.d90_180) { return "d90_180d" }
    return "gt_180d"
}

function Test-DirectoryGlob {
    param([string]$Name, [string]$Pattern)
    if ($Pattern -like '*`**') {
        $prefix = $Pattern.Substring(0, $Pattern.Length - 1)
        return $Name -like "${prefix}*"
    }
    return $Name -eq $Pattern
}

function Match-PatternCatalog {
    param(
        [string]$FullPath,
        [string]$Name,
        [bool]$IsDirectory,
        $Catalog
    )
    $matches = @()
    foreach ($entry in $Catalog) {
        $matched = $false
        switch ($entry.match_type) {
            "directory_name" {
                $matched = $IsDirectory -and ($Name -eq $entry.pattern)
            }
            "file_extension" {
                $matched = (-not $IsDirectory) -and ($Name.ToLower().EndsWith($entry.pattern.ToLower()))
            }
            "path_suffix" {
                $normalized = $FullPath.Replace('/', '\')
                $matched = $normalized.ToLower().EndsWith($entry.pattern.ToLower())
            }
            "directory_glob" {
                $matched = $IsDirectory -and (Test-DirectoryGlob -Name $Name -Pattern $entry.pattern)
            }
        }
        if ($matched) { $matches += $entry.id }
    }
    return $matches
}

function Add-TopEntry {
    param(
        [System.Collections.Generic.List[object]]$List,
        [string]$Path,
        [long]$SizeBytes,
        [int]$MaxEntries
    )
    $List.Add([pscustomobject]@{ path = $Path; size_bytes = $SizeBytes }) | Out-Null
    if ($List.Count -gt ($MaxEntries * 3)) {
        $sorted = $List | Sort-Object -Property size_bytes -Descending | Select-Object -First $MaxEntries
        $List.Clear()
        foreach ($item in $sorted) { [void]$List.Add($item) }
    }
}

function Finalize-TopEntries {
    param(
        [System.Collections.Generic.List[object]]$List,
        [int]$MaxEntries
    )
    return @(
        $List |
            Sort-Object -Property size_bytes -Descending |
            Select-Object -First $MaxEntries
    )
}

function Measure-DirectorySubtree {
    param(
        [string]$DirectoryPath,
        [datetime]$ScanAsOfUtc,
        [hashtable]$BucketDays,
        [hashtable]$PatternTotals,
        [System.Collections.Generic.List[object]]$AccessErrors,
        [int]$MaxAccessErrors,
        [int]$MaxPathLength
    )
    $fileCount = 0L
    $dirCount = 0L
    $sizeBytes = 0L
    $ageBuckets = @{
        lt_30d = 0L; d30_90d = 0L; d90_180d = 0L; gt_180d = 0L
    }
    $stack = [System.Collections.Stack]::new()
    $stack.Push($DirectoryPath)
    while ($stack.Count -gt 0) {
        $current = [string]$stack.Pop()
        if ($current.Length -gt $MaxPathLength) {
            if ($AccessErrors.Count -lt $MaxAccessErrors) {
                $AccessErrors.Add([pscustomobject]@{
                    path = $current; error = "path_too_long"; phase = "pattern_subtree"
                }) | Out-Null
            }
            continue
        }
        try {
            $childEntries = Get-DirectoryEntriesResilient -DirectoryPath $current `
                -AccessErrors $AccessErrors -MaxAccessErrors $MaxAccessErrors -Phase "pattern_subtree"
            foreach ($entry in $childEntries) {
                if ($entry.Length -gt $MaxPathLength) {
                    if ($AccessErrors.Count -lt $MaxAccessErrors) {
                        $AccessErrors.Add([pscustomobject]@{
                            path = $entry; error = "path_too_long"; phase = "pattern_subtree"
                        }) | Out-Null
                    }
                    continue
                }
                $isDir = $false
                try {
                    $attrs = [System.IO.File]::GetAttributes($entry)
                    if ($attrs -band [System.IO.FileAttributes]::ReparsePoint) { continue }
                    $isDir = $attrs -band [System.IO.FileAttributes]::Directory
                } catch {
                    if ($AccessErrors.Count -lt $MaxAccessErrors) {
                        $AccessErrors.Add([pscustomobject]@{
                            path = $entry; error = $_.Exception.GetType().Name; phase = "pattern_subtree"
                        }) | Out-Null
                    }
                    continue
                }
                if ($isDir) {
                    $dirCount++
                    $stack.Push($entry)
                    continue
                }
                try {
                    $info = [System.IO.FileInfo]::new($entry)
                    $fileCount++
                    $sizeBytes += [long]$info.Length
                    $bucket = Get-AgeBucket -LastWriteUtc $info.LastWriteTimeUtc `
                        -ScanAsOfUtc $ScanAsOfUtc -BucketDays $BucketDays
                    $ageBuckets[$bucket] += [long]$info.Length
                } catch {
                    if ($AccessErrors.Count -lt $MaxAccessErrors) {
                        $AccessErrors.Add([pscustomobject]@{
                            path = $entry; error = $_.Exception.GetType().Name; phase = "pattern_subtree"
                        }) | Out-Null
                    }
                }
            }
        } catch {
            if ($AccessErrors.Count -lt $MaxAccessErrors) {
                $AccessErrors.Add([pscustomobject]@{
                    path = $current; error = $_.Exception.GetType().Name; phase = "pattern_subtree"
                }) | Out-Null
            }
        }
    }
    return [pscustomobject]@{
        file_count = $fileCount
        directory_count = $dirCount
        size_bytes = $sizeBytes
        age_buckets = $ageBuckets
    }
}

function Measure-ConfiguredSuffixPaths {
    param(
        [string]$RootPath,
        [datetime]$ScanAsOfUtc,
        $Config,
        [hashtable]$PatternTotals,
        [hashtable]$AgeBuckets,
        [ref]$FileCount,
        [ref]$DirCount,
        [ref]$SizeBytes,
        [hashtable]$TopChildMap,
        [System.Collections.Generic.List[object]]$AccessErrors,
        [int]$MaxAccessErrors,
        [int]$MaxPathLength
    )
    $bucketDays = @{
        lt_30 = [int]$Config.age_bucket_days.lt_30
        d30_90 = [int]$Config.age_bucket_days.d30_90
        d90_180 = [int]$Config.age_bucket_days.d90_180
    }
    $rootNorm = $RootPath.TrimEnd('\')
    $devRoot = Split-Path $rootNorm -Parent
    foreach ($entry in $Config.pattern_catalog) {
        if ($entry.match_type -ne "path_suffix") { continue }
        $suffix = [string]$entry.pattern
        $candidate = Join-Path $devRoot $suffix
        if (-not $candidate.StartsWith($rootNorm, [StringComparison]::OrdinalIgnoreCase)) {
            continue
        }
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        $existing = $PatternTotals[$entry.id]
        if ($existing.size_bytes -gt 0) { continue }
        try {
            $subtree = Measure-DirectorySubtree -DirectoryPath $candidate `
                -ScanAsOfUtc $ScanAsOfUtc -BucketDays $bucketDays `
                -PatternTotals $PatternTotals -AccessErrors $AccessErrors `
                -MaxAccessErrors $MaxAccessErrors -MaxPathLength $MaxPathLength
            $PatternTotals[$entry.id].count++
            $PatternTotals[$entry.id].directory_count += $subtree.directory_count
            $PatternTotals[$entry.id].file_count += $subtree.file_count
            $PatternTotals[$entry.id].size_bytes += $subtree.size_bytes
            $FileCount.Value += $subtree.file_count
            $DirCount.Value += $subtree.directory_count
            $SizeBytes.Value += $subtree.size_bytes
            foreach ($key in $subtree.age_buckets.Keys) {
                $AgeBuckets[$key] += $subtree.age_buckets[$key]
            }
            if (-not $TopChildMap.ContainsKey($candidate)) {
                $TopChildMap[$candidate] = 0L
            }
            $TopChildMap[$candidate] += $subtree.size_bytes
        } catch {
            if ($AccessErrors.Count -lt $MaxAccessErrors) {
                $AccessErrors.Add([pscustomobject]@{
                    path = $candidate
                    error = $_.Exception.GetType().Name
                    phase = "suffix_measure"
                }) | Out-Null
            }
        }
    }
}

function Scan-Root {
    param(
        [string]$RootPath,
        [datetime]$ScanAsOfUtc,
        $Config
    )
    $limits = $Config.scan_limits
    $bucketDays = @{
        lt_30 = [int]$Config.age_bucket_days.lt_30
        d30_90 = [int]$Config.age_bucket_days.d30_90
        d90_180 = [int]$Config.age_bucket_days.d90_180
    }
    $maxTop = [int]$limits.top_directories_per_root
    $largeThreshold = [long]$limits.large_file_threshold_bytes
    $maxLarge = [int]$limits.large_files_max_entries
    $maxReparseSamples = [int]$limits.skipped_reparse_points_max_samples
    $maxAccessErrors = [int]$limits.access_errors_max_samples
    $maxPathLength = [int]$limits.max_path_length

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $fileCount = 0L
    $dirCount = 0L
    $sizeBytes = 0L
    $ageBuckets = @{
        lt_30d = 0L; d30_90d = 0L; d90_180d = 0L; gt_180d = 0L
    }
    $topDirs = [System.Collections.Generic.List[object]]::new()
    $largeFiles = [System.Collections.Generic.List[object]]::new()
    $accessErrors = [System.Collections.Generic.List[object]]::new()
    $skippedReparse = [System.Collections.Generic.List[object]]::new()
    $patternTotals = @{}
    foreach ($entry in $Config.pattern_catalog) {
        $patternTotals[$entry.id] = @{
            count = 0; size_bytes = 0L; directory_count = 0; file_count = 0
        }
    }
    $topChildMap = @{}
    $scanStatus = "complete"
    $limitations = [System.Collections.Generic.List[string]]::new()

    if (-not (Test-Path -LiteralPath $RootPath)) {
        return [pscustomobject]@{
            path = $RootPath
            scan_status = "failed"
            access_errors = @(@{ path = $RootPath; error = "root_missing" })
            skipped_reparse_points = @()
            skipped_reparse_points_count = 0
            scan_duration_seconds = 0
            baseline_delta = @{}
            completeness = "none"
            limitations = @("Root path does not exist.")
            size_bytes = 0
            file_count = 0
            directory_count = 0
            age_buckets_bytes = $ageBuckets
            top_directories = @()
            large_files = @()
            pattern_groups = @()
        }
    }

    $stack = [System.Collections.Stack]::new()
    $stack.Push([pscustomobject]@{ path = $RootPath; depth = 0; top_child = $null })
    $aggregateSkip = @{}

    while ($stack.Count -gt 0) {
        $frame = $stack.Pop()
        $current = [string]$frame.path
        $depth = [int]$frame.depth
        $topChild = $frame.top_child

        if ($current.Length -gt $maxPathLength) {
            $scanStatus = "partial"
            if ($accessErrors.Count -lt $maxAccessErrors) {
                $accessErrors.Add([pscustomobject]@{
                    path = $current; error = "path_too_long"; phase = "walk"
                }) | Out-Null
            }
            continue
        }
        if ($aggregateSkip.ContainsKey($current.ToLower())) { continue }

        $childEntries = Get-DirectoryEntriesResilient -DirectoryPath $current `
            -AccessErrors $accessErrors -MaxAccessErrors $maxAccessErrors -Phase "walk"
        foreach ($entry in $childEntries) {
            try {
                if ($entry.Length -gt $maxPathLength) {
                    $scanStatus = "partial"
                    if ($accessErrors.Count -lt $maxAccessErrors) {
                        $accessErrors.Add([pscustomobject]@{
                            path = $entry; error = "path_too_long"; phase = "walk"
                        }) | Out-Null
                    }
                    continue
                }
                $name = [System.IO.Path]::GetFileName($entry)
                $isDir = $false
                $isReparse = $false
                try {
                    $attrs = [System.IO.File]::GetAttributes($entry)
                    $isReparse = [bool]($attrs -band [System.IO.FileAttributes]::ReparsePoint)
                    $isDir = [bool]($attrs -band [System.IO.FileAttributes]::Directory)
                } catch {
                    $scanStatus = "partial"
                    if ($accessErrors.Count -lt $maxAccessErrors) {
                        $accessErrors.Add([pscustomobject]@{
                            path = $entry; error = $_.Exception.GetType().Name; phase = "walk"
                        }) | Out-Null
                    }
                    continue
                }

                if ($isReparse) {
                    if ($skippedReparse.Count -lt $maxReparseSamples) {
                        $skippedReparse.Add([pscustomobject]@{
                            path = $entry; kind = $(if ($isDir) { "directory" } else { "file" })
                        }) | Out-Null
                    }
                    continue
                }

                $resolvedTopChild = $topChild
                if ($depth -eq 0) { $resolvedTopChild = $entry }

                if ($isDir) {
                    $dirCount++
                    $patternIds = Match-PatternCatalog -FullPath $entry -Name $name `
                        -IsDirectory $true -Catalog $Config.pattern_catalog
                    if ($patternIds.Count -gt 0) {
                        try {
                            $subtree = Measure-DirectorySubtree -DirectoryPath $entry `
                                -ScanAsOfUtc $ScanAsOfUtc -BucketDays $bucketDays `
                                -PatternTotals $patternTotals -AccessErrors $accessErrors `
                                -MaxAccessErrors $maxAccessErrors -MaxPathLength $maxPathLength
                        } catch {
                            $scanStatus = "partial"
                            if ($accessErrors.Count -lt $maxAccessErrors) {
                                $accessErrors.Add([pscustomobject]@{
                                    path = $entry
                                    error = $_.Exception.GetType().Name
                                    phase = "pattern_subtree_walk"
                                }) | Out-Null
                            }
                            $stack.Push([pscustomobject]@{
                                path = $entry; depth = $depth + 1; top_child = $resolvedTopChild
                            })
                            continue
                        }
                        foreach ($pid in $patternIds) {
                            $patternTotals[$pid].count++
                            $patternTotals[$pid].directory_count += $subtree.directory_count
                            $patternTotals[$pid].file_count += $subtree.file_count
                            $patternTotals[$pid].size_bytes += $subtree.size_bytes
                        }
                        $fileCount += $subtree.file_count
                        $dirCount += $subtree.directory_count
                        $sizeBytes += $subtree.size_bytes
                        foreach ($key in $subtree.age_buckets.Keys) {
                            $ageBuckets[$key] += $subtree.age_buckets[$key]
                        }
                        if ($null -ne $resolvedTopChild) {
                            if (-not $topChildMap.ContainsKey($resolvedTopChild)) {
                                $topChildMap[$resolvedTopChild] = 0L
                            }
                            $topChildMap[$resolvedTopChild] += $subtree.size_bytes
                        }
                        $aggregateSkip[$entry.ToLower()] = $true
                        continue
                    }
                    $stack.Push([pscustomobject]@{
                        path = $entry; depth = $depth + 1; top_child = $resolvedTopChild
                    })
                    continue
                }

                try {
                    $info = [System.IO.FileInfo]::new($entry)
                    $len = [long]$info.Length
                    $fileCount++
                    $sizeBytes += $len
                    $bucket = Get-AgeBucket -LastWriteUtc $info.LastWriteTimeUtc `
                        -ScanAsOfUtc $ScanAsOfUtc -BucketDays $bucketDays
                    $ageBuckets[$bucket] += $len
                    if ($null -ne $resolvedTopChild) {
                        if (-not $topChildMap.ContainsKey($resolvedTopChild)) {
                            $topChildMap[$resolvedTopChild] = 0L
                        }
                        $topChildMap[$resolvedTopChild] += $len
                    }
                    $patternIds = Match-PatternCatalog -FullPath $entry -Name $name `
                        -IsDirectory $false -Catalog $Config.pattern_catalog
                    foreach ($pid in $patternIds) {
                        $patternTotals[$pid].count++
                        $patternTotals[$pid].file_count++
                        $patternTotals[$pid].size_bytes += $len
                    }
                    if ($len -ge $largeThreshold) {
                        Add-TopEntry -List $largeFiles -Path $entry -SizeBytes $len -MaxEntries $maxLarge
                    }
                } catch {
                    $scanStatus = "partial"
                    if ($accessErrors.Count -lt $maxAccessErrors) {
                        $accessErrors.Add([pscustomobject]@{
                            path = $entry; error = $_.Exception.GetType().Name; phase = "walk"
                        }) | Out-Null
                    }
                }
            } catch {
                $scanStatus = "partial"
                if ($accessErrors.Count -lt $maxAccessErrors) {
                    $accessErrors.Add([pscustomobject]@{
                        path = $entry; error = $_.Exception.GetType().Name; phase = "walk_entry"
                    }) | Out-Null
                }
            }
        }
    }

    Measure-ConfiguredSuffixPaths -RootPath $RootPath -ScanAsOfUtc $ScanAsOfUtc -Config $Config `
        -PatternTotals $patternTotals -AgeBuckets $ageBuckets `
        -FileCount ([ref]$fileCount) -DirCount ([ref]$dirCount) -SizeBytes ([ref]$sizeBytes) `
        -TopChildMap $topChildMap -AccessErrors $accessErrors `
        -MaxAccessErrors $maxAccessErrors -MaxPathLength $maxPathLength

    foreach ($key in $topChildMap.Keys) {
        Add-TopEntry -List $topDirs -Path $key -SizeBytes $topChildMap[$key] -MaxEntries $maxTop
    }

    $sw.Stop()
    if ($accessErrors.Count -gt 0) { $limitations.Add("Access or path-length errors encountered.") | Out-Null }
    if ($skippedReparse.Count -gt 0) {
        $limitations.Add("Reparse points recorded but not traversed.") | Out-Null
    }
    $completeness = if ($scanStatus -eq "complete") { "full" } else { "partial" }

    $rootBaselineGb = $null
    $baselineKey = $RootPath
    if ($Config.screenshot_baseline.per_root_gb.PSObject.Properties.Name -contains $baselineKey) {
        $rootBaselineGb = [double]$Config.screenshot_baseline.per_root_gb.$baselineKey
    }
    $sizeGb = [math]::Round($sizeBytes / 1GB, 2)
    $baselineDelta = @{}
    if ($null -ne $rootBaselineGb) {
        $deltaGb = [math]::Round($sizeGb - $rootBaselineGb, 2)
        $pct = if ($rootBaselineGb -gt 0) {
            [math]::Round(($deltaGb / $rootBaselineGb) * 100, 2)
        } else { 0 }
        $within = [math]::Abs($pct) -le [double]$Config.screenshot_baseline.tolerance.size_gb_pct
        $baselineDelta = @{
            screenshot_gb = $rootBaselineGb
            measured_gb = $sizeGb
            delta_gb = $deltaGb
            delta_pct = $pct
            within_tolerance = $within
        }
    }

    $patternGroups = @()
    foreach ($entry in $Config.pattern_catalog) {
        $totals = $patternTotals[$entry.id]
        if ($totals.size_bytes -gt 0 -or $totals.count -gt 0) {
            $patternGroups += [ordered]@{
                pattern_id = $entry.id
                hit_count = $totals.count
                file_count = $totals.file_count
                directory_count = $totals.directory_count
                size_bytes = $totals.size_bytes
                size_gb = [math]::Round($totals.size_bytes / 1GB, 3)
            }
        }
    }

    return [pscustomobject]@{
        path = $RootPath
        scan_status = $scanStatus
        access_errors = @($accessErrors)
        skipped_reparse_points = @($skippedReparse)
        skipped_reparse_points_count = $skippedReparse.Count
        scan_duration_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        baseline_delta = $baselineDelta
        completeness = $completeness
        limitations = @($limitations)
        size_bytes = $sizeBytes
        size_gb = $sizeGb
        file_count = $fileCount
        directory_count = $dirCount
        age_buckets_bytes = $ageBuckets
        top_directories = @(Finalize-TopEntries -List $topDirs -MaxEntries $maxTop)
        large_files = @(Finalize-TopEntries -List $largeFiles -MaxEntries $maxLarge)
        pattern_groups = $patternGroups
    }
}

function Parse-WorktreeList {
    param([string]$RawText, [string]$RepoPath)
    $entries = @()
    $current = [ordered]@{}
    foreach ($line in ($RawText -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            if ($current.Count -gt 0) {
                $entries += [pscustomobject]$current
                $current = [ordered]@{}
            }
            continue
        }
        if ($line.StartsWith("worktree ")) {
            $current["path"] = $line.Substring(9).Trim()
            continue
        }
        if ($line.StartsWith("HEAD ")) {
            $current["head"] = $line.Substring(5).Trim()
            continue
        }
        if ($line.StartsWith("branch ")) {
            $current["branch"] = $line.Substring(7).Trim().Replace("refs/heads/", "")
            continue
        }
        if ($line.StartsWith("bare")) { $current["bare"] = $true }
    }
    if ($current.Count -gt 0) { $entries += [pscustomobject]$current }
    foreach ($entry in $entries) {
        $entry | Add-Member -NotePropertyName repo_path -NotePropertyValue $RepoPath -Force
    }
    return $entries
}

function Get-GitRepoMetadata {
    param([string]$RepoPath)
    $meta = [ordered]@{
        path = $RepoPath
        is_git = $false
        remote_url = $null
        head_commit = $null
        is_clean = $null
        status_error = $null
    }
    $gitMarker = Join-Path $RepoPath ".git"
    if (-not (Test-Path -LiteralPath $gitMarker)) { return [pscustomobject]$meta }
    $meta.is_git = $true
    try {
        $remote = & git -C $RepoPath remote get-url origin 2>&1
        if ($LASTEXITCODE -eq 0) { $meta.remote_url = [string]$remote.Trim() }
    } catch { $meta.status_error = "remote_lookup_failed" }
    try {
        $head = & git -C $RepoPath rev-parse HEAD 2>&1
        if ($LASTEXITCODE -eq 0) { $meta.head_commit = [string]$head.Trim() }
    } catch { $meta.status_error = "head_lookup_failed" }
    try {
        $status = & git -C $RepoPath status --porcelain 2>&1
        if ($LASTEXITCODE -eq 0) {
            $meta.is_clean = [string]::IsNullOrWhiteSpace(($status -join "`n"))
        }
    } catch { $meta.status_error = "status_lookup_failed" }
    return [pscustomobject]$meta
}

function Discover-GitRepositories {
    param([string]$ReposRoot)
    $repos = @()
    if (-not (Test-Path -LiteralPath $ReposRoot)) { return $repos }
    foreach ($child in [System.IO.Directory]::EnumerateDirectories($ReposRoot)) {
        $meta = Get-GitRepoMetadata -RepoPath $child
        if ($meta.is_git) { $repos += $meta }
    }
    return $repos
}

function Discover-Worktrees {
    param([array]$GitRepositories)
    $all = @()
    foreach ($repo in $GitRepositories) {
        try {
            $raw = & git -C $repo.path worktree list --porcelain 2>&1
            if ($LASTEXITCODE -ne 0) { continue }
            $all += Parse-WorktreeList -RawText ([string]$raw) -RepoPath $repo.path
        } catch { continue }
    }
    return $all
}

$repoRoot = Normalize-FullPath -PathValue (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $repoRoot
$config = Read-JsonFile -Path (Join-Path $repoRoot $ConfigPath)
$scanAsOfUtc = [datetime]::UtcNow
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot ($config.raw_output_dir + "\workspace_inventory.json")
}

Write-Host "=== Local Dev Workspace Inventory (#3999) ===" -ForegroundColor Cyan
Write-Host "scan_as_of_utc: $($scanAsOfUtc.ToString('o'))"
Write-Host "boundary: read-only metadata; reparse points not traversed; raw output gitignored."

$ErrorActionPreference = "Continue"
$rootResults = @()
foreach ($root in $config.roots) {
    $normalizedRoot = Normalize-FullPath -PathValue $root
    Write-Host "Scanning $normalizedRoot ..."
    $rootResults += Scan-Root -RootPath $normalizedRoot -ScanAsOfUtc $scanAsOfUtc -Config $config
}

$gitRepos = Discover-GitRepositories -ReposRoot $config.repos_scan_root
$worktrees = Discover-Worktrees -GitRepositories $gitRepos

$totalSize = ($rootResults | Measure-Object -Property size_bytes -Sum).Sum
$totalFiles = ($rootResults | Measure-Object -Property file_count -Sum).Sum
$totalDirs = ($rootResults | Measure-Object -Property directory_count -Sum).Sum
$baseline = $config.screenshot_baseline
$measuredGb = [math]::Round($totalSize / 1GB, 2)
$deltaGb = [math]::Round($measuredGb - [double]$baseline.total_size_gb, 2)
$deltaFilesPct = if ([int]$baseline.total_files -gt 0) {
    [math]::Round((($totalFiles - [int]$baseline.total_files) / [int]$baseline.total_files) * 100, 2)
} else { 0 }
$deltaDirsPct = if ([int]$baseline.total_directories -gt 0) {
    [math]::Round((($totalDirs - [int]$baseline.total_directories) / [int]$baseline.total_directories) * 100, 2)
} else { 0 }

$aggregateBaselineDelta = @{
    screenshot_total_gb = [double]$baseline.total_size_gb
    measured_total_gb = $measuredGb
    delta_gb = $deltaGb
    screenshot_files = [int]$baseline.total_files
    measured_files = [long]$totalFiles
    delta_files_pct = $deltaFilesPct
    screenshot_directories = [int]$baseline.total_directories
    measured_directories = [long]$totalDirs
    delta_directories_pct = $deltaDirsPct
    within_size_tolerance = (
        [math]::Abs($deltaGb) -le ([double]$baseline.total_size_gb * [double]$baseline.tolerance.size_gb_pct / 100)
    )
    within_file_tolerance = (
        [math]::Abs($deltaFilesPct) -le [double]$baseline.tolerance.file_count_pct
    )
    within_directory_tolerance = (
        [math]::Abs($deltaDirsPct) -le [double]$baseline.tolerance.directory_count_pct
    )
    tolerance_notes = [string]$baseline.tolerance.notes
}

$anyPartial = @($rootResults | Where-Object { $_.scan_status -ne "complete" }).Count -gt 0
$inventory = [ordered]@{
    schema_version = "local_dev_workspace_inventory.v1"
    issue = "#3999"
    scan_as_of_utc = $scanAsOfUtc.ToString("o")
    boundary_note = "Read-only metadata scan. Reparse points not traversed. Raw output local-only."
    aggregate = [ordered]@{
        total_size_bytes = [long]$totalSize
        total_size_gb = $measuredGb
        total_files = [long]$totalFiles
        total_directories = [long]$totalDirs
        baseline_delta = $aggregateBaselineDelta
        scan_completeness = if ($anyPartial) { "partial" } else { "full" }
    }
    roots = @($rootResults)
    git_repositories = @($gitRepos)
    worktrees = @($worktrees)
}

$outputDir = Split-Path -Parent $OutputPath
if ($outputDir) { New-Item -ItemType Directory -Path $outputDir -Force | Out-Null }
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($OutputPath, ($inventory | ConvertTo-Json -Depth 12), $utf8NoBom)

Write-Host ""
Write-Host "Aggregate: $measuredGb GB, $totalFiles files, $totalDirs directories" -ForegroundColor Yellow
Write-Host "Git repos: $($gitRepos.Count); worktrees: $($worktrees.Count)"
Write-Host "Report written to: $OutputPath" -ForegroundColor Green
