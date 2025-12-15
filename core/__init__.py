---
relations:
  role: package_initializer
  domain: runtime
  upstream: []
  downstream:
    - services/db_writer/db_writer.py
    - services/execution/service.py
    - services/risk/service.py
    - services/signal/service.py
---
"""CDB Core - Shared Domain Models"""
