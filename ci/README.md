# Local Docker CI (Phase 1)

Lokale, Docker-fähige CI-Ausführungsschicht für Claire_de_Binare.

## Status / Grenzen

- **Phase 1:** Scaffold + Evidence-Contract unter `ci/`.
- **Phase 3a + BP #4169:** Nach strikter Evidence-Validation setzt der
  Status-Publisher (`ci/publisher/`) den Required Commit Status `cdb-local-ci`
  (interim PAT / Commit Status, noch kein GitHub-App Check Run).
  Siehe [docs/ci/local-status-publisher.md](../docs/ci/local-status-publisher.md).
- Lokale Evidence allein autorisiert keinen Merge; der published Status
  `cdb-local-ci` ist der live Required Context.
- `policy-gate.yml` bleibt als Workflow-Safety-Gate; der lokale Mirror
  (`tools/ci/policy_gate_local.py`) ist Publish-Pflicht für `cdb-local-ci`.
- Lokales CodeQL/SARIF ersetzt **nicht** den GitHub Security-Tab.
- LR bleibt **NO-GO**. Kein BLUE/RED als Default-CI. Kein GHCR-Push.

## Preferred Windows front door

```powershell
pwsh -File ci/scripts/run_all.ps1
pwsh -File ci/scripts/run_all.ps1 -Profile fast
pwsh -File ci/scripts/run_all.ps1 -Profile heavy
pwsh -File ci/scripts/run_all.ps1 -Stage lint
pwsh -File ci/scripts/run_all.ps1 -Report
pwsh -File ci/scripts/cleanup.ps1 -RunId <run_id>
```

Beide Wrapper (`run_all.ps1` / `run_all.sh`) rufen denselben Orchestrator
`ci/scripts/run.py` auf.

## Make targets

```bash
make ci-local                 # default profile=fast
make ci-local PROFILE=heavy
make ci-local-stage STAGE=lint
make ci-local-report
make ci-local-clean RUN_ID=<run_id>
make ci-local-publish-dry-run EVIDENCE_DIR=ci/artifacts/<run_id>
make ci-local-publish EVIDENCE_DIR=ci/artifacts/<run_id> STATUS_CONTEXT=cdb-local-ci-preview
make ci-local-publish-inspect COMMIT_SHA=<sha>
```

Status publisher (Windows):

```powershell
pwsh -File ci/scripts/publish_status.ps1 -Command dry-run -EvidenceDir ci/artifacts/<run_id>
pwsh -File ci/scripts/publish_status.ps1 -Command publish -EvidenceDir ci/artifacts/<run_id> `
  -StatusContext cdb-local-ci-preview
```

## Profiles

| Profile | Stages |
|---------|--------|
| `fast` (default) | lint, unit, docs, governance (+ report) |
| `heavy` | fast + integration, security, containers (+ report) |

## Stage commands (reuse-first)

| Stage | Wrapped commands |
|-------|------------------|
| lint | `ruff check .`; `black --config pyproject.toml --check` on changed `*.py` vs `origin/main` |
| unit | `pytest -q -k "not test_mcp_time_server_runtime"` (exact `ci.yml` SSOT) |
| docs | `python -m tools.validate_onboarding_docs`; `python -m tools.validate_readme_links`; `python -m tools.ci.docs_conflict_guard`; `python -m tools.ci.repository_canon_guard` |
| governance | MCP fixture validate; `make surreal-validate`; `scripts/governance/run_ci_drift_checks.py` |
| integration | 431B `base.yml` + `test.yml`, project `cdb_ci_<run_id>`, no host ports by default |
| security | gitleaks (if present) + ruff + bandit; opt-in trivy/pip-audit/codeql noted when missing |
| containers | `docker build -f ci/Dockerfile` only; no push |
| report | `reports/check-matrix.json` + fail-closed `manifest.json` |

## Evidence contract

Path: `ci/artifacts/<run_id>/`

Required:

- `manifest.json` / `manifest.sha256`
- `logs/<stage>.log`
- `reports/check-matrix.json`

Bindings:

- Exact `commit_sha` + `branch`
- `dirty_worktree=true` ⇒ overall `BLOCKED`
- Foreign repo / SHA mismatch / duplicate `run_id` ⇒ reject
- Any required SKIPPED ⇒ overall `FAIL`
- Optional SKIPPED requires `skip_reason`

## Resources (16 GB host defaults)

See `ci/config/resources.yaml`: light parallelism ≤2, heavy serial, memory caps
for ci_image/test_runner/postgres/redis, compose project template
`cdb_ci_${run_id}`. Cleanup never deletes unrelated projects/volumes.

## Local vs GitHub parity

| Surface | Local | GitHub |
|---------|-------|--------|
| Required `ci.yml` commands | high (wrapped in local stages) | advisory workflow (not BP-required) |
| `policy-gate` | local mirror enforced at publish | workflow safety (not BP-required) |
| Docs Conflict / Hub | extracted tools modules | workflows still inline |
| CodeQL | optional local SARIF | Security-tab authoritative |
| Branch Protection | — | required: `cdb-local-ci` (Commit Status) |
| Local evidence | advisory artifacts until publish | — |
| Status publisher (Phase 3a) | Commit Status after validation | required context `cdb-local-ci` |

## Architecture

```
pwsh/make/bash → ci/scripts/run.py → ci/stages/* → ci/artifacts/<run_id>/
                 ↑
         ci/config/stages.yaml + resources.yaml
         ci/Dockerfile (Python 3.12; matches ci.yml, not Dockerfile.test 3.14)

optional:
pwsh/make → ci.publisher → GitHub Commit Status (exact SHA; fail-closed)
```

See also: [docs/ci/index.md](../docs/ci/index.md),
[docs/ci/local-status-publisher.md](../docs/ci/local-status-publisher.md),
[docs/runbooks/merge_policy_ci_gate.md](../docs/runbooks/merge_policy_ci_gate.md).
