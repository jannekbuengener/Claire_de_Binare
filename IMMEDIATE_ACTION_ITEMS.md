# Claire de Binaire – Sofortmaßnahmen (Next 72 Hours)

**Datum**: 2025-11-21
**Priorität**: KRITISCH – Blockiert Production Release
**Ziel**: Klare Handlungsanweisungen für Engineering-Team

---

## Situation

Umfassende Architektur-Analyse identifiziert **3 kritische Blocker**, die vor Production-Release aufgelöst werden müssen:

| ID | Issue | Impact | Status |
|----|-------|--------|--------|
| **K1** | TODO in risk_engine.py | Production Logic unvollständig | 🔴 OPEN |
| **K2** | Docker Build-Path Mismatch | Services starten nicht | 🔴 OPEN |
| **K3** | Security Jobs nicht blockierend | Sicherheits-Findings ignorierbar | 🔴 OPEN |

---

## K1: Resolve TODO in risk_engine.py

### Problem
```python
# Datei: services/risk_engine.py, Zeile 430-431
# TODO: Replace placeholder risk logic with production-grade rules and
# connectivity to portfolio and order management services.
```

**Impact**: Blockiert Production Deployment (M8).

### Solution (4 Hours)

#### Step 1.1: Analyze Current Implementation (30 min)

Review was bereits vorhanden:
```bash
# Check existing code
grep -n "evaluate_signal_v2" services/risk_engine.py
grep -n "validate_liquidation_distance" services/mexc_perpetuals.py
grep -n "calculate_funding_fee" services/mexc_perpetuals.py
```

**Finding**: Alle notwendigen Helper-Funktionen existieren bereits!

#### Step 1.2: Document Production Requirements (30 min)

Basierend auf KODEX und Architektur:

```python
# Production-Grade Requirements für evaluate_signal_v2():
# 1. Liquidation Distance Validation
#    → Minimum 15% distance zu liquidation price (configurable)
#    → Reject if: liq_distance < MIN_LIQUIDATION_DISTANCE
#
# 2. Funding Fee Impact
#    → Daily funding fee < 0.1% of position value
#    → Alert if > 0.05%
#    → Reject if > 0.1%
#
# 3. Slippage-Volatility Coupling
#    → High volatility (>50%) → reduce position size OR reject
#    → Already handled in ExecutionSimulator
#
# 4. Market Regime Detection
#    → Normal: Execute normal rules
#    → Stressed: Reduce exposure by 50%
#    → Panic: Stop all new orders
```

#### Step 1.3: Implement Production Logic (2 hours)

**File**: `services/risk_engine.py` (nach Line 385)

```python
# ============================================================================
# PRODUCTION-GRADE RISK VALIDATION
# ============================================================================

def validate_liquidation_safety(
    position: MexcPerpetualPosition,
    min_distance: float = 0.15
) -> Dict[str, any]:
    """Production-grade liquidation validation.

    Args:
        position: MEXC position object
        min_distance: Minimum safe distance (default 15%)

    Returns:
        {"approved": bool, "reason": str, "distance": float}
    """
    from services.mexc_perpetuals import validate_liquidation_distance

    result = validate_liquidation_distance(position, min_distance)
    return {
        "approved": result["approved"],
        "reason": result.get("reason"),
        "distance": result.get("distance")
    }


def check_funding_fee_impact(
    position: MexcPerpetualPosition,
    market_conditions: Dict
) -> Dict[str, any]:
    """Check if funding fees are sustainable.

    Args:
        position: MEXC position
        market_conditions: Market data including funding_rate

    Returns:
        {"approved": bool, "daily_cost": float, "alert": bool}
    """
    funding_rate = float(market_conditions.get("funding_rate", 0.0001))

    # Calculate 24h funding fee
    daily_fee = position.calculate_funding_fee(funding_rate, hours=24.0)
    max_daily_fee_pct = float(os.getenv("MAX_DAILY_FUNDING_FEE_PCT", "0.001"))
    max_acceptable = position.position_value * max_daily_fee_pct

    alert_threshold = max_acceptable * 0.5  # Alert at 50% of max

    return {
        "approved": daily_fee <= max_acceptable,
        "daily_cost": daily_fee,
        "alert": daily_fee > alert_threshold,
        "reason": "excessive_funding_fees" if daily_fee > max_acceptable else None
    }


def detect_market_regimen(market_conditions: Dict) -> str:
    """Detect current market regimen for risk adjustment.

    Args:
        market_conditions: Market data including volatility

    Returns:
        "normal" | "stressed" | "panic"
    """
    volatility = float(market_conditions.get("volatility", 0.30))

    if volatility > 1.0:  # >100% annualized
        return "panic"
    elif volatility > 0.60:  # >60% annualized
        return "stressed"
    else:
        return "normal"


def apply_market_regimen_adjustment(
    position_size: float,
    regimen: str
) -> float:
    """Adjust position size based on market regimen.

    Args:
        position_size: Base position size
        regimen: "normal" | "stressed" | "panic"

    Returns:
        Adjusted position size
    """
    multipliers = {
        "normal": 1.0,
        "stressed": 0.5,
        "panic": 0.0  # No new positions in panic
    }
    return position_size * multipliers.get(regimen, 1.0)
```

#### Step 1.4: Integrate into evaluate_signal_v2() (1 hour)

Modify `evaluate_signal_v2()` to call new validators:

```python
def evaluate_signal_v2(
    signal_event: Dict,
    risk_state: Dict,
    risk_config: Dict,
    market_conditions: Dict,
) -> EnhancedRiskDecision:
    """Enhanced signal evaluation with PRODUCTION-GRADE validation."""

    # ... [existing basic checks] ...

    # NEW: Market Regimen Detection
    regimen = detect_market_regimen(market_conditions)
    logger.info(f"Market regimen: {regimen}")

    # ... [existing perpetuals checks] ...

    # NEW: Liquidation Safety Validation
    liq_safety = validate_liquidation_safety(position, min_distance=0.15)
    if not liq_safety["approved"]:
        return EnhancedRiskDecision(
            approved=False,
            reason=liq_safety["reason"],
            position_size=0.0,
            stop_price=None,
        )

    # NEW: Funding Fee Impact Check
    funding_check = check_funding_fee_impact(position, market_conditions)
    if not funding_check["approved"]:
        return EnhancedRiskDecision(
            approved=False,
            reason=funding_check["reason"],
            position_size=0.0,
            stop_price=None,
        )

    if funding_check["alert"]:
        logger.warning(f"High funding fees: {funding_check['daily_cost']:.2f}")

    # NEW: Market Regimen Adjustment
    adjusted_size = apply_market_regimen_adjustment(position_size, regimen)
    if adjusted_size < position_size:
        logger.info(f"Position size adjusted: {position_size} → {adjusted_size} ({regimen})")
        position_size = adjusted_size

    # ... [rest of existing logic] ...
```

#### Step 1.5: Add Tests (1 hour)

**File**: `tests/test_risk_engine_core.py`

```python
@pytest.mark.unit
def test_production_liquidation_safety():
    """Production-grade liquidation validation."""
    from services.risk_engine import validate_liquidation_safety

    # Mock position with 10% liquidation distance (should fail min 15%)
    position_mock = {
        "liquidation_distance": 0.10,
    }

    result = validate_liquidation_safety(position_mock, min_distance=0.15)
    assert result["approved"] is False


@pytest.mark.unit
def test_production_funding_fee_check():
    """Funding fee sustainability check."""
    from services.risk_engine import check_funding_fee_impact

    position_mock = {"position_value": 100_000}
    market_conditions = {"funding_rate": 0.0005}  # 0.05% per 8h

    result = check_funding_fee_impact(position_mock, market_conditions)
    assert "daily_cost" in result
    assert "alert" in result


@pytest.mark.unit
def test_market_regimen_detection():
    """Market condition classification."""
    from services.risk_engine import detect_market_regimen

    assert detect_market_regimen({"volatility": 0.30}) == "normal"
    assert detect_market_regimen({"volatility": 0.65}) == "stressed"
    assert detect_market_regimen({"volatility": 1.5}) == "panic"
```

#### Step 1.6: Remove TODO (5 min)

```bash
# Replace the TODO comment:
# sed -i '430,431d' services/risk_engine.py

# Or manually delete lines 430-431 in editor
```

### Verification

```bash
# 1. Check file is clean
grep -n "TODO" services/risk_engine.py
# Result: (no output = success)

# 2. Run tests
pytest tests/test_risk_engine_core.py -v

# 3. Check code style
black services/risk_engine.py
ruff check services/risk_engine.py --fix
```

### Acceptance Criteria
- [ ] TODO removed from code
- [ ] All new validators have tests
- [ ] Tests pass
- [ ] Code formatted (black/ruff)
- [ ] Type hints present

**Timeline**: 4 hours

---

## K2: Fix Docker Build Paths

### Problem

```yaml
# docker-compose.yml lines 165-200
cdb_core:
  build:
    context: ./backoffice/services/signal_engine  # ← Does not exist!
    dockerfile: Dockerfile
  # ...

# Same for cdb_risk, cdb_execution
```

**Impact**: Services fail to build and start.

### Solution (3 Hours)

#### Option A: Simplest (Move docker-compose context) – 30 min

```bash
# Current structure:
services/
  ├── risk_engine.py
  ├── position_sizing.py
  └── ...

# Update docker-compose.yml:
cdb_core:
  build:
    context: .
    dockerfile: backoffice/services/cdb_core/Dockerfile
```

**Pros**: Simple, minimal changes
**Cons**: Services must have wrapper code in backoffice/

#### Option B: Recommended (Hybrid structure) – 2.5 hours

```bash
# Create service directories
mkdir -p backoffice/services/cdb_core/{app,etc}
mkdir -p backoffice/services/cdb_risk/{app,etc}
mkdir -p backoffice/services/cdb_execution/{app,etc}

# Step 1: Create wrapper main.py files

# File: backoffice/services/cdb_core/app/main.py
from flask import Flask, jsonify
from services.risk_engine import load_risk_config

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "cdb_core"})

@app.route("/status")
def status():
    config = load_risk_config()
    return jsonify({
        "service": "cdb_core",
        "config_loaded": True,
        "max_position_pct": config.get("MAX_POSITION_PCT")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=False)


# File: backoffice/services/cdb_risk/app/main.py
# Similar structure for Risk Manager


# Step 2: Create requirements.txt for each service

# File: backoffice/services/cdb_core/requirements.txt
Flask==2.3.2
python-dotenv==1.0.0
-e ../../  # Reference shared services


# Step 3: Create Dockerfile for each service

# File: backoffice/services/cdb_core/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy service code
COPY app/ /app/
COPY ../../services /app/services

# Health check
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8001/health')"

# Run service
CMD ["python", "-u", "main.py"]


# Step 4: Update docker-compose.yml

# Before:
cdb_core:
  build:
    context: ./backoffice/services/signal_engine
    dockerfile: Dockerfile

# After:
cdb_core:
  build:
    context: .
    dockerfile: backoffice/services/cdb_core/Dockerfile
  environment:
    PYTHONPATH: /app:/app/services


# Step 5: Verify structure
find backoffice/services -type f -name "*.py" -o -name "Dockerfile" -o -name "requirements.txt"
```

**Pros**: Clean separation, scalable
**Cons**: More file creation

#### Implementation Steps (Hybrid – Recommended)

```bash
# 1. Create directories
mkdir -p backoffice/services/{cdb_core,cdb_risk,cdb_execution}/{app,etc}

# 2. Create main.py files (copy template)
for service in cdb_core cdb_risk cdb_execution; do
  cat > backoffice/services/$service/app/main.py << 'EOF'
from flask import Flask, jsonify
from services.risk_engine import load_risk_config

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "SERVICE_NAME"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
EOF
done

# 3. Create requirements.txt
for service in cdb_core cdb_risk cdb_execution; do
  cat > backoffice/services/$service/requirements.txt << 'EOF'
Flask==2.3.2
python-dotenv==1.0.0
psycopg2-binary==2.9.9
redis==5.0.0
EOF
done

# 4. Create Dockerfiles
for service in cdb_core cdb_risk cdb_execution; do
  cat > backoffice/services/$service/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ /app/
COPY ../../services /app/services
ENV PYTHONPATH=/app:/app/services
CMD ["python", "-u", "main.py"]
EOF
done

# 5. Test build
docker build -f backoffice/services/cdb_core/Dockerfile .
```

### Verification

```bash
# 1. Verify directory structure
tree backoffice/services/cdb_*

# 2. Test docker build
docker build -t test-cdb-core \
  -f backoffice/services/cdb_core/Dockerfile .

# 3. Test docker-compose
docker compose build
docker compose up -d --wait
docker compose ps

# 4. Test health endpoint
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Acceptance Criteria
- [ ] All service directories created
- [ ] Dockerfile builds successfully for each service
- [ ] docker-compose up succeeds
- [ ] Health endpoints respond
- [ ] Services ready to receive requests

**Timeline**: 3 hours

---

## K3: Make Security Jobs Blocking

### Problem

```yaml
# .github/workflows/ci.yaml

security-audit:
  # ...
  continue-on-error: true  # ← Security findings are IGNORED

dependency-audit:
  # ...
  continue-on-error: true  # ← Vulnerable deps are IGNORED
```

**Impact**: Security vulnerabilities can be merged.

### Solution (30 Minutes)

#### Step 1: Edit .github/workflows/ci.yaml

**Lines to modify**: 164, 192

```yaml
# BEFORE (Line 164):
security-audit:
  name: Security Audit (Bandit)
  runs-on: ubuntu-latest
  steps:
    # ...
    - name: Run Bandit
      run: bandit -r services/ -f json -o bandit-report.json
      continue-on-error: true  # ← REMOVE THIS LINE

# AFTER:
security-audit:
  name: Security Audit (Bandit)
  runs-on: ubuntu-latest
  steps:
    # ...
    - name: Run Bandit
      run: bandit -r services/ -f json -o bandit-report.json
      # (no continue-on-error)

# BEFORE (Line 192):
dependency-audit:
  name: Dependency Audit (pip-audit)
  runs-on: ubuntu-latest
  steps:
    # ...
    - name: Run pip-audit
      run: |
        pip-audit --requirement requirements.txt --format json --output pip-audit.json
      continue-on-error: true  # ← REMOVE THIS LINE

# AFTER:
dependency-audit:
  name: Dependency Audit (pip-audit)
  runs-on: ubuntu-latest
  steps:
    # ...
    - name: Run pip-audit
      run: |
        pip-audit --requirement requirements.txt --format json --output pip-audit.json
      # (no continue-on-error)
```

#### Step 2: Verify Changes

```bash
# Check file
grep -A5 "security-audit:" .github/workflows/ci.yaml
grep -A5 "dependency-audit:" .github/workflows/ci.yaml

# Should NOT contain "continue-on-error: true"
```

#### Step 3: Test Locally (Optional)

```bash
# Install tools
pip install bandit pip-audit

# Run security checks
bandit -r services/ -f json -o /tmp/bandit.json
pip-audit --requirement requirements.txt --format json

# Check for findings (should be 0)
echo "Bandit findings:"
jq '.results | length' /tmp/bandit.json
```

### Acceptance Criteria
- [ ] Both "continue-on-error" lines removed
- [ ] Code syntax valid (no YAML errors)
- [ ] Next PR run shows security jobs as blocking
- [ ] Test run verifies no current findings

**Timeline**: 30 minutes

---

## Next Steps After K1/K2/K3

Once all three are complete:

1. **Commit & PR**:
   ```bash
   git checkout -b fix/critical-blockers-k1-k2-k3
   git add -A
   git commit -m "fix: resolve K1, K2, K3 critical blockers

   - K1: Implement production-grade risk validators
   - K2: Fix docker build paths for services
   - K3: Make security jobs blocking in CI

   Closes #ISSUE_ID"

   git push origin fix/critical-blockers-k1-k2-k3
   ```

2. **PR Review Checklist**:
   - [ ] K1: TODO resolved, tests pass
   - [ ] K2: Services build and start
   - [ ] K3: Security jobs blocking
   - [ ] All tests pass
   - [ ] Code formatted (black/ruff)

3. **Verification After Merge**:
   ```bash
   # Pull latest main
   git pull origin main

   # Test full build
   docker compose build
   docker compose up -d --wait
   docker compose ps

   # Test services
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health

   # Run E2E tests
   pytest -v -m e2e
   ```

4. **Production Readiness Checklist**:
   - [ ] K1/K2/K3 resolved
   - [ ] All E2E tests passing
   - [ ] Services healthy
   - [ ] CI pipeline green
   - [ ] Security scan clean
   - [ ] Ready for M8 Production Release

---

## Communication Template

**For Engineering Team Lead:**

```markdown
## Critical Issues Found – 72-Hour Action Plan

We've completed a comprehensive architecture analysis of Claire de Binaire.
Three critical blockers were identified that must be fixed before Production:

### K1: TODO in Production Code (4h)
- Implement production-grade risk validators
- Tests: liquidation safety, funding fees, market regimen
- File: services/risk_engine.py

### K2: Docker Build Path Mismatch (3h)
- Fix service build contexts
- Create wrapper services in backoffice/
- Verify with docker-compose

### K3: Security Jobs Not Blocking (0.5h)
- Remove continue-on-error from security/audit jobs
- CI will now fail on security findings

### Total Effort: ~8 hours
### Timeline: 3 business days
### Owner: [Assign to Tech Lead]
### Blocker for: M8 Production Release

Full analysis available in: ARCHITECTURAL_CODE_ANALYSIS_REPORT.md
Action items detail in: IMMEDIATE_ACTION_ITEMS.md
```

---

**Report Generated**: 2025-11-21
**Status**: Ready to Implement
**Next Review**: After K1/K2/K3 completion
