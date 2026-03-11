## Determinism Re-Audit Bundle

Branch: fix/determinism-clock-uuid-random

Commits (relevant):
- 4d58143 Determinism: injectable clock + datetime cleanup
- ac5932b Determinism: UUID generator + event ids
- f24c2be Determinism: seed manager + mock executor

Changed core files:
- core/utils/clock.py
- core/utils/uuid_gen.py
- core/utils/seed.py

Changed tests:
- tests/unit/test_clock.py
- tests/unit/test_uuid_gen.py
- tests/unit/test_seed.py
- tests/replay/test_deterministic_replay.py

Verification commands:
- rg "datetime\\.(now|utcnow)\\(" -n
- rg "uuid\\.uuid4\\(" -n
- rg "\\brandom\\." -n
- pytest --no-cov

Expected result:
No forbidden calls outside allowed utils; replay test deterministic.

Guardrail:
- Allowed exceptions: core/utils/clock.py, core/utils/seed.py, core/utils/uuid_gen.py
- Guardrail test: tests/unit/test_clock.py (test_guardrails_no_forbidden_calls)
