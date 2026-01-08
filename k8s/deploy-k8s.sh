#!/bin/bash
# Claire de Binare - Kubernetes Deployment Helper
# Usage: ./deploy-k8s.sh [dev|prod]

set -euo pipefail

ENVIRONMENT="${1:-dev}"
NAMESPACE="cdb-trading"
REGISTRY="${DOCKER_REGISTRY:-your-registry}"
VERSION="${VERSION:-latest}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Use 'dev' or 'prod'"
    exit 1
fi

log_info "Deploying to $ENVIRONMENT environment..."

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl."
    exit 1
fi

if ! command -v kustomize &> /dev/null; then
    log_warn "kustomize not found. Will use 'kubectl apply -k' instead."
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    exit 1
fi

log_info "Connected to cluster: $(kubectl config current-context)"

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    log_info "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
else
    log_info "Namespace $NAMESPACE already exists"
fi

# Check if secrets exist
if ! kubectl get secret -n "$NAMESPACE" cdb-secrets &> /dev/null; then
    log_error "Secret 'cdb-secrets' not found in namespace $NAMESPACE"
    log_error "Please create secrets first:"
    log_error "  kubectl create secret generic cdb-secrets \\"
    log_error "    --namespace=$NAMESPACE \\"
    log_error "    --from-literal=redis_password='...' \\"
    log_error "    --from-literal=postgres_password='...' \\"
    log_error "    --from-literal=grafana_password='...' \\"
    log_error "    --from-literal=mexc_api_key='...' \\"
    log_error "    --from-literal=mexc_api_secret='...'"
    exit 1
fi

log_info "Secrets found"

# Production safety check
if [[ "$ENVIRONMENT" == "prod" ]]; then
    log_warn "==================================="
    log_warn "PRODUCTION DEPLOYMENT"
    log_warn "==================================="
    log_warn "This will deploy to PRODUCTION!"
    log_warn "Have you:"
    log_warn "  - Reviewed all changes?"
    log_warn "  - Run E2E tests (≥95% pass)?"
    log_warn "  - Scanned for CVEs (0 critical)?"
    log_warn "  - Verified secrets are correct?"
    log_warn "  - Prepared rollback plan?"
    echo ""
    read -p "Continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
fi

# Apply manifests
log_info "Applying manifests for $ENVIRONMENT..."

if command -v kustomize &> /dev/null; then
    kustomize build "k8s/overlays/$ENVIRONMENT" | kubectl apply -f -
else
    kubectl apply -k "k8s/overlays/$ENVIRONMENT"
fi

# Wait for infrastructure to be ready
log_info "Waiting for infrastructure services..."

kubectl wait --for=condition=ready \
    --timeout=300s \
    -n "$NAMESPACE" \
    pod -l app=cdb-redis

kubectl wait --for=condition=ready \
    --timeout=300s \
    -n "$NAMESPACE" \
    pod -l app=cdb-postgres

log_info "Infrastructure services ready"

# Wait for application services
log_info "Waiting for application services..."

for service in cdb-ws cdb-signal cdb-risk cdb-execution cdb-db-writer; do
    log_info "Checking rollout status: $service"
    kubectl rollout status -n "$NAMESPACE" "deployment/$service" --timeout=5m || true
done

# Check pod status
log_info "Pod status:"
kubectl get pods -n "$NAMESPACE"

# Check service status
log_info "Service status:"
kubectl get svc -n "$NAMESPACE"

# Final health check
log_info "Running health checks..."

FAILED=0

for service in cdb-ws cdb-signal cdb-risk cdb-execution; do
    POD=$(kubectl get pod -n "$NAMESPACE" -l "app=$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$POD" ]]; then
        log_error "No pod found for $service"
        FAILED=1
        continue
    fi
    
    # Check if pod is running
    STATUS=$(kubectl get pod -n "$NAMESPACE" "$POD" -o jsonpath='{.status.phase}')
    if [[ "$STATUS" != "Running" ]]; then
        log_error "$service pod is not running (status: $STATUS)"
        FAILED=1
    else
        log_info "$service is running"
    fi
done

if [[ $FAILED -eq 1 ]]; then
    log_error "Some services failed to deploy properly"
    log_info "Check logs with: kubectl logs -n $NAMESPACE <pod-name>"
    exit 1
fi

log_info "==================================="
log_info "Deployment completed successfully!"
log_info "==================================="

if [[ "$ENVIRONMENT" == "dev" ]]; then
    log_info "Access services via port-forward:"
    log_info "  Grafana:    kubectl port-forward -n $NAMESPACE svc/cdb-grafana 3000:3000"
    log_info "  Prometheus: kubectl port-forward -n $NAMESPACE svc/cdb-prometheus 9090:9090"
    log_info "  PostgreSQL: kubectl port-forward -n $NAMESPACE svc/cdb-postgres 5432:5432"
fi

log_info "Monitor logs:"
log_info "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=signal --tail=100 -f"

log_info "Check status:"
log_info "  kubectl get pods -n $NAMESPACE"
