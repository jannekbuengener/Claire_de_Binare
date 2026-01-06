# FluxCD GitOps Configuration

This directory contains FluxCD configuration for GitOps-based deployment and reconciliation of the Claire de Binare trading system.

## Prerequisites

1. **Install FluxCD CLI**:
   ```bash
   curl -s https://fluxcd.io/install.sh | sudo bash
   ```

2. **Verify Kubernetes Cluster Access**:
   ```bash
   kubectl cluster-info
   ```

## Installation

### 1. Bootstrap FluxCD

For GitHub:
```bash
flux bootstrap github \
  --owner=jannekbuengener \
  --repository=Claire_de_Binare \
  --branch=main \
  --path=./k8s/flux \
  --personal
```

For other Git providers:
```bash
flux bootstrap git \
  --url=https://github.com/jannekbuengener/Claire_de_Binare \
  --branch=main \
  --path=./k8s/flux
```

### 2. Verify Installation

```bash
# Check FluxCD components
flux check

# Check GitRepository source
flux get sources git

# Check Kustomizations
flux get kustomizations
```

### 3. Apply GitOps Configuration

```bash
kubectl apply -f k8s/flux/gitops-sync.yaml
```

## How It Works

### GitOps Reconciliation Loop

```
┌─────────────────────────────────────────┐
│  Git Repository (Source of Truth)      │
│  - k8s/base/                           │
│  - k8s/overlays/dev/                   │
│  - k8s/overlays/prod/                  │
└──────────────┬──────────────────────────┘
               │
               │ 1. FluxCD polls every 1m
               ▼
┌─────────────────────────────────────────┐
│  FluxCD GitRepository Controller        │
│  - Detects changes                      │
│  - Fetches manifests                    │
└──────────────┬──────────────────────────┘
               │
               │ 2. Apply changes
               ▼
┌─────────────────────────────────────────┐
│  FluxCD Kustomization Controller        │
│  - Validates manifests                  │
│  - Applies to cluster                   │
│  - Prunes deleted resources             │
└──────────────┬──────────────────────────┘
               │
               │ 3. Reconcile
               ▼
┌─────────────────────────────────────────┐
│  Kubernetes Cluster                     │
│  - Deployments updated                  │
│  - Health checks validated              │
│  - Automatic rollback on failure        │
└─────────────────────────────────────────┘
```

## Configuration Components

### GitRepository
- **URL**: `https://github.com/jannekbuengener/Claire_de_Binare`
- **Branch**: `main`
- **Poll Interval**: 1 minute
- Monitors the repository for changes

### Kustomizations
1. **cdb-infrastructure**: Base infrastructure (Redis, PostgreSQL, Prometheus, Grafana)
   - Interval: 5 minutes
   - Path: `./k8s/base`
   
2. **cdb-services-dev**: Development environment services
   - Interval: 5 minutes
   - Path: `./k8s/overlays/dev`
   - Depends on: `cdb-infrastructure`
   
3. **cdb-services-prod**: Production environment services
   - Interval: 10 minutes
   - Path: `./k8s/overlays/prod`
   - Depends on: `cdb-infrastructure`

## Features

✅ **Automatic Reconciliation**: Changes in Git are automatically applied to the cluster
✅ **Health Checks**: FluxCD monitors deployment health and rolls back on failure
✅ **Dependency Management**: Services wait for infrastructure to be ready
✅ **Prune**: Deleted resources in Git are automatically removed from cluster
✅ **Validation**: Client-side validation before applying changes

## Monitoring

### Check Reconciliation Status

```bash
# Overall status
flux get all

# Specific resource
flux get kustomizations cdb-infrastructure
flux get kustomizations cdb-services-dev
flux get kustomizations cdb-services-prod

# Logs
flux logs --follow --tail=10
```

### Trigger Manual Reconciliation

```bash
# Force immediate sync
flux reconcile source git claire-de-binare
flux reconcile kustomization cdb-infrastructure
flux reconcile kustomization cdb-services-dev
```

### Suspend/Resume Reconciliation

```bash
# Suspend (for maintenance)
flux suspend kustomization cdb-services-prod

# Resume
flux resume kustomization cdb-services-prod
```

## Troubleshooting

### Check FluxCD Events

```bash
kubectl get events -n flux-system --sort-by='.lastTimestamp'
```

### Check Kustomization Status

```bash
kubectl describe kustomization cdb-infrastructure -n flux-system
```

### View FluxCD Logs

```bash
kubectl logs -n flux-system deployment/kustomize-controller -f
kubectl logs -n flux-system deployment/source-controller -f
```

## Deployment Workflow

### 1. Make Changes
```bash
# Edit manifests
vim k8s/base/services/ws-deployment.yaml

# Commit and push
git add k8s/
git commit -m "Update ws deployment"
git push
```

### 2. FluxCD Automatically:
- Detects the change (within 1 minute)
- Validates the manifests
- Applies to cluster
- Monitors health checks
- Rolls back if deployment fails

### 3. Verify Deployment
```bash
# Check deployment status
kubectl rollout status deployment/dev-cdb-ws -n cdb-trading

# Check FluxCD status
flux get kustomizations
```

## Security

- **Git Credentials**: Stored in `flux-system` secret
- **Image Pull Secrets**: Configure in base kustomization
- **RBAC**: FluxCD has minimal required permissions
- **Secrets Management**: Use Sealed Secrets or External Secrets Operator

## Migration from Manual Deployment

1. Deploy infrastructure manually first
2. Bootstrap FluxCD
3. Apply GitOps configuration
4. Verify reconciliation works
5. Switch to GitOps-only deployments

## Alternative: ArgoCD

If you prefer ArgoCD instead of FluxCD, see `argocd-application.yaml` for configuration.

## References

- [FluxCD Documentation](https://fluxcd.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [GitOps Principles](https://opengitops.dev/)
