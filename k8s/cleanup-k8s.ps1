# Claire de Binare - Kubernetes Cleanup Script (PowerShell)
# Usage: .\cleanup-k8s.ps1

param(
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Namespace = "cdb-trading"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

Write-Warn "==================================="
Write-Warn "KUBERNETES CLEANUP"
Write-Warn "==================================="
Write-Warn "This will DELETE all resources in namespace: $Namespace"
Write-Warn "This includes:"
Write-Warn "  - All deployments"
Write-Warn "  - All services"
Write-Warn "  - All configmaps"
Write-Warn "  - All secrets"
Write-Warn "  - All PVCs (and data!)"
Write-Host ""

if (-not $Force) {
    $response = Read-Host "Are you sure? Type 'DELETE' to confirm"
    if ($response -ne 'DELETE') {
        Write-Info "Cleanup cancelled"
        exit 0
    }
}

# Check if namespace exists
try {
    kubectl get namespace $Namespace 2>&1 | Out-Null
} catch {
    Write-Info "Namespace $Namespace does not exist. Nothing to clean up."
    exit 0
}

# Delete all resources in namespace
Write-Info "Deleting all resources in namespace $Namespace..."

try {
    kubectl delete all --all -n $Namespace --timeout=60s
    Write-Info "Resources deleted"
} catch {
    Write-Warn "Failed to delete all resources. Continuing..."
}

# Delete PVCs
Write-Info "Deleting PersistentVolumeClaims..."
try {
    kubectl delete pvc --all -n $Namespace --timeout=60s
    Write-Info "PVCs deleted"
} catch {
    Write-Warn "Failed to delete PVCs. Continuing..."
}

# Delete ConfigMaps and Secrets
Write-Info "Deleting ConfigMaps and Secrets..."
try {
    kubectl delete configmap --all -n $Namespace
    kubectl delete secret --all -n $Namespace
    Write-Info "ConfigMaps and Secrets deleted"
} catch {
    Write-Warn "Failed to delete ConfigMaps/Secrets. Continuing..."
}

# Delete namespace
Write-Info "Deleting namespace $Namespace..."
try {
    kubectl delete namespace $Namespace --timeout=60s
    Write-Info "Namespace deleted"
} catch {
    Write-Error "Failed to delete namespace"
    exit 1
}

Write-Info "==================================="
Write-Info "Cleanup completed successfully!"
Write-Info "==================================="
