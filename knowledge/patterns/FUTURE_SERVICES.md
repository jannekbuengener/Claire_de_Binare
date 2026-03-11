# Future Services Integration Pattern

**Extracted from**: Working Repo root FUTURE_SERVICES.md (Dec 2025)
**Purpose**: Template for integrating new services into the stack

## Service Integration Checklist

### 1. Service Implementation
- [ ] Create `service.py` with Flask health endpoint
- [ ] Implement core service logic
- [ ] Add Redis pub/sub connections
- [ ] Create `models.py` with Pydantic dataclasses
- [ ] Create `config.py` with env var loading

### 2. Containerization
- [ ] Create `Dockerfile` with non-root user
- [ ] Add health check in Dockerfile
- [ ] Pin base image with SHA256
- [ ] Create `requirements.txt`

### 3. Compose Integration
- [ ] Add service to `dev.yml`
- [ ] Configure environment variables
- [ ] Set up dependencies (depends_on)
- [ ] Add health check in compose
- [ ] Bind ports to localhost only (127.0.0.1:PORT:PORT)

### 4. Database Integration
- [ ] Create schema in `infrastructure/database/schema.sql`
- [ ] Add seed data if needed
- [ ] Test database connection

### 5. Testing
- [ ] Add unit tests (`tests/unit/service_name/`)
- [ ] Add integration tests
- [ ] Add E2E test cases
- [ ] Verify test markers (`@pytest.mark.unit`, etc.)

### 6. Documentation
- [ ] Create service README.md
- [ ] Document API endpoints
- [ ] Add troubleshooting section
- [ ] Update DOCKER_STACK_RUNBOOK.md

### 7. Deployment
- [ ] Verify service starts without errors
- [ ] Check health endpoint responds
- [ ] Verify Redis connections
- [ ] Test pub/sub message flow
- [ ] Monitor logs for errors

## Port Allocation

**Reserved Ports** (localhost-only binding):
- 8001: Core Service
- 8002: Risk Service
- 8003: Execution Service
- 8004: Paper Runner
- 8005: Market Service (planned)
- 8006: Allocation Service (planned)
- 8007: Regime Service (planned)
- 8000: WebSocket Service

## Service Status Matrix

| Service | service.py | Dockerfile | Compose | Status |
|---------|-----------|-----------|---------|--------|
| core | ✅ | ✅ | ✅ | Running |
| risk | ✅ | ✅ | ✅ | Running |
| execution | ✅ | ✅ | ✅ | Running |
| signal | ✅ | ✅ | ✅ | Running |
| db_writer | ✅ | ✅ | ✅ | Running |
| ws | ✅ | ✅ | ✅ | Running |
| market | ✅ | ✅ | ❌ | Disabled (config pending) |
| allocation | ✅ | ✅ | ❌ | Disabled (config pending) |
| regime | ✅ | ✅ | ❌ | Disabled (config pending) |

---

**Last Updated**: 2025-12-27
**Source**: Migration from Working Repo (Issue #143)
