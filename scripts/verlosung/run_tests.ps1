if ($env:USE_SYSTEM_PYTHON -eq "true" -and (Test-Path "$env:SYSTEM_PYTHON_PATH\python.exe")) {
    Write-Host "Using system Python at $env:SYSTEM_PYTHON_PATH"
    $python = "$env:SYSTEM_PYTHON_PATH\python.exe"
} else {
    Write-Host "System Python not found -> fallback to local installation"
    # <lokale Installation>
$python = $env:SYSTEM_PYTHON
if (-not (Test-Path $python)) {
    Write-Host "System Python nicht gefunden → Abbruch"
    exit 1
}

& $python -m pytest -v
}
