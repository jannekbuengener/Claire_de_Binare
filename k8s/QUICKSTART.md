# Quick Start Guide - Kubernetes Deployment

This guide gets you up and running with Claire de Binare on Kubernetes in 15 minutes.

## Prerequisites

- Kubernetes cluster running (Minikube, Kind, or cloud)
- kubectl installed and configured
- Docker registry access
- 15 minutes ⏱️

## Step 1: Build Images (5 min)

```powershell
# Set your registry
$REGISTRY = "your-registry.azurecr.io"  # or docker.io/username

# Build all images
docker build -t $REGISTRY/cdb-ws:latest -f services/ws/Dockerfile .
docker build -t $REGISTRY/cdb-signal:latest -f services/signal/Dockerfile .
docker build -t $REGISTRY/cdb-risk:latest -f services/risk/Dockerfile .
docker build -t $REGISTRY/cdb-execution:latest -f services/execution/Dockerfile .
docker build -t $REGISTRY/cdb-db-writer:latest -f services/db_writer/Dockerfile .

# Push to registry
docker push $REGISTRY/cdb-ws:latest
docker push $REGISTRY/cdb-signal:latest
docker push $REGISTRY/cdb-risk:latest
docker push $REGISTRY/cdb-execution:latest
docker push $REGISTRY/cdb-db-writer:latest
```

## Step 2: Update Registry in Manifests (1 min)

Edit `k8s/base/kustomization.yaml`:

```yaml
images:
  - name: your-registry/cdb-ws
    newName: YOUR_ACTUAL_REGISTRY/cdb-ws  # <-- Update this
    newTag: latest
  # ... update all other images
```

## Step 3: Create Secrets (2 min)

```powershell
# Generate passwords
$REDIS_PASSWORD = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 24 | % {[char]$_})
$POSTGRES_PASSWORD = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 24 | % {[char]$_})
$GRAFANA_PASSWORD = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 24 | % {[char]$_})

# Create namespace
kubectl create namespace cdb-trading

# Create secrets
kubectl create secret generic cdb-secrets `
  --namespace=cdb-trading `
  --from-literal=redis_password=$REDIS_PASSWORD `
  --from-literal=postgres_password=$POSTGRES_PASSWORD `
  --from-literal=grafana_password=$GRAFANA_PASSWORD `
  --from-literal=mexc_api_key="YOUR_MEXC_TESTNET_KEY" `
  --from-literal=mexc_api_secret="YOUR_MEXC_TESTNET_SECRET" `
  --from-literal=mexc_trade_api_key="YOUR_MEXC_TRADE_KEY" `
  --from-literal=mexc_trade_api_secret="YOUR_MEXC_TRADE_SECRET"
```

## Step 4: Deploy (5 min)

```powershell
# Deploy to dev
.\k8s\deploy-k8s.ps1 -Environment dev

# Wait for pods to be ready (automatic in script)
# This will take 3-5 minutes
```

## Step 5: Verify (2 min)

```powershell
# Check pod status
kubectl get pods -n cdb-trading

# All pods should be Running
# NAME                             READY   STATUS    RESTARTS   AGE
# cdb-redis-xxx                    1/1     Running   0          2m
# cdb-postgres-xxx                 1/1     Running   0          2m
# cdb-prometheus-xxx               1/1     Running   0          2m
# cdb-grafana-xxx                  1/1     Running   0          2m
# cdb-ws-xxx                       1/1     Running   0          1m
# cdb-signal-xxx                   1/1     Running   0          1m
# cdb-risk-xxx                     1/1     Running   0          1m
# cdb-execution-xxx                1/1     Running   0          1m
# cdb-db-writer-xxx                1/1     Running   0          1m

# Check service endpoints
kubectl get svc -n cdb-trading
```

## Step 6: Access Services

```powershell
# Grafana (http://localhost:3000)
kubectl port-forward -n cdb-trading svc/cdb-grafana 3000:3000

# Prometheus (http://localhost:9090)
kubectl port-forward -n cdb-trading svc/cdb-prometheus 9090:9090

# PostgreSQL (localhost:5432)
kubectl port-forward -n cdb-trading svc/cdb-postgres 5432:5432
```

Default Grafana credentials:
- Username: `admin`
- Password: (the one you created in step 3)

## Step 7: Monitor Logs

```powershell
# Signal service (main trading logic)
kubectl logs -n cdb-trading -l app=cdb-signal --tail=50 -f

# All services
kubectl logs -n cdb-trading -l app.kubernetes.io/name=claire-de-binare --tail=20 -f
```

## Troubleshooting

### Pods Not Starting

```powershell
# Check pod events
kubectl describe pod -n cdb-trading <pod-name>

# Check logs
kubectl logs -n cdb-trading <pod-name>
```

### Image Pull Errors

- Verify registry credentials
- Check image names in kustomization.yaml
- Ensure images exist in registry

### Secret Errors

```powershell
# Verify secret exists
kubectl get secret -n cdb-trading cdb-secrets

# Recreate if needed
kubectl delete secret -n cdb-trading cdb-secrets
# Then run step 3 again
```

## Cleanup

```powershell
# Remove everything
.\k8s\cleanup-k8s.ps1

# Or manually
kubectl delete namespace cdb-trading
```

## Next Steps

1. **Review Logs**: Check that services are operating correctly
2. **Import Dashboards**: Add Grafana dashboards from `infrastructure/monitoring/grafana/dashboards/`
3. **Configure Alerts**: Set up Prometheus alerting
4. **Run E2E Tests**: Validate the deployment
5. **Production Deployment**: When ready, use `.\k8s\deploy-k8s.ps1 -Environment prod`

## Common Commands

```powershell
# View all resources
kubectl get all -n cdb-trading

# Restart a deployment
kubectl rollout restart -n cdb-trading deployment/cdb-signal

# Scale a deployment
kubectl scale -n cdb-trading deployment/cdb-signal --replicas=2

# View resource usage
kubectl top pods -n cdb-trading
```

## Help

- **Full Documentation**: See `k8s/README.md`
- **Secrets Guide**: See `k8s/SECRETS_GUIDE.md`
- **Issues**: Check logs and events first
- **Support**: Review troubleshooting section in README

---

**Total Time**: ~15 minutes ⏱️  
**Status**: ✅ Ready to deploy  
**Next**: Build images and go! 🚀
