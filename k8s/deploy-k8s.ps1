# Claire de Binare - Kubernetes Deployment Helper (PowerShell)
# Usage: .\deploy-k8s.ps1 -Environment dev|prod

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('dev','prod')]
    [string]$Environment = 'dev',
    
    [Parameter(Mandatory=$false)]
    [string]$Registry = $env:DOCKER_REGISTRY ?? 'your-registry',
    
    [Parameter(Mandatory=$false)]
    [string]$Version = $env:VERSION ?? 'latest'
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

Write-Info "Deploying to $Environment environment..."

# Check prerequisites
Write-Info "Checking prerequisites..."

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Error "kubectl not found. Please install kubectl."
    exit 1
}

if (-not (Get-Command kustomize -ErrorAction SilentlyContinue)) {
    Write-Warn "kustomize not found. Will use 'kubectl apply -k' instead."
}

# Check cluster connectivity
try {
    kubectl cluster-info | Out-Null
    $context = kubectl config current-context
    Write-Info "Connected to cluster: $context"
} catch {
    Write-Error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    exit 1
}

# Create namespace if it doesn't exist
try {
    kubectl get namespace $Namespace 2>&1 | Out-Null
    Write-Info "Namespace $Namespace already exists"
} catch {
    Write-Info "Creating namespace: $Namespace"
    kubectl create namespace $Namespace
}

# Check if secrets exist
try {
    kubectl get secret -n $Namespace cdb-secrets 2>&1 | Out-Null
    Write-Info "Secrets found"
} catch {
    Write-Error "Secret 'cdb-secrets' not found in namespace $Namespace"
    Write-Error "Please create secrets first:"
    Write-Error "  kubectl create secret generic cdb-secrets ``"
    Write-Error "    --namespace=$Namespace ``"
    Write-Error "    --from-literal=redis_password='...' ``"
    Write-Error "    --from-literal=postgres_password='...' ``"
    Write-Error "    --from-literal=grafana_password='...' ``"
    Write-Error "    --from-literal=mexc_api_key='...' ``"
    Write-Error "    --from-literal=mexc_api_secret='...'"
    exit 1
}

# Production safety check
if ($Environment -eq 'prod') {
    Write-Warn "==================================="
    Write-Warn "PRODUCTION DEPLOYMENT"
    Write-Warn "==================================="
    Write-Warn "This will deploy to PRODUCTION!"
    Write-Warn "Have you:"
    Write-Warn "  - Reviewed all changes?"
    Write-Warn "  - Run E2E tests (>=95% pass)?"
    Write-Warn "  - Scanned for CVEs (0 critical)?"
    Write-Warn "  - Verified secrets are correct?"
    Write-Warn "  - Prepared rollback plan?"
    Write-Host ""
    $response = Read-Host "Continue? (yes/no)"
    if ($response -ne 'yes') {
        Write-Info "Deployment cancelled"
        exit 0
    }
}

# Apply manifests
Write-Info "Applying manifests for $Environment..."

if (Get-Command kustomize -ErrorAction SilentlyContinue) {
    kustomize build "k8s/overlays/$Environment" | kubectl apply -f -
} else {
    kubectl apply -k "k8s/overlays/$Environment"
}

# Wait for infrastructure to be ready
Write-Info "Waiting for infrastructure services..."

kubectl wait --for=condition=ready `
    --timeout=300s `
    -n $Namespace `
    pod -l app=cdb-redis

kubectl wait --for=condition=ready `
    --timeout=300s `
    -n $Namespace `
    pod -l app=cdb-postgres

Write-Info "Infrastructure services ready"

# Wait for application services
Write-Info "Waiting for application services..."

$services = @('cdb-ws', 'cdb-signal', 'cdb-risk', 'cdb-execution', 'cdb-db-writer')

foreach ($service in $services) {
    Write-Info "Checking rollout status: $service"
    try {
        kubectl rollout status -n $Namespace "deployment/$service" --timeout=5m
    } catch {
        Write-Warn "Rollout status check failed for $service"
    }
}

# Check pod status
Write-Info "Pod status:"
kubectl get pods -n $Namespace

# Check service status
Write-Info "Service status:"
kubectl get svc -n $Namespace

# Final health check
Write-Info "Running health checks..."

$failed = $false

foreach ($service in @('cdb-ws', 'cdb-signal', 'cdb-risk', 'cdb-execution')) {
    try {
        $pod = kubectl get pod -n $Namespace -l "app=$service" -o jsonpath='{.items[0].metadata.name}' 2>$null
        
        if ([string]::IsNullOrEmpty($pod)) {
            Write-Error "No pod found for $service"
            $failed = $true
            continue
        }
        
        $status = kubectl get pod -n $Namespace $pod -o jsonpath='{.status.phase}'
        if ($status -ne 'Running') {
            Write-Error "$service pod is not running (status: $status)"
            $failed = $true
        } else {
            Write-Info "$service is running"
        }
    } catch {
        Write-Error "Failed to check $service status"
        $failed = $true
    }
}

if ($failed) {
    Write-Error "Some services failed to deploy properly"
    Write-Info "Check logs with: kubectl logs -n $Namespace <pod-name>"
    exit 1
}

Write-Info "==================================="
Write-Info "Deployment completed successfully!"
Write-Info "==================================="

if ($Environment -eq 'dev') {
    Write-Info "Access services via port-forward:"
    Write-Info "  Grafana:    kubectl port-forward -n $Namespace svc/cdb-grafana 3000:3000"
    Write-Info "  Prometheus: kubectl port-forward -n $Namespace svc/cdb-prometheus 9090:9090"
    Write-Info "  PostgreSQL: kubectl port-forward -n $Namespace svc/cdb-postgres 5432:5432"
}

Write-Info "Monitor logs:"
Write-Info "  kubectl logs -n $Namespace -l app.kubernetes.io/component=signal --tail=100 -f"

Write-Info "Check status:"
Write-Info "  kubectl get pods -n $Namespace"
