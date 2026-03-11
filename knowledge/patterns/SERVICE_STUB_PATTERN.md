# Service Stub Pattern

**Extracted from**: Working Repo AUTONOMOUS_WORK_COMPLETE_2025-12-24.md
**Purpose**: Template for creating minimal service stubs

## Pattern Overview

When creating a new service stub before full implementation:

### 1. Minimal Service Structure

```python
# services/service_name/service.py
from flask import Flask, jsonify
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "service_name"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### 2. Dockerfile Template

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 serviceuser
WORKDIR /app

# Copy and install requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY service.py /app/

# Switch to non-root user
USER serviceuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run service
CMD ["python", "service.py"]
```

### 3. Requirements Template

```txt
Flask==3.0.0
redis==5.0.1
psycopg2-binary==2.9.9
pydantic==2.5.2
```

### 4. Compose Service Definition

```yaml
  service_name:
    build:
      context: ../..
      dockerfile: services/service_name/Dockerfile
    container_name: cdb_service_name
    restart: unless-stopped
    env_file:
      - ../../.env
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      cdb_redis:
        condition: service_healthy
      cdb_postgres:
        condition: service_healthy
    networks:
      - cdb_network
```

## When to Use

- Creating placeholder service for future implementation
- Testing Docker Compose orchestration
- Validating port allocation
- Prototyping service dependencies

## Migration from Stub to Full Service

1. Implement core business logic in `service.py`
2. Add `models.py` with data classes
3. Add `config.py` with environment variables
4. Implement Redis pub/sub connections
5. Add database queries
6. Add comprehensive error handling
7. Write unit tests
8. Write integration tests
9. Update README.md with API documentation

---

**Last Updated**: 2025-12-27
**Source**: Migration from Working Repo (Issue #143)
