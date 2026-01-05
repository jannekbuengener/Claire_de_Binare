# Claire de Binare - Set Docker Secrets
# Dieses Script fragt lokal nach Passwörtern und schreibt sie in .secrets/

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Claire de Binare - Docker Secrets Setup" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Gib deine Passwörter ein (werden NICHT angezeigt):" -ForegroundColor Yellow
Write-Host ""

# Redis Password
$redis = Read-Host -AsSecureString "Redis Password"
$redisPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($redis)
)

# Postgres Password
$postgres = Read-Host -AsSecureString "Postgres Password"
$postgresPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($postgres)
)

# Grafana Password
$grafana = Read-Host -AsSecureString "Grafana Password"
$grafanaPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($grafana)
)

Write-Host ""
Write-Host "Schreibe Secrets..." -ForegroundColor Yellow

# Schreibe Secrets (ohne Newline am Ende)
[System.IO.File]::WriteAllText("$PSScriptRoot\.secrets\redis_password", $redisPlain)
[System.IO.File]::WriteAllText("$PSScriptRoot\.secrets\postgres_password", $postgresPlain)
[System.IO.File]::WriteAllText("$PSScriptRoot\.secrets\grafana_password", $grafanaPlain)

# Clear sensitive variables
$redisPlain = $null
$postgresPlain = $null
$grafanaPlain = $null

Write-Host ""
Write-Host "✅ Secrets erfolgreich gesetzt!" -ForegroundColor Green
Write-Host ""
Write-Host "Dateien:" -ForegroundColor Cyan
Write-Host "  - .secrets/redis_password" -ForegroundColor Gray
Write-Host "  - .secrets/postgres_password" -ForegroundColor Gray
Write-Host "  - .secrets/grafana_password" -ForegroundColor Gray
Write-Host ""
Write-Host "Nächster Schritt:" -ForegroundColor Cyan
Write-Host "  docker compose up -d" -ForegroundColor White
Write-Host ""
