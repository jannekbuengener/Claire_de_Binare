# Production Security Hardening Guide

**Security framework for Claire de Binare production trading**

## Overview

This guide covers security hardening requirements for production deployment with real money trading.

---

## Security Layers

### 1. API Key Management

#### Current State
✅ Docker secrets for infrastructure (Redis, PostgreSQL)
❌ MEXC API keys in `.env` file (development only)

#### Production Requirements

**MEXC API Keys:**
```yaml
# docker-compose.yml
secrets:
  mexc_api_key:
    file: ../.cdb_local/.secrets/mexc_api_key
  mexc_api_secret:
    file: ../.cdb_local/.secrets/mexc_api_secret
```

**Service Configuration:**
```yaml
# services/execution/service
secrets:
  - mexc_api_key
  - mexc_api_secret
environment:
  MEXC_API_KEY_FILE: /run/secrets/mexc_api_key
  MEXC_API_SECRET_FILE: /run/secrets/mexc_api_secret
```

**Code Changes:**
```python
# services/execution/config.py
import os

def _read_secret(secret_name: str, fallback_env: str) -> str:
    """Read from Docker secret or fallback to env var"""
    secret_path = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_path):
        with open(secret_path) as f:
            return f.read().strip()
    return os.getenv(fallback_env, "")

MEXC_API_KEY = _read_secret("mexc_api_key", "MEXC_API_KEY")
MEXC_API_SECRET = _read_secret("mexc_api_secret", "MEXC_API_SECRET")
```

#### API Key Rotation

**Procedure:**
1. Generate new API key on MEXC
2. Update secret files:
   ```bash
   echo "new_key" > ../.cdb_local/.secrets/mexc_api_key
   echo "new_secret" > ../.cdb_local/.secrets/mexc_api_secret
   ```
3. Rolling restart services:
   ```bash
   docker-compose up -d --no-deps --force-recreate cdb_execution
   docker-compose up -d --no-deps --force-recreate cdb_risk
   ```
4. Verify connection
5. Revoke old API key on MEXC

**Rotation Schedule:**
- Mandatory: Every 90 days
- Recommended: Every 30 days
- Emergency: Immediately if compromised

---

### 2. Rate Limiting

#### API Rate Limits (MEXC)

**Current Limits:**
- REST API: 20 requests/second
- Order placement: 100 orders/10 seconds
- WebSocket: 10 connections per IP

**Implementation:**
```python
# services/execution/rate_limiter.py
import time
from collections import deque
from threading import Lock

class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()

    def acquire(self) -> bool:
        """Attempt to acquire rate limit token"""
        with self.lock:
            now = time.time()

            # Remove old requests outside time window
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False

    def wait_and_acquire(self, timeout: float = 10.0) -> bool:
        """Wait until token available or timeout"""
        start = time.time()
        while time.time() - start < timeout:
            if self.acquire():
                return True
            time.sleep(0.1)
        return False


# Usage in MEXC client
class MexcClient:
    def __init__(self):
        # 15 req/sec (leave margin below 20/sec limit)
        self.rate_limiter = RateLimiter(max_requests=15, time_window=1.0)

    def place_order(self, *args, **kwargs):
        if not self.rate_limiter.wait_and_acquire(timeout=5.0):
            raise Exception("Rate limit exceeded")

        # Place order...
```

---

### 3. Order Validation

#### Pre-Execution Validation

```python
# services/risk/order_validator.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class OrderLimits:
    """Production order limits"""

    # Position Limits
    max_position_size_usd: float = 1000.0  # Start conservative
    max_position_pct: float = 0.10  # 10% of equity
    max_total_exposure: float = 0.30  # 30% total

    # Order Size Limits
    min_order_size_usd: float = 10.0  # MEXC MIN_NOTIONAL
    max_order_size_usd: float = 5000.0  # Per order

    # Symbol Whitelist (only tested pairs)
    allowed_symbols: list = None

    def __post_init__(self):
        if self.allowed_symbols is None:
            self.allowed_symbols = ["BTCUSDT", "ETHUSDT"]


class OrderValidator:
    """Validates orders before execution"""

    def __init__(self, limits: OrderLimits):
        self.limits = limits

    def validate_order(self, order: dict, account_balance: float) -> tuple[bool, Optional[str]]:
        """
        Validate order against limits

        Returns:
            (is_valid, error_message)
        """
        symbol = order.get("symbol")
        side = order.get("side")
        quantity = order.get("quantity", 0)
        price = order.get("price", 0)

        # Symbol whitelist
        if symbol not in self.limits.allowed_symbols:
            return False, f"Symbol {symbol} not in whitelist"

        # Calculate order value
        order_value_usd = quantity * price

        # Min/Max size
        if order_value_usd < self.limits.min_order_size_usd:
            return False, f"Order too small: ${order_value_usd:.2f} < ${self.limits.min_order_size_usd}"

        if order_value_usd > self.limits.max_order_size_usd:
            return False, f"Order too large: ${order_value_usd:.2f} > ${self.limits.max_order_size_usd}"

        # Position size vs equity
        position_pct = order_value_usd / account_balance
        if position_pct > self.limits.max_position_pct:
            return False, f"Position too large: {position_pct:.1%} > {self.limits.max_position_pct:.1%}"

        return True, None
```

#### Environment-Based Limits

```bash
# .env - Production
MAX_POSITION_SIZE_USD=1000          # Start small
MAX_ORDER_SIZE_USD=500              # Per order
ALLOWED_SYMBOLS=BTCUSDT,ETHUSDT     # Only tested pairs
MAX_DAILY_ORDERS=50                 # Circuit breaker

# .env - After validation period
MAX_POSITION_SIZE_USD=5000          # Scale up gradually
MAX_ORDER_SIZE_USD=2000
ALLOWED_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT
```

---

### 4. Circuit Breakers

#### Emergency Stop Mechanisms

```python
# services/risk/circuit_breaker.py
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Trading halted
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    # Failure thresholds
    max_consecutive_failures: int = 3
    max_failures_per_hour: int = 10

    # Loss thresholds
    max_daily_loss_pct: float = 0.05  # 5%
    max_drawdown_pct: float = 0.10    # 10%

    # Recovery
    recovery_timeout_sec: float = 300.0  # 5 minutes

class CircuitBreaker:
    """Circuit breaker for trading operations"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.failure_times = []
        self.opened_at: Optional[float] = None

    def record_success(self):
        """Record successful operation"""
        self.consecutive_failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.opened_at = None

    def record_failure(self, reason: str):
        """Record failed operation"""
        now = time.time()
        self.consecutive_failures += 1
        self.failure_times.append(now)

        # Remove failures older than 1 hour
        self.failure_times = [t for t in self.failure_times if t > now - 3600]

        # Check thresholds
        if (self.consecutive_failures >= self.config.max_consecutive_failures or
            len(self.failure_times) >= self.config.max_failures_per_hour):
            self.open_circuit(reason)

    def open_circuit(self, reason: str):
        """Open circuit - halt trading"""
        self.state = CircuitState.OPEN
        self.opened_at = time.time()
        # Send alert (Slack, email, etc.)
        self._send_alert(f"🚨 CIRCUIT BREAKER OPENED: {reason}")

    def can_execute(self) -> tuple[bool, Optional[str]]:
        """Check if execution allowed"""
        now = time.time()

        if self.state == CircuitState.CLOSED:
            return True, None

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if self.opened_at and now - self.opened_at > self.config.recovery_timeout_sec:
                self.state = CircuitState.HALF_OPEN
                return True, None
            return False, "Circuit breaker OPEN - trading halted"

        # HALF_OPEN - allow limited testing
        return True, None

    def _send_alert(self, message: str):
        """Send alert to operators"""
        # TODO: Implement Slack/Email/SMS alerts
        print(f"ALERT: {message}")
```

#### Manual Emergency Stop

```python
# services/execution/emergency_stop.py
import redis
import logging

logger = logging.getLogger(__name__)

class EmergencyStop:
    """Manual emergency stop mechanism"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stop_key = "emergency_stop"

    def activate(self, reason: str = "Manual stop"):
        """Activate emergency stop"""
        self.redis.set(self.stop_key, reason)
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {reason}")

    def deactivate(self):
        """Deactivate emergency stop"""
        self.redis.delete(self.stop_key)
        logger.warning("⚠️  Emergency stop deactivated")

    def is_active(self) -> tuple[bool, Optional[str]]:
        """Check if emergency stop active"""
        reason = self.redis.get(self.stop_key)
        if reason:
            return True, reason.decode() if isinstance(reason, bytes) else reason
        return False, None


# CLI command
# redis-cli SET emergency_stop "Market anomaly detected"
# redis-cli DEL emergency_stop
```

---

### 5. Audit Trail

#### Trade Logging

```python
# services/execution/audit_logger.py
import logging
import json
from datetime import datetime
from pathlib import Path

class AuditLogger:
    """Immutable audit trail for all trading operations"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Separate log file per day
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{today}.jsonl"

        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def log_order(self, event_type: str, order_data: dict, result: dict = None):
        """Log order event"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "order": order_data,
            "result": result,
        }
        self.logger.info(json.dumps(entry, ensure_ascii=False))


# Usage
audit = AuditLogger(Path("/var/log/cdb/audit"))

# Log order submission
audit.log_order("ORDER_SUBMITTED", order_data)

# Log execution result
audit.log_order("ORDER_FILLED", order_data, result)

# Log rejection
audit.log_order("ORDER_REJECTED", order_data, {"reason": "Insufficient balance"})
```

---

### 6. Network Security

#### Docker Network Isolation

```yaml
# docker-compose.yml
networks:
  cdb_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

  # External-only services (monitoring)
  monitoring_network:
    driver: bridge

services:
  cdb_execution:
    networks:
      - cdb_network  # Internal only
    # No published ports in production

  cdb_grafana:
    networks:
      - cdb_network
      - monitoring_network  # Can access external
    ports:
      - "127.0.0.1:3000:3000"  # Localhost only
```

#### Firewall Rules (Host Level)

```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change default port)
sudo ufw allow 2222/tcp

# Allow monitoring (localhost only)
sudo ufw allow from 127.0.0.1 to any port 3000  # Grafana

# Enable
sudo ufw enable
```

---

### 7. Monitoring & Alerts

#### Critical Alerts

```python
# services/monitoring/alerts.py
from dataclasses import dataclass
from enum import Enum

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Alert:
    level: AlertLevel
    title: str
    message: str
    timestamp: str

# Alert triggers
ALERT_RULES = {
    # Trading
    "order_rejection_rate": {"threshold": 0.20, "level": AlertLevel.WARNING},
    "execution_failure_rate": {"threshold": 0.10, "level": AlertLevel.CRITICAL},
    "daily_loss_pct": {"threshold": 0.05, "level": AlertLevel.CRITICAL},

    # System
    "api_latency_ms": {"threshold": 1000, "level": AlertLevel.WARNING},
    "redis_connection_errors": {"threshold": 3, "level": AlertLevel.CRITICAL},
    "postgres_connection_errors": {"threshold": 3, "level": AlertLevel.CRITICAL},

    # Security
    "unauthorized_access_attempts": {"threshold": 5, "level": AlertLevel.CRITICAL},
    "api_key_rotation_overdue": {"threshold": 90, "level": AlertLevel.WARNING},
}
```

---

## Deployment Checklist

### Pre-Production

- [ ] All secrets in Docker secrets (not .env)
- [ ] API key rotation procedure tested
- [ ] Rate limiting implemented and tested
- [ ] Order validation with conservative limits
- [ ] Circuit breakers configured
- [ ] Emergency stop mechanism tested
- [ ] Audit logging enabled
- [ ] Network isolation configured
- [ ] Firewall rules applied
- [ ] Monitoring alerts configured

### Initial Production

- [ ] Start with VERY small position limits ($100-500)
- [ ] Whitelist only 1-2 trading pairs
- [ ] DRY_RUN=false only after extensive testnet validation
- [ ] Monitor every trade manually for first 24h
- [ ] Keep emergency stop command ready
- [ ] Have rollback plan prepared

### Scaling Up

- [ ] 1 week successful operation → increase limits 2x
- [ ] 1 month successful operation → add more pairs
- [ ] 3 months successful operation → consider automation

---

## Security Incident Response

### If API Key Compromised

1. **Immediate:**
   ```bash
   redis-cli SET emergency_stop "API key compromised"
   ```

2. **Revoke:**
   - Login to MEXC
   - Revoke compromised API key
   - Check for unauthorized orders

3. **Rotate:**
   - Generate new API key
   - Update secrets
   - Restart services

4. **Audit:**
   - Review audit logs
   - Check all orders in past 24h
   - Document incident

### If Unauthorized Trading Detected

1. **Stop:**
   ```bash
   docker-compose stop cdb_execution
   redis-cli SET emergency_stop "Unauthorized activity"
   ```

2. **Assess:**
   - Check audit logs
   - Verify all orders
   - Calculate losses

3. **Secure:**
   - Rotate all credentials
   - Review access logs
   - Update security measures

4. **Report:**
   - Document timeline
   - Report to exchange if needed
   - Update procedures

---

## Additional Resources

- [OWASP Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [MEXC API Security](https://mexcdevelop.github.io/apidocs/spot_v3_en/)

---

**Remember:** Security is an ongoing process, not a one-time setup. Regular audits and updates are essential!
