# Docker Secrets Management: A Complete Blueprint for Windows 11 + WSL2

**Build-time and runtime secrets require fundamentally different security controls.** This guide provides battle-tested patterns for Docker Desktop developers who need production-grade secret handling without enterprise infrastructure complexity. The core principle: secrets should exist only where needed, only when needed, and never persist in artifacts.

---

## Executive summary

- **Never use `ARG` or `ENV` for secrets** — they persist in image layers, `docker history`, and `docker inspect`, making extraction trivial for anyone with image access
- **BuildKit's `--mount=type=secret` is mandatory** for build-time secrets — secrets exist only during the RUN command, never touch the filesystem, and leave no trace in the final image
- **Docker Compose `secrets:` directive** mounts secrets to `/run/secrets/` as files, keeping them out of environment variable listings and `docker inspect` output
- **The `_FILE` environment variable pattern** (e.g., `POSTGRES_PASSWORD_FILE`) is supported by official images and should be implemented in all custom applications
- **SOPS + age is the recommended encryption approach** for solo Windows operators — zero infrastructure, simple key management, and Git-native secret versioning
- **Pre-commit hooks with Gitleaks** catch secrets before they enter Git history, which is critical because removing secrets from history is painful and often incomplete
- **File-first with environment fallback** should be the universal pattern for reading secrets in application code
- **Secret rotation playbooks must exist before you need them** — the time to figure out rotation procedures is not during an active incident
- **GitHub Actions must use the `secrets:` input**, never `build-args:`, and secrets must be explicitly masked when derived or transformed

---

## Recommended architecture

The architecture separates concerns across three distinct phases, each with different threat models and controls.

### Build-time layer (Dockerfile + BuildKit)

```
┌──────────────────────────────────────────────────────────────┐
│                    BUILD-TIME SECRETS                        │
├──────────────────────────────────────────────────────────────┤
│  Secret Source        │  Docker Command                      │
│  ──────────────────── │ ──────────────────────────────────── │
│  Local file           │  --secret id=npm,src=~/.npmrc        │
│  Environment var      │  --secret id=token,env=API_TOKEN     │
│  SSH agent            │  --ssh default                       │
├──────────────────────────────────────────────────────────────┤
│  Dockerfile Pattern                                          │
│  ────────────────────────────────────────────────────────── │
│  RUN --mount=type=secret,id=npm,target=/root/.npmrc \        │
│      npm ci && rm -rf /root/.npm                             │
├──────────────────────────────────────────────────────────────┤
│  Result: Secret exists ONLY during RUN, never in layers      │
└──────────────────────────────────────────────────────────────┘
```

### Runtime layer (Docker Compose)

```
┌──────────────────────────────────────────────────────────────┐
│                    RUNTIME SECRETS                           │
├──────────────────────────────────────────────────────────────┤
│  Host                    │  Container                        │
│  ──────────────────────  │  ──────────────────────────────── │
│  .secrets/db_pass.txt    →  /run/secrets/db_password        │
│  .secrets/api_key.txt    →  /run/secrets/api_key            │
├──────────────────────────────────────────────────────────────┤
│  docker-compose.yml                                          │
│  ─────────────────────────────────────────────────────────── │
│  secrets:                                                    │
│    db_password:                                              │
│      file: ./.secrets/db_password.txt                        │
├──────────────────────────────────────────────────────────────┤
│  Result: Secrets not in env vars, not in docker inspect      │
└──────────────────────────────────────────────────────────────┘
```

### Directory structure contract

```
project-root/
├── .secrets/                    # GITIGNORED - actual secrets
│   ├── db_password.txt
│   ├── api_key.txt
│   └── jwt_secret.txt
├── .secrets.example/            # COMMITTED - placeholder templates
│   ├── db_password.txt          # Contains: change-me-password
│   └── api_key.txt              # Contains: your-api-key-here
├── secrets.sops.yaml            # COMMITTED - encrypted secrets (optional)
├── .sops.yaml                   # COMMITTED - SOPS configuration
├── .gitignore
├── .dockerignore
├── .gitleaks.toml
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Dockerfile
└── scripts/
    ├── init-secrets.sh          # Initialize .secrets/ from examples
    └── rotate-secret.sh         # Secret rotation helper
```

---

## Decision matrix

### Build-time secret method comparison

| Method | Persists in Image | Visible in History | Cache Safe | Recommendation |
|--------|-------------------|-------------------|------------|----------------|
| `ARG` + `--build-arg` | ✅ Yes | ✅ Fully exposed | ❌ No | **Never use** |
| `ENV` instruction | ✅ Yes | ✅ Fully exposed | ❌ No | **Never use** |
| `COPY` then delete | ✅ In earlier layers | ✅ Extractable | ❌ No | **Never use** |
| `--mount=type=secret` | ❌ No | ❌ No trace | ✅ Yes | **Always use** |
| `--mount=type=ssh` | ❌ No | ❌ No trace | ✅ Yes | **Use for Git** |

### Secret storage approach comparison

| Approach | Setup Complexity | Ongoing Maintenance | Solo Developer Fit | Security | Recommendation |
|----------|------------------|---------------------|-------------------|----------|----------------|
| Plain .env + .gitignore | Low | Low | Good | ⚠️ Easily leaked | Dev only |
| SOPS + age | Medium | Low | **Excellent** | ✅ High | **Recommended** |
| HashiCorp Vault | High | High | Poor | ✅ Highest | Enterprise |
| Cloud KMS (AWS/GCP/Azure) | Medium-High | Medium | Fair | ✅ Very High | Cloud-native |

### Secret scanning tool comparison

| Feature | Gitleaks | TruffleHog | GitHub Secret Scanning |
|---------|----------|------------|------------------------|
| Secret patterns | 160+ | 800+ | 200+ partners |
| Live verification | ❌ | ✅ API check | ✅ Partner validation |
| Pre-commit native | ✅ | Via wrapper | ❌ |
| Best for | Pre-commit, CI | Deep audits | GitHub-native |
| False positive rate | Medium | Low (verified) | Low |

---

## Implementation blueprint

### A) Build-time secrets (Dockerfile patterns)

**Pattern 1: Private NPM package authentication**

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./

# Secret mounted only during npm install, never persisted
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --production && \
    rm -rf /root/.npm

COPY . .
RUN npm run build

# Final image has no secrets
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER node
CMD ["node", "dist/index.js"]
```

**Build command:**
```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t myapp .
```

**Pattern 2: Private Git repository cloning**

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git openssh-client
RUN mkdir -p -m 0700 ~/.ssh && \
    ssh-keyscan github.com >> ~/.ssh/known_hosts

WORKDIR /app

# SSH agent forwarded for git clone only
RUN --mount=type=ssh \
    git clone git@github.com:myorg/private-lib.git ./lib

COPY . .
RUN CGO_ENABLED=0 go build -o /myapp

FROM gcr.io/distroless/static
COPY --from=builder /myapp /myapp
ENTRYPOINT ["/myapp"]
```

**Build command:**
```bash
eval $(ssh-agent) && ssh-add ~/.ssh/id_ed25519
docker build --ssh default -t myapp .
```

**Pattern 3: API key for licensed downloads**

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu:22.04 AS downloader
RUN apt-get update && apt-get install -y curl ca-certificates
WORKDIR /assets

# Secret available as environment variable during this RUN only
RUN --mount=type=secret,id=api_key,env=ASSET_API_KEY \
    curl -H "Authorization: Bearer ${ASSET_API_KEY}" \
         -o models.tar.gz \
         https://api.example.com/licensed/models/v2.tar.gz && \
    tar -xzf models.tar.gz && rm models.tar.gz

FROM python:3.11-slim
WORKDIR /app
COPY --from=downloader /assets/models /app/models
COPY . .
CMD ["python", "app.py"]
```

**Build command:**
```bash
export ASSET_API_KEY="your-key-here"
docker build --secret id=api_key,env=ASSET_API_KEY -t myapp .
```

**Pattern 4: Multiple secrets in one build**

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .

RUN --mount=type=secret,id=pip_conf,target=/root/.pip/pip.conf \
    --mount=type=secret,id=netrc,target=/root/.netrc \
    pip install --no-cache-dir -r requirements.txt

COPY . .

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app .
USER nobody
CMD ["python", "main.py"]
```

**Build command:**
```bash
docker build \
    --secret id=pip_conf,src=~/.pip/pip.conf \
    --secret id=netrc,src=~/.netrc \
    -t myapp .
```

### B) Runtime secrets (Docker Compose)

**Complete docker-compose.yml with secrets:**

```yaml
services:
  # PostgreSQL with _FILE convention
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER_FILE: /run/secrets/postgres_user
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_DB: myapp
    secrets:
      - postgres_user
      - postgres_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$(cat /run/secrets/postgres_user)"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Application with file-first secret reading
  backend:
    build: ./backend
    environment:
      DATABASE_HOST: postgres
      DATABASE_PORT: 5432
      DATABASE_NAME: myapp
      # Point to secret files (app reads from files)
      DATABASE_USER_FILE: /run/secrets/postgres_user
      DATABASE_PASSWORD_FILE: /run/secrets/postgres_password
      JWT_SECRET_FILE: /run/secrets/jwt_secret
    secrets:
      - postgres_user
      - postgres_password
      - jwt_secret
    depends_on:
      postgres:
        condition: service_healthy

  # Redis with secret in command
  redis:
    image: redis:7-alpine
    command: >
      sh -c "redis-server --requirepass $$(cat /run/secrets/redis_password)"
    secrets:
      - redis_password

secrets:
  postgres_user:
    file: ./.secrets/postgres_user.txt
  postgres_password:
    file: ./.secrets/postgres_password.txt
  jwt_secret:
    file: ./.secrets/jwt_secret.txt
  redis_password:
    file: ./.secrets/redis_password.txt

volumes:
  postgres_data:
```

**File-first secret reader (Python):**

```python
import os
from pathlib import Path

class SecretError(Exception):
    pass

def get_secret(key: str, secrets_dir: str = "/run/secrets") -> str:
    """Read secret with file-first, environment fallback pattern."""
    file_env_key = f"{key}_FILE"
    
    # Priority 1: _FILE environment variable pointing to file
    if file_env_key in os.environ:
        secret_path = Path(os.environ[file_env_key])
        if secret_path.is_dir():
            raise SecretError(
                f"{file_env_key} points to directory, not file. "
                f"This usually means the source file was missing on the host."
            )
        if secret_path.is_file():
            return secret_path.read_text(encoding='utf-8').strip()
    
    # Priority 2: Default secrets directory
    default_path = Path(secrets_dir) / key.lower()
    if default_path.is_file():
        return default_path.read_text(encoding='utf-8').strip()
    
    # Priority 3: Direct environment variable
    if key in os.environ:
        return os.environ[key]
    
    raise SecretError(f"Secret '{key}' not found in files or environment")

# Usage
db_password = get_secret('DATABASE_PASSWORD')
jwt_secret = get_secret('JWT_SECRET')
```

**File-first secret reader (Node.js):**

```javascript
const fs = require('fs');
const path = require('path');

function getSecret(key, secretsDir = '/run/secrets') {
    const fileEnvKey = `${key}_FILE`;
    
    // Priority 1: _FILE env var
    if (process.env[fileEnvKey]) {
        const secretPath = process.env[fileEnvKey];
        const stats = fs.statSync(secretPath, { throwIfNoEntry: false });
        
        if (stats?.isDirectory()) {
            throw new Error(
                `${fileEnvKey} points to directory '${secretPath}', not a file. ` +
                `Create the source file on the host and restart.`
            );
        }
        if (stats?.isFile()) {
            return fs.readFileSync(secretPath, 'utf8').trim();
        }
    }
    
    // Priority 2: Default secrets directory
    const defaultPath = path.join(secretsDir, key.toLowerCase());
    if (fs.existsSync(defaultPath) && fs.statSync(defaultPath).isFile()) {
        return fs.readFileSync(defaultPath, 'utf8').trim();
    }
    
    // Priority 3: Direct env var
    if (process.env[key]) {
        return process.env[key];
    }
    
    throw new Error(`Secret '${key}' not found`);
}

module.exports = { getSecret };
```

**Secret initialization script:**

```bash
#!/bin/bash
# scripts/init-secrets.sh
set -euo pipefail

SECRETS_DIR=".secrets"
EXAMPLES_DIR=".secrets.example"

echo "🔐 Initializing Docker secrets..."

mkdir -p "$SECRETS_DIR"

if [ ! -d "$EXAMPLES_DIR" ]; then
    echo "❌ Error: $EXAMPLES_DIR directory not found"
    exit 1
fi

for example_file in "$EXAMPLES_DIR"/*; do
    if [ -f "$example_file" ]; then
        filename=$(basename "$example_file")
        target="$SECRETS_DIR/$filename"
        
        if [ ! -f "$target" ]; then
            cp "$example_file" "$target"
            echo "📝 Created $target"
        else
            echo "✓ $target exists, skipping"
        fi
    fi
done

chmod 600 "$SECRETS_DIR"/* 2>/dev/null || true
chmod 700 "$SECRETS_DIR" 2>/dev/null || true

echo "✅ Secrets initialized. Update values in $SECRETS_DIR/"
```

### C) CI/CD secrets (GitHub Actions)

**Complete secure workflow:**

```yaml
name: Secure Docker Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # ✅ CORRECT: Using secrets input (NOT build-args)
          secrets: |
            "npm_token=${{ secrets.NPM_TOKEN }}"
            "github_token=${{ secrets.GITHUB_TOKEN }}"
          # Cache is safe - secrets not included in cache keys
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**What NOT to do:**

```yaml
# ❌ NEVER DO THIS - Secrets exposed in image history
- name: Build (INSECURE)
  uses: docker/build-push-action@v6
  with:
    build-args: |
      NPM_TOKEN=${{ secrets.NPM_TOKEN }}  # EXPOSED!
```

### D) Encrypted secrets in Git (SOPS + age)

**One-time setup in WSL2:**

```bash
# Install age
AGE_VERSION=$(curl -s "https://api.github.com/repos/FiloSottile/age/releases/latest" | grep -Po '"tag_name": "v\K[^"]+')
curl -Lo age.tar.gz "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
tar xf age.tar.gz && sudo mv age/age age/age-keygen /usr/local/bin/ && rm -rf age*

# Install SOPS
SOPS_VERSION=$(curl -s "https://api.github.com/repos/getsops/sops/releases/latest" | grep -Po '"tag_name": "v\K[^"]+')
curl -Lo sops "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"
sudo install -m 555 sops /usr/local/bin/sops && rm sops

# Generate key pair
mkdir -p ~/.sops && age-keygen -o ~/.sops/key.txt && chmod 600 ~/.sops/key.txt

# Configure shell
echo 'export SOPS_AGE_KEY_FILE=$HOME/.sops/key.txt' >> ~/.bashrc
source ~/.bashrc

# Get your public key (needed for .sops.yaml)
grep "public key:" ~/.sops/key.txt
```

**Repository .sops.yaml configuration:**

```yaml
# .sops.yaml
creation_rules:
  - path_regex: \.sops\.(yaml|yml|json|env)$
    age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p  # Your public key
    encrypted_regex: ^(data|stringData|password|secret|token|key|api_key|.*_KEY|.*_SECRET)$
```

**Daily workflow:**

```bash
# Create encrypted secrets file
cat > secrets.yaml << EOF
database:
  password: supersecret123
api_key: sk-live-abc123
EOF
sops --encrypt secrets.yaml > secrets.sops.yaml
rm secrets.yaml  # Delete plaintext

# Edit encrypted file (decrypts in editor, re-encrypts on save)
sops secrets.sops.yaml

# Decrypt for Docker Compose
sops -d secrets.sops.yaml | yq '.database.password' > .secrets/db_password.txt
docker compose up -d

# View decrypted content
sops -d secrets.sops.yaml
```

### E) Anti-drift and governance

**Complete .gitignore:**

```gitignore
# Secrets - NEVER COMMIT
.secrets/
secrets/
.env
.env.*
!.env.example
!.env.sample

# Credential files
*.pem
*.key
*.p12
*.pfx
id_rsa*
*.ppk

# Cloud credentials
.aws/
.azure/
credentials
*service-account*.json

# Decrypted SOPS files
*.decrypted.*

# Password/token files
*password*
*secret*
*token*
!*.example
```

**Complete .dockerignore:**

```dockerignore
# Secrets
.secrets/
secrets/
.env
.env.*
*.pem
*.key
credentials

# Git
.git
.gitignore
.github

# Development
Dockerfile*
docker-compose*.yml
*.md
docs/
test/
tests/
node_modules/
__pycache__/
```

**Pre-commit configuration (.pre-commit-config.yaml):**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
        args: ['--maxkb=500']

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.1
    hooks:
      - id: gitleaks
```

**Installation:**

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Initial scan
```

---

## "Never again" contract

```markdown
# Secret Management Contract
## Project: _________________ Date: _________________

### Before First Commit
- [ ] .gitignore with secret patterns added
- [ ] .dockerignore with secret patterns added  
- [ ] pre-commit hooks installed with gitleaks
- [ ] .secrets.example/ created with placeholder values
- [ ] Required secrets documented in README

### During Development
- [ ] Never hardcode secrets in source files
- [ ] Use --mount=type=secret for build-time secrets
- [ ] Use Docker Compose secrets: directive for runtime
- [ ] Implement file-first pattern in all applications
- [ ] Review git diff before every commit

### In CI/CD
- [ ] Use secrets: input, NEVER build-args:
- [ ] Gitleaks runs in pipeline
- [ ] Secrets stored in GitHub/GitLab secret managers

### Code Review Checklist
- [ ] No secrets in PR diff
- [ ] .gitignore updated for new secret patterns
- [ ] Secret scanning passed in CI

### Team Acknowledgment
Developer: _________________ Date: _____
Reviewer:  _________________ Date: _____
```

---

## Leak response playbook

### Immediate response (first 15 minutes)

```
┌─────────────────────────────────────────────────────────┐
│              SECRET LEAK DETECTED                        │
├─────────────────────────────────────────────────────────┤
│ 1. STOP   → Don't panic, don't rotate blindly           │
│ 2. ASSESS → What secret? What does it access?           │
│ 3. SCOPE  → How long exposed? Where visible?            │
│ 4. NOTIFY → Alert security team immediately             │
│ 5. ROTATE → Execute rotation with coordination          │
│ 6. VERIFY → Confirm old secret is revoked               │
│ 7. CLEAN  → Remove from git history if public           │
│ 8. REVIEW → Post-incident documentation                 │
└─────────────────────────────────────────────────────────┘
```

### Rotation by secret type

**AWS Access Keys:**
```bash
# Create new key
aws iam create-access-key --user-name <username>
# Update all services
# Test connectivity
# Disable old key (don't delete yet)
aws iam update-access-key --access-key-id <old-key> --status Inactive
# After 48 hours, delete
aws iam delete-access-key --access-key-id <old-key>
```

**Database Passwords:**
```sql
-- Generate new password, then:
ALTER USER 'appuser'@'%' IDENTIFIED BY 'new_password';
-- Update Docker secrets, restart services
-- Monitor for failed auth attempts
```

**GitHub/GitLab Tokens:**
```bash
# Generate new token in UI
# Update all usages
git remote set-url origin https://<new-token>@github.com/org/repo.git
# Revoke old token in UI
# Check audit logs for unauthorized usage
```

### Git history cleanup (if exposed publicly)

```bash
# Install BFG Repo-Cleaner
# Create secrets.txt with patterns to remove
echo "supersecretpassword" >> secrets.txt

# Run BFG
bfg --replace-text secrets.txt

# Force push (coordinate with team!)
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force --all
```

### Post-incident checklist

```markdown
- [ ] Secret rotated and old secret revoked
- [ ] All services tested with new secret
- [ ] Git history cleaned (if public exposure)
- [ ] Audit logs reviewed for unauthorized access
- [ ] Root cause identified (how did it leak?)
- [ ] Prevention measures implemented
- [ ] Team notified of new secret
- [ ] Documentation updated
```

---

## Windows 11 + WSL2 + Docker Desktop specifics

**Docker Desktop 23.0+** uses BuildKit by default — no configuration needed. Secret mounts work identically to Linux. Store `.secrets/` within WSL2 filesystem (not `/mnt/c/`) for proper file permissions.

**SSH agent forwarding** requires running the agent in WSL2:
```bash
eval $(ssh-agent)
ssh-add ~/.ssh/id_ed25519
docker build --ssh default .
```

**Known limitation:** BuildKit secret mounts using tmpfs do **not work with native Windows containers**. This guide applies to Linux containers running on Docker Desktop with WSL2 backend.

---

## Key sources

- Docker BuildKit Secrets: docs.docker.com/build/building/secrets/
- Docker Compose Secrets: docs.docker.com/compose/how-tos/use-secrets/
- GitHub Actions Secrets: docs.github.com/actions/security-guides/using-secrets-in-github-actions
- docker/build-push-action: github.com/docker/build-push-action
- SOPS: github.com/getsops/sops
- age: github.com/FiloSottile/age
- Gitleaks: github.com/gitleaks/gitleaks
- TruffleHog: github.com/trufflesecurity/trufflehog