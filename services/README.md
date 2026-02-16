# Contains individual microservices implementations.

## Where to write / Where not to write
*   **Write here:** Stateless microservices code, service-specific configurations, Dockerfiles, requirements.
*   **Do NOT write here:** Shared core logic (use `core/`), persistent state (use PSM concept), governance documents.

## Key entrypoints
*   [DB Writer Service (services/db_writer/)](services/db_writer/)
*   [Execution Service (services/execution/)](services/execution/)
*   [Regime Service (services/regime/)](services/regime/)
*   [Risk Service (services/risk/)](services/risk/)
*   [Signal Service (services/signal/)](services/signal/)
*   [Allocation Service (services/allocation/)](services/allocation/)

## Redis Transport Notes

- **market_data**: Uses Redis **Pub/Sub** (not Redis Streams). `XLEN market_data` returns 0 — this is expected.
- **signals, orders, allocation_decisions**: Use Redis **Streams** for durable event log.
