# PR Notes

- Adjusted `tests/validate_setup.ps1` to perform static environment checks only
  and to leave pytest execution to manual commands.
- Harmonized `pytest.ini` and `TESTING.md` around the `unit`/`integration`
  markers, default `tests/` path, and example invocations.
- Clarified scaffolds: integration tests remain skipped; docker compose smoke
  test is explicitly marked as a scaffold; risk engine helpers documented.
