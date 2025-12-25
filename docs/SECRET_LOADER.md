---
title: Unified Secret Loader
agent: claude
scope: SECURITY
phase: 1
related_issues: [#224]
related_files: [DEVELOPMENT.md, ARCHITEKTUR.md]
---

Kurzbeschreibung:
Zentrale Read-Funktion `cdb_utils.secret_loader.read_secret` zur einheitlichen Verarbeitung von Secrets.

Usage contract (machine-parsable):
- inputs:
  - name: string (logical secret name)
  - env_var: optional string (env var name)
  - file_path: optional string (absolute or repo-relative path to secret file)
  - dir_path: optional string (absolute or repo-relative path to dir containing secret files)
  - default: optional string
- priority: [env_var, file_path, dir_path (named file), dir_path (single-file), default]
- outputs: string (secret value)
- errors: SecretNotFoundError

Notes for agents:
- When linking to files in related_files, prefer repo-relative paths.
- For programmatic search, prefer env first to avoid file-system access.

Related Issues: #224
Related Files: DEVELOPMENT.md, ARCHITEKTUR.md

CI test job suggestion (minimal):

Use the following GitHub Actions job snippet to run the unit tests for the secret loader. This is a minimal suggestion — adapt Python version or matrix as needed.

```yaml
name: Test Secret Loader
on: [push, pull_request]

jobs:
  test-secret-loader:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install test requirements
        run: |
          python -m pip install --upgrade pip pytest
      - name: Run tests
        run: pytest tests/test_secret_loader.py -q
```
