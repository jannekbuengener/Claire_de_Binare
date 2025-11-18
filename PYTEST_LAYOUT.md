# Pytest Layout – Claire de Binaire

## Ordnerstruktur
```
tests/
├─ conftest.py
├─ test_risk_engine_core.py
├─ test_risk_engine_limits.py
└─ test_config_env.py
```

## Beispieltests
### Daily Drawdown
```python
def test_daily_drawdown_blocks_trading(...):
    ...
```

### Exposure-Limit
```python
def test_exposure_blocks_new_orders(...):
    ...
```
