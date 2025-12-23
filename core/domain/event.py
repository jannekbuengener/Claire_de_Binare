# core/domain/event.py

# Canonical Redis Stream Names
# These names should be used consistently across all services for Redis Streams.

# Stream for order results published by the execution service
# Consumers: db_writer, risk (and potentially PSM)
CANONICAL_ORDER_RESULTS_STREAM = "stream.cdb.order_results"

# Other canonical stream names can be added here as needed
# CANONICAL_SIGNALS_STREAM = "stream.cdb.signals"
# CANONICAL_ORDERS_STREAM = "stream.cdb.orders"
# CANONICAL_BOT_SHUTDOWN_STREAM = "stream.cdb.bot_shutdown"
# CANONICAL_RISK_RESET_STREAM = "stream.cdb.risk_reset"