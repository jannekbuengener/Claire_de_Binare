"""Core Domain Models - Shared across all services

relations:
  role: package_initializer
  domain: datamodel
  upstream: []
  downstream:
    - services/db_writer/db_writer.py
    - services/execution/service.py
    - services/risk/service.py
    - services/signal/service.py
"""
