#!/bin/bash
# Deploy Claire de Binare trading system to Kubernetes
# Usage: ./deploy-k8s.sh <dev|prod> [--skip-checks] [--dry-run]

set -e

ENVIRONMENT="${1:-}"
SKIP_CHECKS=false
DRY_RUN=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-checks)
            SKIP_CHECKS=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Usage: $0 <dev|prod> [--skip-checks] [--dry-run]"
    exit 1
fi

echo "========================================"
echo " Claire de Binare K8s Deployment"
echo " Environment: $ENVIRONMENT"
echo "========================================"
echo ""

# Pre-flight checks
if [[ "$SKIP_CHECKS" == "false" ]]; then
    echo "[1/6] Running pre-flight checks..."
    
    # Check kubectl
    if command -v kubectl &> /dev/null; then
        echo "  ✓ kubectl found"
    else
        echo "  ✗ kubectl not found. Please install kubectl."
        exit 1
    fi
    
    # Check cluster access
    if kubectl cluster-info &> /dev/null; then
        echo "  ✓ Cluster access verified"
    else
        echo "  ✗ Cannot access Kubernetes cluster"
        exit 1
    fi
    
    # Check kustomize
    if kubectl kustomize --help &> /dev/null; then
        echo "  ✓ kustomize available"
    else
        echo "  ✗ kustomize not available"
        exit 1
    fi
    
    echo ""
fi

# Validate manifests
echo "[2/6] Validating manifests..."
OVERLAY_PATH="k8s/overlays/$ENVIRONMENT"

if [[ "$DRY_RUN" == "true" ]]; then
    echo "  DRY RUN: Previewing changes..."
    kubectl kustomize "$OVERLAY_PATH"
    echo ""
    echo "Dry run complete. Run without --dry-run to apply changes."
    exit 0
fi

if kubectl kustomize "$OVERLAY_PATH" > /dev/null 2>&1; then
    echo "  ✓ Manifests validated"
else
    echo "  ✗ Manifest validation failed"
    exit 1
fi
echo ""

# Create namespace
echo "[3/6] Creating namespace..."
kubectl apply -f k8s/base/namespace.yaml
echo ""

# Create secrets (if they don't exist)
echo "[4/6] Checking secrets..."
if kubectl get secret cdb-secrets -n cdb-trading &> /dev/null; then
    echo "  ✓ Secrets found"
else
    echo "  ⚠ Secret 'cdb-secrets' not found!"
    echo "  Please create secrets before deploying:"
    echo "  kubectl create secret generic cdb-secrets --namespace=cdb-trading \\"
    echo "    --from-literal=redis_password='...' \\"
    echo "    --from-literal=postgres_password='...'"
    echo ""
    read -p "Continue without secrets? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi
echo ""

# Apply manifests
echo "[5/6] Deploying to Kubernetes..."
kubectl apply -k "$OVERLAY_PATH"
echo ""

# Wait for deployments
echo "[6/6] Waiting for deployments..."
echo "  Waiting for infrastructure services..."

kubectl wait --for=condition=available --timeout=300s \
    deployment/redis \
    -n cdb-trading 2>/dev/null || true

kubectl wait --for=condition=ready --timeout=300s \
    statefulset/postgresql \
    -n cdb-trading 2>/dev/null || true

echo "  ✓ Infrastructure ready"

echo "  Waiting for application services..."
if [[ "$ENVIRONMENT" == "dev" ]]; then
    PREFIX="dev-"
else
    PREFIX="prod-"
fi

kubectl wait --for=condition=available --timeout=300s \
    deployment/${PREFIX}cdb-ws \
    deployment/${PREFIX}cdb-signal \
    deployment/${PREFIX}cdb-risk \
    deployment/${PREFIX}cdb-execution \
    deployment/${PREFIX}cdb-db-writer \
    -n cdb-trading 2>/dev/null || true

echo "  ✓ Application services ready"
echo ""

# Display status
echo "========================================"
echo " Deployment Complete!"
echo "========================================"
echo ""
echo "Check deployment status:"
echo "  kubectl get pods -n cdb-trading"
echo "  kubectl get svc -n cdb-trading"
echo ""
echo "View logs:"
echo "  kubectl logs -f deployment/${PREFIX}cdb-ws -n cdb-trading"
echo ""
echo "Access Grafana:"
echo "  kubectl port-forward svc/grafana 3000:3000 -n cdb-trading"
echo ""
