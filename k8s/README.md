# Claire de Binare - Kubernetes Deployment Guide

## Overview

This directory contains Kubernetes manifests for deploying the Claire de Binare algorithmic trading system. The deployment uses **Kustomize** for configuration management, allowing easy customization for different environments.

## Architecture

### Components

#### Infrastructure Services
- **Redis** - In-memory cache and message broker
- **PostgreSQL** - Primary data store
- **Prometheus** - Metrics collection and monitoring
- **Grafana** - Visualization and dashboards

#### Application Services
- **WebSocket Service (cdb-ws)** - Market data ingestion via WebSocket
- **Signal Service (cdb-signal)** - Trading signal generation
- **Risk Service (cdb-risk)** - Risk management and validation
- **Execution Service (cdb-execution)** - Order execution
- **DB Writer Service (cdb-db-writer)** - Database persistence

### Directory Structure

```
k8s/
├── base/                           # Base manifests (environment-agnostic)
│   ├── namespace.yaml              # Namespace definition
│   ├── configmap.yaml              # Non-sensitive configuration
│   ├── secret-template.yaml        # Secret template (DO NOT commit actual secrets)
│   ├── pvcs.yaml                   # PersistentVolumeClaims
│   ├── kustomization.yaml          # Base kustomization
│   ├── infrastructure/             # Infrastructure components
│   │   ├── redis.yaml              # Redis deployment + service
│   │   ├── postgres.yaml           # PostgreSQL deployment + service
│   │   ├── prometheus.yaml         # Prometheus deployment + service
│   │   └── grafana.yaml            # Grafana deployment + service
│   └── services/                   # Application services
│       ├── ws-deployment.yaml      # WebSocket service
│       ├── signal-deployment.yaml  # Signal service
│       ├── risk-deployment.yaml    # Risk service
│       ├── execution-deployment.yaml # Execution service
│       └── db-writer-deployment.yaml # DB writer service
└── overlays/                       # Environment-specific overlays
    ├── dev/                        # Development environment
    │   ├── kustomization.yaml      # Dev kustomization
    │   ├── configmap-patch.yaml    # Dev config overrides
    │   └── deployment-patches.yaml # Dev deployment patches
    └── prod/                       # Production environment
        ├── kustomization.yaml      # Prod kustomization
        ├── deployment-patches.yaml # Prod deployment patches
        └── security-patches.yaml   # Prod security enhancements
```

## Prerequisites

1. **Kubernetes Cluster** (v1.24+)
   - Minikube, Kind, or cloud provider (GKE, EKS, AKS)
   - Sufficient resources: 8GB RAM, 4 CPU cores minimum

2. **Tools**
   - `kubectl` (v1.24+)
   - `kustomize` (v4.5+) or use `kubectl apply -k`
   - Docker registry access for custom images

3. **Storage**
   - StorageClass named `standard` (or update manifests)
   - Support for ReadWriteOnce PersistentVolumes

## Quick Start

### Step 1: Build and Push Container Images

Build all service images:

```bash
# Build images for all services
docker build -t your-registry/cdb-ws:latest -f services/ws/Dockerfile .
docker build -t your-registry/cdb-signal:latest -f services/signal/Dockerfile .
docker build -t your-registry/cdb-risk:latest -f services/risk/Dockerfile .
docker build -t your-registry/cdb-execution:latest -f services/execution/Dockerfile .
docker build -t your-registry/cdb-db-writer:latest -f services/db_writer/Dockerfile .

# Push to your registry
docker push your-registry/cdb-ws:latest
docker push your-registry/cdb-signal:latest
docker push your-registry/cdb-risk:latest
docker push your-registry/cdb-execution:latest
docker push your-registry/cdb-db-writer:latest
```

### Step 2: Create Secrets

**IMPORTANT**: Never commit actual secrets to git!

Create secrets manually:

```bash
# Create namespace first
kubectl create namespace cdb-trading

# Create secrets
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-literal=redis_password='your-redis-password' \
  --from-literal=postgres_password='your-postgres-password' \
  --from-literal=grafana_password='your-grafana-password' \
  --from-literal=mexc_api_key='your-mexc-testnet-api-key' \
  --from-literal=mexc_api_secret='your-mexc-testnet-api-secret' \
  --from-literal=mexc_trade_api_key='your-mexc-trade-key' \
  --from-literal=mexc_trade_api_secret='your-mexc-trade-secret'
```

Or use **Sealed Secrets** for GitOps (recommended):

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

### Step 3: Deploy to Development

```bash
# Deploy using kustomize
kubectl apply -k k8s/overlays/dev

# Or using kustomize standalone
kustomize build k8s/overlays/dev | kubectl apply -f -

# Verify deployment
kubectl get pods -n cdb-trading
kubectl get svc -n cdb-trading
```

### Step 4: Access Services (Dev)

Port forward to access services locally:

```bash
# Grafana
kubectl port-forward -n cdb-trading svc/cdb-grafana 3000:3000

# Prometheus
kubectl port-forward -n cdb-trading svc/cdb-prometheus 9090:9090

# PostgreSQL
kubectl port-forward -n cdb-trading svc/cdb-postgres 5432:5432

# Redis
kubectl port-forward -n cdb-trading svc/cdb-redis 6379:6379
```

## Production Deployment

### Pre-deployment Checklist

Before deploying to production, ensure:

- [ ] All E2E tests pass (≥95% pass rate)
- [ ] Security scans complete (0 critical CVEs)
- [ ] Secrets properly managed (Sealed Secrets or External Secrets)
- [ ] Resource limits reviewed and appropriate
- [ ] Monitoring and alerting configured
- [ ] Backup strategy in place
- [ ] Rollback plan documented and tested
- [ ] MEXC_TESTNET=false and API keys verified
- [ ] Budget and capacity approved

### Deploy to Production

```bash
# Update image tags in k8s/overlays/prod/kustomization.yaml
# Use specific version tags, not 'latest'

# Deploy
kubectl apply -k k8s/overlays/prod

# Monitor rollout
kubectl rollout status -n cdb-trading deployment/cdb-ws
kubectl rollout status -n cdb-trading deployment/cdb-signal
kubectl rollout status -n cdb-trading deployment/cdb-risk
kubectl rollout status -n cdb-trading deployment/cdb-execution
kubectl rollout status -n cdb-trading deployment/cdb-db-writer

# Check health
kubectl get pods -n cdb-trading
kubectl logs -n cdb-trading -l app.kubernetes.io/component=signal --tail=100
```

## Configuration Management

### Environment Variables

Configured via ConfigMap (`k8s/base/configmap.yaml`):
- `REDIS_HOST`, `POSTGRES_HOST` - Service endpoints
- `MEXC_TESTNET` - Use testnet API (default: true)
- `DRY_RUN` - Log trades without executing (default: true)
- `SIGNAL_STRATEGY_ID` - Trading strategy (default: paper)
- `LOG_LEVEL` - Logging verbosity (default: WARNING)

### Secrets

Managed via Secret (`cdb-secrets`):
- `redis_password` - Redis authentication
- `postgres_password` - PostgreSQL authentication
- `grafana_password` - Grafana admin password
- `mexc_api_key`, `mexc_api_secret` - MEXC API credentials
- `mexc_trade_api_key`, `mexc_trade_api_secret` - MEXC trading credentials

### Overlays

#### Development
- Reduced resource requests/limits
- Debug logging enabled
- Single replica per service
- Relaxed security for debugging

#### Production
- Higher resource limits
- Multiple replicas for HA
- Strict security policies (seccomp, read-only filesystem)
- Production logging levels

## Storage

### PersistentVolumeClaims

| PVC | Size | Usage |
|-----|------|-------|
| redis-data-pvc | 5Gi | Redis persistence |
| postgres-data-pvc | 20Gi | PostgreSQL data |
| prometheus-data-pvc | 10Gi | Prometheus metrics |
| grafana-data-pvc | 2Gi | Grafana dashboards |
| validation-data-pvc | 5Gi | Risk validation data |

**Note**: Adjust sizes based on your data retention requirements.

## Monitoring

### Prometheus

Metrics available at: `http://cdb-prometheus:9090`

Scrape targets:
- cdb-ws:8000
- cdb-signal:8005
- cdb-risk:8002
- cdb-execution:8003

### Grafana

Dashboards available at: `http://cdb-grafana:3000`

Default credentials:
- Username: `admin`
- Password: (from secret)

Import dashboards from `infrastructure/monitoring/grafana/dashboards/`

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -n cdb-trading

# Describe pod for events
kubectl describe pod -n cdb-trading <pod-name>

# Check logs
kubectl logs -n cdb-trading <pod-name>
```

### Secret Not Found

```bash
# Verify secret exists
kubectl get secret -n cdb-trading cdb-secrets

# Check secret contents (base64 encoded)
kubectl get secret -n cdb-trading cdb-secrets -o yaml
```

### Persistent Volume Issues

```bash
# Check PVC status
kubectl get pvc -n cdb-trading

# Check PV bindings
kubectl get pv

# Describe PVC for events
kubectl describe pvc -n cdb-trading <pvc-name>
```

### Database Connection Issues

```bash
# Test PostgreSQL connectivity from pod
kubectl exec -it -n cdb-trading <pod-name> -- sh
apk add postgresql-client
psql -h cdb-postgres -U claire_user -d claire_de_binare

# Test Redis connectivity
kubectl exec -it -n cdb-trading <pod-name> -- sh
apk add redis
redis-cli -h cdb-redis -a <password> ping
```

## Maintenance

### Updating Images

```bash
# Update image tag in overlay kustomization.yaml
# Then apply changes
kubectl apply -k k8s/overlays/prod

# Or use kubectl set image
kubectl set image -n cdb-trading deployment/cdb-signal \
  signal=your-registry/cdb-signal:v1.1.0

# Verify rollout
kubectl rollout status -n cdb-trading deployment/cdb-signal
```

### Rollback

```bash
# View rollout history
kubectl rollout history -n cdb-trading deployment/cdb-signal

# Rollback to previous version
kubectl rollout undo -n cdb-trading deployment/cdb-signal

# Rollback to specific revision
kubectl rollout undo -n cdb-trading deployment/cdb-signal --to-revision=2
```

### Scaling

```bash
# Scale deployment
kubectl scale -n cdb-trading deployment/cdb-signal --replicas=3

# Or update kustomization overlay and apply
```

### Database Backups

```bash
# Backup PostgreSQL
kubectl exec -n cdb-trading cdb-postgres-<pod-id> -- \
  pg_dump -U claire_user claire_de_binare > backup.sql

# Restore PostgreSQL
kubectl exec -i -n cdb-trading cdb-postgres-<pod-id> -- \
  psql -U claire_user claire_de_binare < backup.sql
```

## Security Best Practices

1. **Use Sealed Secrets or External Secrets Operator** - Never commit secrets to git
2. **Enable RBAC** - Restrict access to namespace resources
3. **Network Policies** - Limit inter-pod communication
4. **Pod Security Standards** - Enforce restricted PSS
5. **Read-only Root Filesystem** - Already configured in manifests
6. **Non-root User** - All containers run as non-root
7. **Resource Limits** - Prevent resource exhaustion
8. **Image Scanning** - Scan for CVEs before deployment
9. **TLS/mTLS** - Encrypt internal communication (future enhancement)

## CI/CD Integration

### GitLab CI Example

```yaml
deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl apply -k k8s/overlays/prod
  only:
    - main
```

### GitHub Actions Example

```yaml
- name: Deploy to Kubernetes
  run: |
    kubectl apply -k k8s/overlays/prod
```

## Migration from Docker Compose

### Key Differences

| Docker Compose | Kubernetes |
|----------------|-----------|
| docker-compose.yml | Multiple YAML manifests |
| Environment variables | ConfigMaps + Secrets |
| Volumes | PersistentVolumeClaims |
| Networks | Services + Network Policies |
| Port bindings | Services (ClusterIP/NodePort/LoadBalancer) |
| Depends_on | Init containers / readiness probes |

### Migration Steps

1. **Build container images** for all services
2. **Push images** to container registry
3. **Create secrets** in Kubernetes
4. **Deploy infrastructure** (Redis, PostgreSQL)
5. **Wait for infrastructure** to be healthy
6. **Deploy application services**
7. **Verify functionality** with E2E tests
8. **Configure monitoring** and alerts
9. **Set up backups** and disaster recovery
10. **Document rollback procedures**

## Support

For issues or questions:
- Check logs: `kubectl logs -n cdb-trading <pod-name>`
- Review events: `kubectl get events -n cdb-trading`
- Consult documentation in `/docs`
- Review governance policies in `/governance`

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Claire de Binare Docs Hub](../DOCS_MOVED_TO_DOCS_HUB.md)
- [Docker Compose Configuration](../infrastructure/compose/)

---

**Status**: ✅ READY - Production-grade Kubernetes manifests
**Last Updated**: 2026-01-06
**Maintainer**: Infrastructure Team
