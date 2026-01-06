#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Cleanup Claire de Binare Kubernetes resources
.DESCRIPTION
    Remove all Kubernetes resources for Claire de Binare trading system
.PARAMETER Environment
    Target environment: dev, prod, or all
.PARAMETER Force
    Skip confirmation prompt
.EXAMPLE
    .\cleanup-k8s.ps1 -Environment dev
.EXAMPLE
    .\cleanup-k8s.ps1 -Environment all -Force
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'prod', 'all')]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Red
Write-Host " Claire de Binare K8s Cleanup" -ForegroundColor Red
Write-Host " Environment: $Environment" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

if (-not $Force) {
    Write-Host "WARNING: This will delete all resources in the cdb-trading namespace!" -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure? (yes/NO)"
    if ($confirm -ne 'yes') {
        Write-Host "Cleanup cancelled." -ForegroundColor Green
        exit 0
    }
}

Write-Host "Starting cleanup..." -ForegroundColor Yellow
Write-Host ""

if ($Environment -eq 'all') {
    Write-Host "Deleting entire namespace..." -ForegroundColor Yellow
    kubectl delete namespace cdb-trading --wait=true
    Write-Host "  ✓ Namespace deleted" -ForegroundColor Green
} else {
    $prefix = if ($Environment -eq 'dev') { 'dev-' } else { 'prod-' }
    
    Write-Host "Deleting $Environment deployments..." -ForegroundColor Yellow
    kubectl delete deployment -l environment=$Environment -n cdb-trading --wait=true 2>$null
    Write-Host "  ✓ Deployments deleted" -ForegroundColor Green
    
    Write-Host "Deleting $Environment services..." -ForegroundColor Yellow
    kubectl delete service -l environment=$Environment -n cdb-trading --wait=true 2>$null
    Write-Host "  ✓ Services deleted" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Cleanup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
