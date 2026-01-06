# Quick Start Guide - 15 Minutes to Deployment

Get Claire de Binare running on Kubernetes in 15 minutes or less.

## Prerequisites Checklist

- [ ] Kubernetes cluster (local or cloud)
- [ ] `kubectl` installed
- [ ] Container images built and pushed
- [ ] 15 minutes of time

## Step 1: Prepare Images (5 minutes)

### Build Images

```bash
cd /path/to/Claire_de_Binare

# Build all service images
docker build -t your-registry/cdb-ws:latest -f services/ws/Dockerfile .
docker build -t your-registry/cdb-signal:latest -f services/signal/Dockerfile .
docker build -t your-registry/cdb-risk:latest -f services/risk/Dockerfile .
docker build -t your-registry/cdb-execution:latest -f services/execution/Dockerfile .
docker build -t your-registry/cdb-db-writer:latest -f services/db_writer/Dockerfile .
```

### Push to Registry

```bash
docker push your-registry/cdb-ws:latest
docker push your-registry/cdb-signal:latest
docker push your-registry/cdb-risk:latest
docker push your-registry/cdb-execution:latest
docker push your-registry/cdb-db-writer:latest
```

### Update Kustomization

Edit `k8s/base/kustomization.yaml` and replace `your-registry` with your actual registry:

```yaml
images:
  - name: your-registry/cdb-ws
    newName: your-actual-registry/cdb-ws
    newTag: latest
  # ... repeat for other images
```

## Step 2: Create Secrets (2 minutes)

Choose one method:

### Method A: Quick Manual Creation

```bash
kubectl create namespace cdb-trading

kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-literal=redis_password="change-me-redis-pass" \
  --from-literal=postgres_password="change-me-pg-pass" \
  --from-literal=postgres_admin_password="change-me-admin-pass" \
  --from-literal=api_key="your-api-key" \
  --from-literal=api_secret="your-api-secret" \
  --from-literal=exchange_api_key="your-exchange-key" \
  --from-literal=exchange_api_secret="your-exchange-secret"
```

### Method B: From .env File

```bash
# Create .env file
cat > /tmp/secrets.env <<EOF
redis_password=your-redis-password
postgres_password=your-postgres-password
postgres_admin_password=your-admin-password
api_key=your-api-key
api_secret=your-api-secret
exchange_api_key=your-exchange-key
exchange_api_secret=your-exchange-secret
EOF

# Create secret from file
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-env-file=/tmp/secrets.env

# Clean up
rm /tmp/secrets.env
```

## Step 3: Deploy to Kubernetes (3 minutes)

### Option A: Using Deployment Script (Recommended)

**PowerShell (Windows):**
```powershell
.\k8s\deploy-k8s.ps1 -Environment dev
```

**Bash (Linux/Mac):**
```bash
./k8s/deploy-k8s.sh dev
```

### Option B: Manual kubectl

```bash
# Apply base configuration
kubectl apply -k k8s/overlays/dev

# Watch deployment progress
kubectl get pods -n cdb-trading -w
```

## Step 4: Verify Deployment (5 minutes)

### Check Pod Status

```bash
kubectl get pods -n cdb-trading
```

Expected output:
```
NAME                              READY   STATUS    RESTARTS   AGE
dev-cdb-db-writer-xxx-xxx        1/1     Running   0          2m
dev-cdb-execution-xxx-xxx        1/1     Running   0          2m
dev-cdb-risk-xxx-xxx             1/1     Running   0          2m
dev-cdb-signal-xxx-xxx           1/1     Running   0          2m
dev-cdb-ws-xxx-xxx               1/1     Running   0          2m
grafana-xxx-xxx                  1/1     Running   0          3m
postgresql-0                     1/1     Running   0          3m
prometheus-xxx-xxx               1/1     Running   0          3m
redis-xxx-xxx                    1/1     Running   0          3m
```

### Check Services

```bash
kubectl get svc -n cdb-trading
```

### View Logs

```bash
# WebSocket service
kubectl logs -f deployment/dev-cdb-ws -n cdb-trading

# All services
kubectl logs -l app.kubernetes.io/name=claire-de-binare -n cdb-trading --tail=50
```

### Access Grafana

```bash
# Port forward
kubectl port-forward svc/grafana 3000:3000 -n cdb-trading

# Open browser: http://localhost:3000
# Default credentials:
#   User: admin
#   Password: (from postgres_admin_password secret)
```

### Access Prometheus

```bash
kubectl port-forward svc/prometheus 9090:9090 -n cdb-trading
# Open browser: http://localhost:9090
```

## Common Issues & Solutions

### Issue: Pods Stuck in "ImagePullBackOff"

**Solution:** Check image names in kustomization.yaml match your registry.

```bash
kubectl describe pod <pod-name> -n cdb-trading
```

Update `k8s/base/kustomization.yaml` with correct registry and image tags.

### Issue: Pods Stuck in "CrashLoopBackOff"

**Solution:** Check logs for errors.

```bash
kubectl logs <pod-name> -n cdb-trading
```

Common causes:
- Missing or incorrect secrets
- Database connection issues
- Invalid configuration

### Issue: Secrets Not Found

**Solution:** Verify secret exists and has correct keys.

```bash
# Check if secret exists
kubectl get secret cdb-secrets -n cdb-trading

# View secret keys (not values)
kubectl describe secret cdb-secrets -n cdb-trading
```

### Issue: Services Not Starting

**Solution:** Check resource availability.

```bash
# Check node resources
kubectl top nodes

# Check pod resource requests
kubectl describe pod <pod-name> -n cdb-trading | grep -A 10 "Requests:"
```

## Next Steps

### 1. Run Health Checks

```bash
# Check all deployments are ready
kubectl get deployments -n cdb-trading

# Check all pods are healthy
kubectl get pods -n cdb-trading | grep -v Running
```

### 2. Test Trading System

```bash
# Port forward WebSocket service
kubectl port-forward svc/dev-cdb-ws 8000:8000 -n cdb-trading

# Test health endpoint
curl http://localhost:8000/health
```

### 3. Monitor Metrics

Access Grafana at http://localhost:3000 and:
- Import trading system dashboards
- Set up alerts
- Monitor service health

### 4. Deploy to Production

Once dev is stable:

```bash
# PowerShell
.\k8s\deploy-k8s.ps1 -Environment prod

# Bash
./k8s/deploy-k8s.sh prod
```

## Cleanup

Remove development deployment:

```powershell
# PowerShell
.\k8s\cleanup-k8s.ps1 -Environment dev

# Bash
kubectl delete -k k8s/overlays/dev
```

Remove everything:

```bash
kubectl delete namespace cdb-trading
```

## Additional Resources

- [Main README](README.md) - Full documentation
- [SECRETS_GUIDE.md](SECRETS_GUIDE.md) - Advanced secrets management
- [flux/README.md](flux/README.md) - GitOps setup

## Success Checklist

- [x] All images built and pushed
- [x] Secrets created
- [x] All pods running
- [x] Services accessible
- [x] Grafana dashboards visible
- [x] No error logs

**Congratulations!** 🎉 Claire de Binare is now running on Kubernetes!