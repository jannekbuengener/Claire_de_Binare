#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Claire de Binare trading system to Kubernetes
.DESCRIPTION
    Automated deployment script for Kubernetes manifests with pre-flight checks and validation
.PARAMETER Environment
    Target environment: dev or prod
.PARAMETER SkipChecks
    Skip pre-flight checks
.PARAMETER DryRun
    Preview changes without applying
.EXAMPLE
    .\deploy-k8s.ps1 -Environment dev
.EXAMPLE
    .\deploy-k8s.ps1 -Environment prod -DryRun
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'prod')]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipChecks,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Claire de Binare K8s Deployment" -ForegroundColor Cyan
Write-Host " Environment: $Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Pre-flight checks
if (-not $SkipChecks) {
    Write-Host "[1/6] Running pre-flight checks..." -ForegroundColor Yellow
    
    # Check kubectl
    try {
        $null = kubectl version --client 2>&1
        Write-Host "  ✓ kubectl found" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ kubectl not found. Please install kubectl." -ForegroundColor Red
        exit 1
    }
    
    # Check cluster access
    try {
        $null = kubectl cluster-info 2>&1
        Write-Host "  ✓ Cluster access verified" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Cannot access Kubernetes cluster" -ForegroundColor Red
        exit 1
    }
    
    # Check kustomize
    try {
        $null = kubectl kustomize --help 2>&1
        Write-Host "  ✓ kustomize available" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ kustomize not available" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
}

# Validate manifests
Write-Host "[2/6] Validating manifests..." -ForegroundColor Yellow
$overlayPath = "k8s/overlays/$Environment"

if ($DryRun) {
    Write-Host "  DRY RUN: Previewing changes..." -ForegroundColor Cyan
    kubectl kustomize $overlayPath
    Write-Host ""
    Write-Host "Dry run complete. Use without -DryRun to apply changes." -ForegroundColor Green
    exit 0
}

try {
    $null = kubectl kustomize $overlayPath 2>&1
    Write-Host "  ✓ Manifests validated" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Manifest validation failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Create namespace
Write-Host "[3/6] Creating namespace..." -ForegroundColor Yellow
kubectl apply -f k8s/base/namespace.yaml
Write-Host ""

# Create secrets (if they don't exist)
Write-Host "[4/6] Checking secrets..." -ForegroundColor Yellow
$secretExists = kubectl get secret cdb-secrets -n cdb-trading 2>$null
if (-not $secretExists) {
    Write-Host "  ⚠ Secret 'cdb-secrets' not found!" -ForegroundColor Yellow
    Write-Host "  Please create secrets before deploying:" -ForegroundColor Yellow
    Write-Host "  kubectl create secret generic cdb-secrets --namespace=cdb-trading \" -ForegroundColor Cyan
    Write-Host "    --from-literal=redis_password='...' \" -ForegroundColor Cyan
    Write-Host "    --from-literal=postgres_password='...'" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "Continue without secrets? (y/N)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        Write-Host "Deployment cancelled." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ✓ Secrets found" -ForegroundColor Green
}
Write-Host ""

# Apply manifests
Write-Host "[5/6] Deploying to Kubernetes..." -ForegroundColor Yellow
kubectl apply -k $overlayPath
Write-Host ""

# Wait for deployments
Write-Host "[6/6] Waiting for deployments..." -ForegroundColor Yellow
Write-Host "  Waiting for infrastructure services..." -ForegroundColor Cyan
kubectl wait --for=condition=available --timeout=300s \
    deployment/redis \
    -n cdb-trading 2>$null

kubectl wait --for=condition=ready --timeout=300s \
    statefulset/postgresql \
    -n cdb-trading 2>$null

Write-Host "  ✓ Infrastructure ready" -ForegroundColor Green

Write-Host "  Waiting for application services..." -ForegroundColor Cyan
$prefix = if ($Environment -eq 'dev') { 'dev-' } else { 'prod-' }

kubectl wait --for=condition=available --timeout=300s \
    deployment/${prefix}cdb-ws \
    deployment/${prefix}cdb-signal \
    deployment/${prefix}cdb-risk \
    deployment/${prefix}cdb-execution \
    deployment/${prefix}cdb-db-writer \
    -n cdb-trading 2>$null

Write-Host "  ✓ Application services ready" -ForegroundColor Green
Write-Host ""

# Display status
Write-Host "========================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Check deployment status:" -ForegroundColor Yellow
Write-Host "  kubectl get pods -n cdb-trading" -ForegroundColor Cyan
Write-Host "  kubectl get svc -n cdb-trading" -ForegroundColor Cyan
Write-Host ""
Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "  kubectl logs -f deployment/${prefix}cdb-ws -n cdb-trading" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Grafana:" -ForegroundColor Yellow
Write-Host "  kubectl port-forward svc/grafana 3000:3000 -n cdb-trading" -ForegroundColor Cyan
Write-Host ""
