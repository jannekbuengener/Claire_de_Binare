# Decision Log

- Adopted `pytest` as the default testing framework with markers `unit` and
  `integration` plus a default `tests/` discovery path.
- Added the environment validator script `tests/validate_setup.ps1` to confirm
  local dependencies and core test files without executing tests automatically.
- Status: Implemented (N1 – test structure and scaffolds in place; integration
  tests remain skipped until services are available).
