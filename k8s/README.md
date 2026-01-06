# Kubernetes Deployment - Claire de Binare Trading System

**Status: ✅ COMPLETE - Production-Ready**

Comprehensive Kubernetes manifests with GitOps support (FluxCD/ArgoCD) for the Claire de Binare cryptocurrency trading system.

## 📦 What's Included

- **25+ manifest files** with full configuration
- **4 infrastructure services**: Redis, PostgreSQL, Prometheus, Grafana
- **5 application services**: WebSocket, Signal, Risk, Execution, DB Writer
- **2 environment overlays**: Development and Production
- **GitOps configuration**: FluxCD and ArgoCD support
- **Automation scripts**: PowerShell and Bash deployment scripts
- **Comprehensive documentation**: Quick start, secrets management, troubleshooting

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│ Kubernetes Cluster (cdb-trading)        │
│                                         │
├─────────────────────────────────────────┤
│ Infrastructure Layer:                   │
│  • Redis (in-memory cache)              │
│  • PostgreSQL (data store)              │
│  • Prometheus (metrics)                 │
│  • Grafana (dashboards)                 │
├─────────────────────────────────────────┤
│ Application Services:                   │
│  • WebSocket (market data ingestion)    │
│  • Signal (trading signal generation)   │
│  • Risk (validation & limits)           │
│  • Execution (order execution)          │
│  • DB Writer (data persistence)         │
└─────────────────────────────────────────┘
```

## 📁 Directory Structure

```
k8s/
├── README.md                    # This file
├── QUICKSTART.md                # 15-minute deployment guide
├── SECRETS_GUIDE.md             # Secrets management guide
├── DELIVERY_SUMMARY.md          # Complete delivery overview
├── deploy-k8s.ps1               # PowerShell deployment script
├── deploy-k8s.sh                # Bash deployment script
├── cleanup-k8s.ps1              # Cleanup script
├── base/                        # Base manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret-template.yaml
│   ├── pvcs.yaml
│   ├── kustomization.yaml
│   ├── infrastructure/
│   │   ├── redis.yaml
│   │   ├── postgresql.yaml
│   │   ├── prometheus.yaml
│   │   └── grafana.yaml
│   └── services/
│       ├── ws-deployment.yaml
│       ├── ws-service.yaml
│       ├── signal-deployment.yaml
│       ├── signal-service.yaml
│       ├── risk-deployment.yaml
│       ├── execution-deployment.yaml
│       └── db-writer-deployment.yaml
├── overlays/                    # Environment-specific configs
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   ├── replica-patch.yaml
│   │   └── resource-patch.yaml
│   └── prod/
│       ├── kustomization.yaml
│       ├── replica-patch.yaml
│       └── security-patch.yaml
└── flux/                        # GitOps configuration
    ├── README.md
    ├── gitops-sync.yaml         # FluxCD configuration
    └── argocd-application.yaml  # ArgoCD configuration
```

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes cluster** (local or cloud)
2. **kubectl** installed and configured
3. **Container registry** with images pushed
4. **Secrets** created (see [SECRETS_GUIDE.md](SECRETS_GUIDE.md))

### Deploy in 3 Steps

```bash
# 1. Create secrets
kubectl create secret generic cdb-secrets --namespace=cdb-trading \
  --from-literal=redis_password="your-redis-pass" \
  --from-literal=postgres_password="your-postgres-pass" \
  --from-literal=exchange_api_key="your-api-key" \
  --from-literal=exchange_api_secret="your-api-secret"

# 2. Deploy to development
./k8s/deploy-k8s.sh dev

# 3. Verify deployment
kubectl get pods -n cdb-trading
```

See [QUICKSTART.md](QUICKSTART.md) for detailed step-by-step guide.

## ✨ Key Features

### Security Hardening
- ✅ Non-root containers (user: 1000)
- ✅ Read-only root filesystem
- ✅ Seccomp profiles (RuntimeDefault)
- ✅ Dropped capabilities (ALL)
- ✅ Secrets as mounted files (not env vars)
- ✅ RBAC-ready structure

### High Availability
- ✅ Multiple replicas in production
- ✅ Rolling deployments (zero-downtime)
- ✅ Liveness/readiness probes
- ✅ Resource limits and requests
- ✅ Pod disruption budgets ready

### Observability
- ✅ Prometheus metrics collection
- ✅ Grafana dashboards
- ✅ Structured logging
- ✅ Health check endpoints

### GitOps Ready
- ✅ FluxCD configuration included
- ✅ ArgoCD configuration included
- ✅ Automatic reconciliation
- ✅ Rollback on failure

## 🔧 Configuration

### Environment Overlays

**Development** (`overlays/dev/`):
- 1 replica per service
- Reduced resources
- Debug logging
- Fast iteration

**Production** (`overlays/prod/`):
- 2+ replicas for HA
- Production resources
- INFO logging
- Security hardening

### Resource Requirements

| Service | Dev Resources | Prod Resources |
|---------|--------------|----------------|
| WebSocket | 128Mi/100m | 512Mi/500m |
| Signal | 256Mi/150m | 1Gi/1000m |
| Risk | 256Mi/150m | 1Gi/1000m |
| Execution | 256Mi/150m | 1Gi/1000m |
| DB Writer | 128Mi/100m | 512Mi/500m |
| Redis | 128Mi/100m | 512Mi/500m |
| PostgreSQL | 256Mi/200m | 1Gi/1000m |

## 🔐 Secrets Management

See [SECRETS_GUIDE.md](SECRETS_GUIDE.md) for detailed guide on:
1. Manual secret creation
2. Sealed Secrets (GitOps)
3. External Secrets Operator (Cloud)
4. HashiCorp Vault integration

## 📊 Monitoring

### Access Grafana

```bash
kubectl port-forward svc/grafana 3000:3000 -n cdb-trading
# Open http://localhost:3000
```

### Access Prometheus

```bash
kubectl port-forward svc/prometheus 9090:9090 -n cdb-trading
# Open http://localhost:9090
```

**Note**: For production HA monitoring, consider:
- Running 2+ Prometheus replicas with federation
- Using Thanos for long-term storage and HA
- Implementing AlertManager for alerting

### View Logs

```bash
# Specific service
kubectl logs -f deployment/dev-cdb-ws -n cdb-trading

# All services
kubectl logs -l app.kubernetes.io/name=claire-de-binare -n cdb-trading
```

## 🔄 GitOps Deployment

### Using FluxCD

```bash
# Install FluxCD
flux bootstrap github \
  --owner=jannekbuengener \
  --repository=Claire_de_Binare \
  --branch=main \
  --path=./k8s/flux

# Monitor reconciliation
flux get all
```

### Using ArgoCD

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Apply applications
kubectl apply -f k8s/flux/argocd-application.yaml

# Access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

See [flux/README.md](flux/README.md) for detailed GitOps setup.

## 🧹 Cleanup

### Remove specific environment

```powershell
# PowerShell
.\k8s\cleanup-k8s.ps1 -Environment dev

# Bash
./k8s/cleanup-k8s.sh dev
```

### Remove everything

```bash
kubectl delete namespace cdb-trading
```

## 📚 Documentation

- [QUICKSTART.md](QUICKSTART.md) - 15-minute deployment guide
- [SECRETS_GUIDE.md](SECRETS_GUIDE.md) - Secrets management patterns
- [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md) - Complete delivery overview
- [flux/README.md](flux/README.md) - GitOps setup guide

## ✅ Acceptance Criteria Met

- [x] All services containerized and stateless
- [x] ConfigMaps/Secrets for configuration
- [x] Resource limits defined
- [x] Liveness/Readiness probes implemented
- [x] GitOps reconcile configured (FluxCD/ArgoCD)
- [x] Kustomize for deployments
- [x] Security hardening applied
- [x] Monitoring integrated

## 🤝 Support

For issues or questions:
1. Check the [QUICKSTART.md](QUICKSTART.md) guide
2. Review [SECRETS_GUIDE.md](SECRETS_GUIDE.md) for secrets issues
3. Check [flux/README.md](flux/README.md) for GitOps troubleshooting
4. Consult the main project documentation

## 📝 Next Steps

1. Build container images for all services
2. Push images to your container registry
3. Update `kustomization.yaml` with your registry
4. Create secrets using one of the documented methods
5. Deploy to development environment
6. Run E2E tests
7. Deploy to production when ready
