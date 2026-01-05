## Deterministic Event ID Contract

Event IDs are deterministic and derived from canonical event content:
`event_type`, `stream_id`, `sequence_number`, `timestamp`, and the event `payload`.

Implications:
- Any change to payload fields or serialization changes the event ID (intended).
- Treat event schemas as contracts; version changes explicitly (e.g., `schema_version` bump).
- Keep payload content stable for replay consistency.
