# Secrets Management Guide

Comprehensive guide for managing secrets in Kubernetes for the Claire de Binare trading system.

## Overview

Secrets contain sensitive data like:
- Database passwords
- API keys
- Exchange credentials
- TLS certificates

**NEVER commit secrets to Git!**

## Method 1: Manual Secret Creation

### For Development (Quick & Simple)

```bash
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-literal=redis_password="dev-redis-pass" \
  --from-literal=postgres_password="dev-pg-pass" \
  --from-literal=postgres_admin_password="dev-admin-pass" \
  --from-literal=api_key="dev-api-key" \
  --from-literal=api_secret="dev-api-secret" \
  --from-literal=exchange_api_key="dev-exchange-key" \
  --from-literal=exchange_api_secret="dev-exchange-secret"
```

### From Files

```bash
# Create individual secret files
echo -n "my-redis-password" > redis_password.txt
echo -n "my-postgres-password" > postgres_password.txt
echo -n "my-api-key" > api_key.txt
echo -n "my-api-secret" > api_secret.txt

# Create secret from files
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-file=redis_password=redis_password.txt \
  --from-file=postgres_password=postgres_password.txt \
  --from-file=api_key=api_key.txt \
  --from-file=api_secret=api_secret.txt

# Clean up files
rm -f *.txt
```

### From .env File

```bash
# Create .env file (DO NOT COMMIT)
cat > secrets.env <<EOF
redis_password=your-redis-password
postgres_password=your-postgres-password
postgres_admin_password=your-admin-password
api_key=your-api-key
api_secret=your-api-secret
exchange_api_key=your-exchange-key
exchange_api_secret=your-exchange-secret
EOF

# Create secret
kubectl create secret generic cdb-secrets \
  --namespace=cdb-trading \
  --from-env-file=secrets.env

# Securely delete
shred -u secrets.env  # Linux
# or
rm secrets.env  # Mac/Windows
```

## Method 2: Sealed Secrets (GitOps-Friendly)

**Best for:** GitOps workflows where you want to version control encrypted secrets.

### Installation

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
# Mac
brew install kubeseal

# Linux
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar xfz kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

### Usage

```bash
# Create regular secret file (DO NOT COMMIT)
cat > secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: cdb-secrets
  namespace: cdb-trading
type: Opaque
stringData:
  redis_password: "your-redis-password"
  postgres_password: "your-postgres-password"
  api_key: "your-api-key"
  api_secret: "your-api-secret"
EOF

# Seal the secret (encrypted)
kubeseal -f secret.yaml -w sealed-secret.yaml

# sealed-secret.yaml is safe to commit to Git!
git add sealed-secret.yaml
git commit -m "Add sealed secrets"

# Apply sealed secret
kubectl apply -f sealed-secret.yaml

# Controller automatically creates the decrypted secret
kubectl get secret cdb-secrets -n cdb-trading
```

### Benefits
- ✅ Secrets encrypted at rest in Git
- ✅ Safe to commit to version control
- ✅ GitOps-friendly
- ✅ Automatic decryption in cluster

## Method 3: External Secrets Operator (Cloud)

**Best for:** Production with cloud secret managers (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault)

### Installation

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

### AWS Secrets Manager Example

```yaml
# Create SecretStore
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
---
# Create ExternalSecret
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
  - secretKey: api_key
    remoteRef:
      key: cdb/api_key
  - secretKey: api_secret
    remoteRef:
      key: cdb/api_secret
```

### Azure Key Vault Example

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: azure-secrets
  namespace: cdb-trading
spec:
  provider:
    azurekv:
      authType: ManagedIdentity
      vaultUrl: "https://your-vault.vault.azure.net"
```

### Benefits
- ✅ Centralized secret management
- ✅ Automatic rotation
- ✅ Audit logging
- ✅ Access control via cloud IAM

## Method 4: HashiCorp Vault

**Best for:** Enterprise environments with existing Vault infrastructure

### Installation

```bash
# Install Vault via Helm
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --namespace=vault \
  --create-namespace
```

### Configuration

```yaml
# Enable Kubernetes auth in Vault
vault auth enable kubernetes

vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443"

# Create policy
vault policy write cdb-secrets - <<EOF
path "secret/data/cdb/*" {
  capabilities = ["read"]
}
EOF

# Create role
vault write auth/kubernetes/role/cdb-secrets \
  bound_service_account_names=cdb-secrets \
  bound_service_account_namespaces=cdb-trading \
  policies=cdb-secrets \
  ttl=24h
```

### Usage in Pods

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cdb-ws
spec:
  serviceAccountName: cdb-secrets
  containers:
  - name: ws
    image: your-registry/cdb-ws:latest
    env:
    - name: VAULT_ADDR
      value: "http://vault:8200"
    volumeMounts:
    - name: vault-token
      mountPath: /vault/secrets
  volumes:
  - name: vault-token
    emptyDir:
      medium: Memory
  initContainers:
  - name: vault-init
    image: vault:latest
    command:
    - sh
    - -c
    - |
      vault kv get -field=redis_password secret/cdb/redis > /vault/secrets/redis_password
```

## Comparison Matrix

| Method | Complexity | Security | GitOps | Cost | Best For |
|--------|-----------|----------|--------|------|----------|
| Manual | Low | Medium | ❌ | Free | Development |
| Sealed Secrets | Medium | High | ✅ | Free | GitOps |
| External Secrets | Medium | High | ✅ | Cloud costs | Cloud production |
| Vault | High | Very High | ✅ | Infrastructure | Enterprise |

## Security Best Practices

### 1. Never Commit Plain Secrets

```bash
# Add to .gitignore
echo "secrets.env" >> .gitignore
echo "*.secret.yaml" >> .gitignore
echo "**/secret-*.yaml" >> .gitignore
```

### 2. Use RBAC

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
  namespace: cdb-trading
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: secret-reader-binding
  namespace: cdb-trading
subjects:
- kind: ServiceAccount
  name: cdb-service-account
roleRef:
  kind: Role
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### 3. Enable Encryption at Rest

```yaml
# EncryptionConfiguration for kube-apiserver
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-32-byte-key>
    - identity: {}
```

### 4. Rotate Secrets Regularly

```bash
# Example rotation script
kubectl create secret generic cdb-secrets-new \
  --namespace=cdb-trading \
  --from-literal=redis_password="new-password" \
  --dry-run=client -o yaml | kubectl apply -f -

# Update deployments to use new secret
kubectl patch deployment cdb-ws -n cdb-trading \
  -p '{"spec":{"template":{"metadata":{"annotations":{"secret-rotation":"'$(date +%s)'"}}}}}'
```

### 5. Audit Secret Access

```bash
# Enable audit logging in kube-apiserver
--audit-log-path=/var/log/kubernetes/audit.log
--audit-policy-file=/etc/kubernetes/audit-policy.yaml
```

## Troubleshooting

### Check if Secret Exists

```bash
kubectl get secret cdb-secrets -n cdb-trading
```

### View Secret Keys (not values)

```bash
kubectl describe secret cdb-secrets -n cdb-trading
```

### Decode Secret Value (for debugging)

```bash
kubectl get secret cdb-secrets -n cdb-trading -o jsonpath='{.data.redis_password}' | base64 --decode
```

### Check Secret is Mounted in Pod

```bash
kubectl exec -it <pod-name> -n cdb-trading -- ls -la /secrets/
```

## Recommended Approach by Environment

### Development
- **Method:** Manual creation
- **Rotation:** Manual as needed
- **Storage:** Local only

### Staging
- **Method:** Sealed Secrets
- **Rotation:** Quarterly
- **Storage:** Git (encrypted)

### Production
- **Method:** External Secrets Operator + Cloud KMS
- **Rotation:** Monthly (automated)
- **Storage:** Cloud Secret Manager

## Additional Resources

- [Kubernetes Secrets Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Sealed Secrets GitHub](https://github.com/bitnami-labs/sealed-secrets)
- [External Secrets Operator](https://external-secrets.io/)
- [HashiCorp Vault](https://www.vaultproject.io/)
