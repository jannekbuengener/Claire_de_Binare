#!/usr/bin/env python3
"""
Healthcheck script for cdb_db_writer service.
Verifies Redis connectivity with password from secrets.
"""
import sys
import redis

try:
    with open('/run/secrets/redis_password', 'r') as f:
        password = f.read().strip()

    r = redis.Redis(host='cdb_redis', password=password, socket_connect_timeout=3)
    r.ping()
    sys.exit(0)
except Exception as e:
    print(f"Healthcheck failed: {e}", file=sys.stderr)
    sys.exit(1)
