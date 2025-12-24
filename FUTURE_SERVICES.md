# Future Services - Integration Roadmap

## Overview

This document tracks services that have Dockerfiles or implementation code but are not yet integrated into the canonical Docker stack.

**Purpose**: Prevent confusion about orphaned Dockerfiles and provide clear integration path.

**Status**: Documentation phase (Criterion G - Confusion-proofing)

---

## Current Stack Status

### ✅ Active Services (in `infrastructure/compose/dev.yml`)

**Infrastructure** (in `infrastructure/compose/base.yml`):
- `cdb_redis` - Message bus and cache
- `cdb_postgres` - Primary database
- `cdb_prometheus` - Metrics collection
- `cdb_grafana` - Visualization and dashboards

**Logging** (in `infrastructure/compose/logging.yml`):
- `cdb_loki` - Log aggregation server
- `cdb_promtail` - Log collector

**Application Services** (in `infrastructure/compose/dev.yml`):
- `cdb_ws` - WebSocket service (root `Dockerfile`)
- `cdb_core` - Core signal processing (`services/signal/Dockerfile`)
- `cdb_risk` - Risk management (`services/risk/Dockerfile`)
- `cdb_execution` - Order execution (`services/execution/Dockerfile`)
- `cdb_db_writer` - Database writer (`services/db_writer/Dockerfile`)

---

## Orphaned Dockerfiles

### 1. `services/allocation/Dockerfile`

**Status**: 🔜 Not integrated

**Purpose**: Position allocation and portfolio management

**Current State**:
- Dockerfile exists
- Service code presumably exists in `services/allocation/`
- Not defined in any compose file
- Not mentioned in `stack_up.ps1` target services

**Integration Requirements**:
1. Add service definition to `infrastructure/compose/dev.yml`
2. Configure port binding (127.0.0.1:XXXX:8000)
3. Add to `stack_up.ps1` target services list
4. Create healthcheck
5. Document in COMPOSE_LAYERS.md

**Suggested Compose Config**:
```yaml
  cdb_allocation:
    build:
      context: ../..
      dockerfile: services/allocation/Dockerfile
    container_name: cdb_allocation
    restart: unless-stopped
    env_file: .env
    ports:
      - "127.0.0.1:8005:8005"  # Dockerfile EXPOSE 8005
    volumes:
      - ../../logs:/app/logs
    depends_on:
      - cdb_redis
      - cdb_postgres
    networks:
      - cdb_network
```

**Note**: Dockerfile includes non-root user (allocuser) and built-in HEALTHCHECK ✅

---

### 2. `services/market/Dockerfile`

**Status**: 🔜 Not integrated

**Purpose**: Market data ingestion and processing

**Current State**:
- Dockerfile exists
- Service code presumably exists in `services/market/`
- Not defined in any compose file
- Not mentioned in `stack_up.ps1` target services

**Integration Requirements**:
1. Add service definition to `infrastructure/compose/dev.yml`
2. Configure port binding (127.0.0.1:XXXX:8000)
3. Add to `stack_up.ps1` target services list
4. Create healthcheck
5. Verify dependencies (likely Redis + Postgres)

**Suggested Compose Config**:
```yaml
  cdb_market:
    build:
      context: ../..
      dockerfile: services/market/Dockerfile
    container_name: cdb_market
    restart: unless-stopped
    env_file: .env
    ports:
      - "127.0.0.1:8004:8004"  # Dockerfile EXPOSE 8004
    volumes:
      - ../../logs:/app/logs
    depends_on:
      - cdb_redis
      - cdb_postgres
    networks:
      - cdb_network
```

**Note**: Dockerfile includes non-root user (marketuser) and built-in HEALTHCHECK ✅

---

### 3. `services/regime/Dockerfile`

**Status**: 🔜 Not integrated

**Purpose**: Market regime detection and classification

**Current State**:
- Dockerfile exists
- Service code presumably exists in `services/regime/`
- Not defined in any compose file
- Not mentioned in `stack_up.ps1` target services

**Integration Requirements**:
1. Add service definition to `infrastructure/compose/dev.yml`
2. Configure port binding (127.0.0.1:XXXX:8000)
3. Add to `stack_up.ps1` target services list
4. Create healthcheck
5. Verify dependencies

**Suggested Compose Config**:
```yaml
  cdb_regime:
    build:
      context: ../..
      dockerfile: services/regime/Dockerfile
    container_name: cdb_regime
    restart: unless-stopped
    env_file: .env
    ports:
      - "127.0.0.1:8006:8006"  # Dockerfile EXPOSE 8006 (fixed from 8004 conflict)
    volumes:
      - ../../logs:/app/logs
    depends_on:
      - cdb_redis
      - cdb_postgres
    networks:
      - cdb_network
```

**Note**: Dockerfile includes non-root user (regimeuser) and built-in HEALTHCHECK ✅

---

## Planned Services (Mentioned but Not Defined)

### 4. `cdb_paper_runner`

**Status**: 🔜 Planned → ✅ Dockerfile Found in Legacy

**Purpose**: Paper trading simulation runner

**Current State**:
- Mentioned in `stack_up.ps1` target services list
- Mentioned in `COMPOSE_LAYERS.md` documentation
- Placeholder in `infrastructure/compose/rollback.yml`
- Implementation exists: `services/execution/paper_trading.py`
- **✅ LEGACY DOCKERFILE DISCOVERED**: `Dockerfile_cdb_paper_runner` in quarantine
- Not defined in any active compose file

**Legacy Dockerfile Details**:
- Port: 8004 (matches our allocation!)
- Main file: `service.py`
- Features: Email alerting (`email_alerter.py`)
- Log structure: `/app/logs` + `/app/logs/events`
- See `LEGACY_ANALYSIS.md` for full details

**Integration Decision Required**:
- **Option A**: Dedicated service with own container
  - Pros: Isolated, independent scaling
  - Cons: Resource overhead, more complex
- **Option B**: Run within `cdb_execution` container
  - Pros: Simpler, shared code
  - Cons: Coupled lifecycle
- **Option C**: Scheduled task / cron job
  - Pros: No persistent container
  - Cons: No real-time monitoring

**Suggested Compose Config** (Option A - Using Legacy Dockerfile):
```yaml
  cdb_paper_runner:
    build:
      context: ../..
      dockerfile: services/paper_runner/Dockerfile  # Copy from legacy Dockerfile_cdb_paper_runner
    container_name: cdb_paper_runner
    restart: unless-stopped
    env_file: .env
    ports:
      - "127.0.0.1:8004:8004"  # Legacy Dockerfile uses 8004
    volumes:
      - ../../logs:/app/logs
    depends_on:
      - cdb_redis
      - cdb_postgres
    networks:
      - cdb_network
```

**Note**: Before integration, copy `Dockerfile_cdb_paper_runner` from quarantine to `services/paper_runner/Dockerfile`

---

## Integration Roadmap

### Phase 1: Documentation (Current)
- ✅ Document all orphaned Dockerfiles
- ✅ Identify integration requirements
- ✅ Propose compose configurations

### Phase 2: Core Services (Next)
**Priority**: High

1. **cdb_market** - Market data is foundational
   - Add to compose stack
   - Test integration with Redis/Postgres
   - Verify logging via Loki

2. **cdb_allocation** - Position management critical
   - Add to compose stack
   - Test interaction with execution service
   - Verify risk integration

3. **cdb_regime** - Market classification needed
   - Add to compose stack
   - Test signal integration
   - Verify data flow from market service

### Phase 3: Paper Trading (Future)
**Priority**: Medium

1. **cdb_paper_runner**
   - Decide on architecture (dedicated vs. embedded)
   - Implement chosen approach
   - Add to compose stack
   - Create comprehensive tests

### Phase 4: Production Hardening
**Priority**: Low (after all services integrated)

1. Create production overlay (`infrastructure/compose/prod.yml`)
2. Remove port bindings (use network isolation)
3. Add resource limits
4. Configure production logging levels
5. Set up health dependencies with `-StrictHealth`

---

## Port Allocation Plan

**Current Allocations**:
- 6379: Redis (infrastructure)
- 5432: Postgres (infrastructure)
- 19090: Prometheus (infrastructure)
- 3000: Grafana (infrastructure)
- 3100: Loki (logging)
- 8000: cdb_ws (WebSocket)
- 8001: cdb_core (signal processing)
- 8002: cdb_risk (risk management)
- 8003: cdb_execution (order execution)

**Future Allocations** (Dockerfile EXPOSE values):
- 8004: cdb_market (market data) - Dockerfile ready ✅
- 8005: cdb_allocation (position allocation) - Dockerfile ready ✅
- 8006: cdb_regime (regime detection) - Dockerfile ready ✅
- 8007: cdb_paper_runner (paper trading) - Dockerfile in quarantine

**Port Mapping Pattern**:
- Services expose their designated ports internally (8001, 8002, 8003, etc.)
- External bindings MUST use `127.0.0.1:PORT:PORT` format (localhost-only, per Criterion B)
- Example: `127.0.0.1:8004:8004` for market service

**Note**: Current dev.yml uses `XXXX:8000` mapping pattern which conflicts with Dockerfile EXPOSE directives. Services actually listen on their designated ports (8001-8007), not on 8000.

---

## Integration Checklist

When integrating a new service, follow this checklist:

### Pre-Integration
- [ ] Verify Dockerfile builds successfully
- [ ] Verify service code exists and is functional
- [ ] Identify all dependencies (Redis, Postgres, other services)
- [ ] Determine port requirements

### Compose Integration
- [ ] Add service definition to `infrastructure/compose/dev.yml`
- [ ] Configure localhost-only port binding (`127.0.0.1:XXXX:8000`)
- [ ] Add volume mounts (logs, configs)
- [ ] Configure dependencies (`depends_on`)
- [ ] Add to correct network (`cdb_network`)
- [ ] Create healthcheck (if HTTP service)

### Stack Configuration
- [ ] Add service to `stack_up.ps1` target services list
- [ ] Update `infrastructure/compose/COMPOSE_LAYERS.md`
- [ ] Add to rollback template (`infrastructure/compose/rollback.yml`)
- [ ] Update `DOCKER_STACK_RUNBOOK.md` if needed

### Testing
- [ ] Test service starts successfully
- [ ] Verify dependencies resolved
- [ ] Check logs for errors
- [ ] Verify communication with dependencies
- [ ] Test healthcheck (if configured)
- [ ] Test rollback procedure

### Documentation
- [ ] Update this file (FUTURE_SERVICES.md)
- [ ] Document service purpose in COMPOSE_LAYERS.md
- [ ] Add troubleshooting procedures to RUNBOOK if needed
- [ ] Update port allocation table

---

## Notes

- **cdb_ws Service**: Uses root `Dockerfile` (not in services/), may need cleanup
- **Dockerfile Naming**: All service Dockerfiles follow pattern `services/<name>/Dockerfile`
- **Port Pattern**: All application services expose port 8000 internally, mapped to unique external ports
- **Network Isolation**: Dev profile binds to 127.0.0.1, prod profile (future) will use internal network only

---

## Questions for Team

1. **Paper Runner Architecture**: Which option (A/B/C) for `cdb_paper_runner`?
2. **Integration Priority**: Confirm order - market → allocation → regime?
3. **cdb_ws Cleanup**: Should we move root `Dockerfile` to `services/ws/Dockerfile`?
4. **Resource Limits**: Should we add memory/CPU limits during integration or later?

---

## See Also

- `infrastructure/compose/COMPOSE_LAYERS.md` - Current architecture
- `infrastructure/compose/dev.yml` - Active service definitions
- `infrastructure/scripts/stack_up.ps1` - Stack launcher with target services
- `DOCKER_STACK_RUNBOOK.md` - Operational procedures
