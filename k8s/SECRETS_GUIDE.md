# Secrets Management Guide

## Overview

This guide explains how to securely manage secrets for the Claire de Binare Kubernetes deployment.

## ⚠️ NEVER Commit Secrets to Git

The `k8s/base/secret-template.yaml` is a **template only**. Never commit actual secrets to version control.

## Methods

### Method 1: Manual Secret Creation (Development)

For development and testing, create secrets manually:

```bash
# Generate strong passwords
REDIS_PASSWORD=$(openssl rand -base64 24)
POSTGRES_PASSWORD=$(openssl rand -base64 24)
GRAFANA_PASSWORD=$(openssl rand -base64 24)

# Create secret
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-literal=redis_password="$REDIS_PASSWORD" \
  --from-literal=postgres_password="$POSTGRES_PASSWORD" \
  --from-literal=grafana_password="$GRAFANA_PASSWORD" \
  --from-literal=mexc_api_key="your-mexc-testnet-api-key" \
  --from-literal=mexc_api_secret="your-mexc-testnet-api-secret" \
  --from-literal=mexc_trade_api_key="your-mexc-trade-key" \
  --from-literal=mexc_trade_api_secret="your-mexc-trade-secret"
```

### Method 2: From Files

If you have secret files:

```bash
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-file=redis_password=/path/to/redis_password \
  --from-file=postgres_password=/path/to/postgres_password \
  --from-file=grafana_password=/path/to/grafana_password \
  --from-file=mexc_api_key=/path/to/mexc_api_key.txt \
  --from-file=mexc_api_secret=/path/to/mexc_api_secret.txt
```

### Method 3: Sealed Secrets (Recommended for GitOps)

[Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) allows you to encrypt secrets that can be safely committed to git.

#### Setup

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
# Linux
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar xfz kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# macOS
brew install kubeseal

# Windows
# Download from releases page and add to PATH
```

#### Create Sealed Secret

```bash
# Create a regular secret (don't commit this!)
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-literal=redis_password="$REDIS_PASSWORD" \
  --from-literal=postgres_password="$POSTGRES_PASSWORD" \
  --dry-run=client -o yaml > secret.yaml

# Seal it
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml

# Now you can safely commit sealed-secret.yaml to git
git add sealed-secret.yaml
git commit -m "Add sealed secrets"

# Delete the plain secret file
rm secret.yaml
```

#### Deploy Sealed Secret

```bash
# Apply the sealed secret
kubectl apply -f sealed-secret.yaml

# The controller will automatically decrypt it into a regular secret
kubectl get secret -n cdb-trading cdb-secrets
```

### Method 4: External Secrets Operator (Recommended for Production)

[External Secrets Operator](https://external-secrets.io/) syncs secrets from external secret management systems.

Supports:
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- HashiCorp Vault
- And many more...

#### Setup with AWS Secrets Manager

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

Create `SecretStore`:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets
  namespace: cdb-trading
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

Create `ExternalSecret`:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: cdb-secrets
  namespace: cdb-trading
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: cdb-secrets
    creationPolicy: Owner
  data:
  - secretKey: redis_password
    remoteRef:
      key: cdb/redis_password
  - secretKey: postgres_password
    remoteRef:
      key: cdb/postgres_password
  - secretKey: grafana_password
    remoteRef:
      key: cdb/grafana_password
  - secretKey: mexc_api_key
    remoteRef:
      key: cdb/mexc_api_key
  - secretKey: mexc_api_secret
    remoteRef:
      key: cdb/mexc_api_secret
```

## Secret Rotation

### Manual Rotation

```bash
# Update secret
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-literal=redis_password="new-password" \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new secret
kubectl rollout restart -n cdb-trading deployment/cdb-redis
kubectl rollout restart -n cdb-trading deployment/cdb-ws
# ... restart other deployments as needed
```

### Automated Rotation with External Secrets

External Secrets Operator can automatically refresh secrets:

```yaml
spec:
  refreshInterval: 1h  # Refresh every hour
```

Pods will need to be restarted to pick up new values, or use tools like [Reloader](https://github.com/stakater/Reloader).

## Viewing Secrets

```bash
# List secrets
kubectl get secrets -n cdb-trading

# View secret (base64 encoded)
kubectl get secret -n cdb-trading cdb-secrets -o yaml

# Decode a specific key
kubectl get secret -n cdb-trading cdb-secrets -o jsonpath='{.data.redis_password}' | base64 -d
```

## Security Best Practices

1. **Never commit plaintext secrets** to version control
2. **Use RBAC** to restrict access to secrets
3. **Enable encryption at rest** in etcd
4. **Use separate secrets** for different environments
5. **Rotate secrets regularly** (quarterly minimum)
6. **Audit secret access** using Kubernetes audit logs
7. **Use least privilege** - only grant access to secrets needed
8. **Monitor for secret leaks** in logs and metrics

## Backup and Recovery

### Backup Secrets

```bash
# Export secrets (encrypted)
kubectl get secret -n cdb-trading cdb-secrets -o yaml > cdb-secrets-backup.yaml

# Store securely (encrypted storage, access controlled)
```

### Restore Secrets

```bash
# Restore from backup
kubectl apply -f cdb-secrets-backup.yaml
```

## Troubleshooting

### Secret Not Found

```bash
# Check if secret exists
kubectl get secret -n cdb-trading cdb-secrets

# Check secret contents
kubectl describe secret -n cdb-trading cdb-secrets
```

### Pod Cannot Access Secret

```bash
# Check pod events
kubectl describe pod -n cdb-trading <pod-name>

# Check if secret is mounted
kubectl exec -n cdb-trading <pod-name> -- ls -la /run/secrets/

# Check secret permissions
kubectl exec -n cdb-trading <pod-name> -- cat /run/secrets/redis_password
```

### Sealed Secret Won't Decrypt

```bash
# Check SealedSecret status
kubectl describe sealedsecret -n cdb-trading cdb-secrets

# Check controller logs
kubectl logs -n kube-system -l name=sealed-secrets-controller
```

## References

- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [External Secrets Operator](https://external-secrets.io/)
- [Secret Management Best Practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
