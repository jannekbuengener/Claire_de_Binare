# Live → Fixture → Mock Policy

- Default tests: offline only
- Gate live probes with CDB_EXTERNAL_TESTS=1
- Capture fixtures with secrets redacted
- Replay fixtures deterministically in CI
