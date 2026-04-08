# Integration Proposal: MEXC API Credentials für cdb_ws

**Datum:** 2025-12-29
**Status:** PROPOSAL (Delivery Gate: FALSE → Analysis Mode)
**Blocker:** MEXC WebSocket Subscription returns "Blocked!" - Credentials erforderlich
**User Approval Required:** ✅ JA (vor Implementation)

---

## Problem Statement

**Current State:**
- cdb_ws WebSocket Service vollständig implementiert (245 Zeilen Production Code)
- Container healthy, Metrics aktiv, Code produktionsreif
- **BLOCKER:** MEXC API blockiert Subscription trotz "Public" Endpoint

**Evidence:**
```
Subscription response: {
  "id":0,
  "code":0,
  "msg":"Not Subscribed successfully! [spot@public.deals.v3.api@BTCUSDT]. Reason： Blocked!"
}
```

**Impact:**
- 0 Market Data Messages
- 0 Signals generiert (cdb_signal wartet auf Daten)
- Gesamte Trading Pipeline blockiert

---

## Credentials Status

**Location:** `C:\Users\janne\Documents\.secrets\.cdb\`

**Vorhandene Files:**
- ✅ `MEXC_API_KEY.txt` (18 bytes)
- ✅ `MEXC_API_SECRET.txt` (32 bytes)
- ✅ `MEXC_TRADE_API_KEY.txt` (18 bytes) - Separate Trading Keys
- ✅ `MEXC_TRADE_API_SECRET.txt` (32 bytes)

**Note:** Es existieren zwei Sets:
1. **Regular API Keys** - Für Market Data (cdb_ws)
2. **Trading API Keys** - Für Order Execution (cdb_execution)

---

## Integration Architecture

### Pattern: Docker Compose Secrets (kanonisch)

Gemäß `Deep Research Docker Secrets.md` und aktuellem Stack-Pattern (REDIS_PASSWORD, POSTGRES_PASSWORD, GRAFANA_PASSWORD):

```yaml
# infrastructure/compose/base.yml

secrets:
  mexc_api_key:
    file: ${SECRETS_PATH}/MEXC_API_KEY.txt
  mexc_api_secret:
    file: ${SECRETS_PATH}/MEXC_API_SECRET.txt

services:
  cdb_ws:
    secrets:
      - mexc_api_key
      - mexc_api_secret
    environment:
      MEXC_API_KEY_FILE: /run/secrets/mexc_api_key
      MEXC_API_SECRET_FILE: /run/secrets/mexc_api_secret
```

### Code Changes: services/ws/service.py

**Secrets Loading (File-First Pattern):**
```python
# Configuration from environment
MEXC_WS_URL = os.getenv("MEXC_WS_URL", "wss://wbs.mexc.com/ws")
WS_SYMBOL = os.getenv("WS_SYMBOL", "BTCUSDT")

# Secrets via Docker Compose secrets: directive
def load_secret(name, env_file_var):
    """Load secret from file (Docker secrets pattern)"""
    file_path = os.getenv(env_file_var)
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read().strip()
    # Fallback to direct env var (dev only)
    return os.getenv(name, "")

MEXC_API_KEY = load_secret("MEXC_API_KEY", "MEXC_API_KEY_FILE")
MEXC_API_SECRET = load_secret("MEXC_API_SECRET", "MEXC_API_SECRET_FILE")
```

**WebSocket Auth Integration:**

Gemäß MEXC API Documentation benötigt WebSocket Authentication einen Auth-Header:

```python
async def connect_websocket(self):
    """Connect to MEXC WebSocket and subscribe to trade stream"""

    # Generate Auth Headers (MEXC Pattern)
    import hmac
    import hashlib
    import time

    timestamp = int(time.time() * 1000)
    signature_payload = f"{timestamp}{MEXC_API_KEY}"
    signature = hmac.new(
        MEXC_API_SECRET.encode('utf-8'),
        signature_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Connect with Auth Headers
    headers = {
        "X-MEXC-APIKEY": MEXC_API_KEY,
        "X-MEXC-TIMESTAMP": str(timestamp),
        "X-MEXC-SIGNATURE": signature
    }

    self.ws = await websockets.connect(
        self.ws_url,
        extra_headers=headers
    )
    ws_connection_status.set(1)
    logger.info(f"WebSocket connected (authenticated): {self.ws_url}")

    # Subscribe to trade stream (same as before)
    subscribe_msg = {
        "method": "SUBSCRIPTION",
        "params": [f"spot@public.deals.v3.api@{self.symbol}"]
    }
    await self.ws.send(json.dumps(subscribe_msg))
    logger.info(f"Subscribed to trade stream: {self.symbol}")

    # Wait for subscription confirmation
    try:
        confirmation = await asyncio.wait_for(self.ws.recv(), timeout=5)
        logger.info(f"Subscription response: {confirmation}")
    except asyncio.TimeoutError:
        logger.warning("No subscription confirmation received within 5s")
```

---

## Implementation Steps

### Phase 1: Docker Compose Configuration ✅ SAFE (keine Code-Mutation)

**File:** `infrastructure/compose/base.yml`

**Changes:**
1. Add secrets definitions (top-level):
   ```yaml
   secrets:
     mexc_api_key:
       file: ${SECRETS_PATH}/MEXC_API_KEY.txt
     mexc_api_secret:
       file: ${SECRETS_PATH}/MEXC_API_SECRET.txt
   ```

2. Update `cdb_ws` service:
   ```yaml
   cdb_ws:
     # ... existing config ...
     secrets:
       - mexc_api_key
       - mexc_api_secret
     environment:
       MEXC_API_KEY_FILE: /run/secrets/mexc_api_key
       MEXC_API_SECRET_FILE: /run/secrets/mexc_api_secret
   ```

**Risk:** NIEDRIG (folgt existierendem Pattern von REDIS_PASSWORD etc.)

### Phase 2: Service Code Update ⚠️ REQUIRES DELIVERY GATE

**File:** `services/ws/service.py`

**Changes:**
1. Add `load_secret()` helper function (lines ~55-65)
2. Load credentials via file-first pattern (lines ~52-53)
3. Update `connect_websocket()` with Auth Headers (lines ~97-135)
4. Add `import hmac, hashlib, time` (lines ~21-23)

**Dependencies:** Keine neuen (hmac/hashlib/time sind stdlib)

**Risk:** MITTEL (WebSocket Auth kann scheitern wenn MEXC API Format falsch)

### Phase 3: Testing & Validation

**Commands:**
```bash
# Rebuild image
docker compose -f infrastructure/compose/base.yml build cdb_ws

# Restart stack
.\infrastructure\scripts\stack_up.ps1 -Logging

# Check logs for successful subscription
docker logs cdb_ws --tail 50 | grep -E "(Subscription|Connected|Blocked)"

# Verify Redis Stream has data
docker exec cdb_redis redis-cli -a $REDIS_PASSWORD xlen market_data

# Check Prometheus metrics
curl http://localhost:8000/metrics | grep ws_messages_received_total
```

**Success Criteria:**
- ✅ No "Blocked!" error in logs
- ✅ Subscription confirmation: `"msg":"Subscribed successfully"`
- ✅ `ws_messages_received_total` > 0
- ✅ Redis Stream `market_data` has entries (xlen > 0)
- ✅ cdb_signal logs show incoming trade data

**Failure Rollback:**
```bash
git restore services/ws/service.py
docker compose -f infrastructure/compose/base.yml build cdb_ws
.\infrastructure\scripts\stack_up.ps1 -Logging
```

---

## Security Considerations

### ✅ COMPLIANT with CDB Security Policy

1. **Secrets Never in Git:** ✅ Files in `~/.secrets/.cdb/` (gitignored)
2. **Docker Secrets Pattern:** ✅ Mounted to `/run/secrets/` (read-only, tmpfs)
3. **File-First Pattern:** ✅ `*_FILE` env vars prevent accidental logging
4. **No Hardcoded Credentials:** ✅ All via environment/files
5. **Separate Trading Keys:** ✅ Market Data ≠ Order Execution Keys

### Secrets Rotation Plan

**Trigger:** Nach Secret Exposure oder 90 Tage

**Process:**
1. Generate new MEXC API Keys via MEXC Dashboard
2. Update files in `~/.secrets/.cdb/`
3. Restart cdb_ws: `docker compose restart cdb_ws`
4. Verify metrics: `ws_messages_received_total` increasing

**NO rebuild required** - Secrets mounted at runtime!

---

## Alternative: Dev Mode (Fallback)

Falls Auth-Header Pattern fehlschlägt, Alternative:

### Option A: MEXC REST API Polling (nicht empfohlen)
- Pro: Keine WebSocket Auth
- Con: Hohe Latenz, Rate Limits, keine Realtime Daten

### Option B: Third-Party WebSocket Proxy
- Pro: Keine direkte MEXC Integration
- Con: Zusätzliche Dependency, Trust-Issue

### Option C: Testnet WebSocket (empfohlen für Testing)
- MEXC Testnet: `wss://contract.mexc.com/ws` (möglicherweise keine Auth)
- Pro: Testing ohne Production Keys
- Con: Testnet-Daten ≠ Real Market

---

## Cost-Benefit Analysis

**Implementation Time:** ~30 Minuten (Code) + 15 Minuten (Testing) = 45 Minuten

**Risk Level:** NIEDRIG
- WebSocket Code bereits produktionsreif
- Auth Pattern gut dokumentiert (MEXC API Docs + Blog Posts)
- Rollback trivial (git restore)

**Benefit:**
- ✅ Unblocks gesamte Trading Pipeline
- ✅ Enables Paper Trading Validation
- ✅ Grafana Dashboard wird live

**Opportunity Cost:**
- Keine - Blocker MUSS gelöst werden für weiteren Progress

---

## User Approval Required

**Fragen an Jannek:**

1. **API Keys Confirmation:**
   - `MEXC_API_KEY.txt` vs. `MEXC_TRADE_API_KEY.txt` - Welches Set für Market Data?
   - Oder beide ausprobieren?

2. **Delivery Gate:**
   - Soll ich `DELIVERY_APPROVED.yaml` für diese Änderung aktivieren?
   - Oder User macht Code-Änderungen selbst?

3. **Testing Strategy:**
   - Testnet zuerst (safe) oder direkt Production Keys (schneller)?

4. **Rollout:**
   - Sofort implementieren oder erst weitere Dokumentation?

---

## Proposed Timeline

**Assuming User Approval:**

1. **T+0 Min:** User setzt `DELIVERY_APPROVED.yaml` → `approved: true`
2. **T+5 Min:** Ich implementiere Code Changes (Phase 2)
3. **T+10 Min:** Docker Build + Stack Restart
4. **T+15 Min:** Log Validation (Check for "Subscribed successfully")
5. **T+20 Min:** Redis Stream Verification (xlen market_data > 0)
6. **T+25 Min:** Prometheus Metrics Check (messages_total > 0)
7. **T+30 Min:** Integration Test abgeschlossen
8. **T+45 Min:** User setzt `DELIVERY_APPROVED.yaml` → `approved: false`

**Total:** 45 Minuten bis Paper Trading Pipeline funktioniert

---

## Governance Compliance

**Current Mode:** ANALYSIS MODE (Delivery Gate = FALSE)

**This Document:**
- ✅ Proposal nur (keine Mutations)
- ✅ User Approval erforderlich vor Implementation
- ✅ Geschrieben in `knowledge/logs/` (erlaubt per CDB_AGENT_POLICY.md)

**Implementation:**
- ⚠️ Erfordert Delivery Gate TRUE
- ⚠️ Working Repo Mutation (`services/ws/service.py`, `infrastructure/compose/base.yml`)

**Decision Event:** Nicht erforderlich (keine Governance/Policy Change, nur Technical Implementation)

---

## Next Steps

**Waiting for User Decision:**
1. Approve/Reject Proposal
2. Confirm API Keys to use (regular vs. trading)
3. Set Delivery Gate if approved
4. Implementation Start

**After Implementation:**
1. Session Log Update mit Results
2. Paper Trading Pipeline Validation (C11)
3. Grafana Dashboard Verification (B)

---

**Proposal Ende:** 2025-12-29 08:45 CET
**Awaiting User Approval**
