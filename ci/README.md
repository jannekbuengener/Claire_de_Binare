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
- Autonomous merge is capability-based (any session, not agent-type-based):
  see [`docs/runbooks/merge_policy_ci_gate.md`](../docs/runbooks/merge_policy_ci_gate.md)
  § Capability-based Autonomous Merge. `cdb-local-ci` SUCCESS on the exact PR
  head SHA is the required merge context; missing capability → honest
  `DONE_PR_OPEN_MERGE_HANDOFF`, never `--admin`.

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
| unit | `pytest -q -k "not test_mcp_time_server_runtime"` (SSOT; thin `ci.yml` delegates here) |
| docs | `python -m tools.validate_onboarding_docs`; `python -m tools.validate_readme_links`; `python -m tools.ci.docs_conflict_guard`; `python -m tools.ci.repository_canon_guard` |
| governance | MCP fixture validate; surreal validate; `scripts/governance/run_ci_drift_checks.py` (BP live when readable; offline baseline fallback + disclosure when gh API 403) |
| integration | 431B `base.yml` + `test.yml`, project `cdb_ci_<run_id>`, no host ports by default |
| security | gitleaks (if present) + ruff + bandit; opt-in trivy/pip-audit/codeql noted when missing |
| containers | `docker build -f ci/Dockerfile` only; no push |
| report | `reports/check-matrix.json` + fail-closed `manifest.json` |

Auf Windows bleibt `sys.executable -m black` der Default. Falls genau dieser
Interpreter einen belegten Black-Runtime-Defekt hat, darf der lokale Operator
`CDB_BLACK_EXECUTABLE` auf eine existierende Black-CLI setzen. Der Runner
validiert den Pfad fail-closed und protokolliert das konkrete Executable in der
Stage-Evidence; die Formatprüfung wird nicht übersprungen.

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
| Fast validation | `ci/scripts/run.py --profile fast` | `.github/workflows/ci.yml` thin wrapper → same orchestrator |
| Job `ci (Unit/Integration + Lint gesammelt)` | stages lint/unit/docs/governance (+ report) | advisory check-run name (not BP-required) |
| `policy-gate` | local mirror at publish only; **no full parity** | GitHub-native `policy-gate.yml` (PR API) |
| `surrealdb-validate` job | covered inside governance stage | path-filtered GitHub-native remainder in `ci.yml` |
| Docs Conflict / Canon | docs stage modules | also separate advisory workflows |
| CodeQL | optional local SARIF | Security-tab authoritative |
| Branch Protection | — | required: `cdb-local-ci` (Commit Status) |
| Local evidence | advisory artifacts until publish | — |
| Status publisher (Phase 3a) | Commit Status after validation | required context `cdb-local-ci` |

### Workflow → Stage mapping (`ci.yml` job `ci`)

| Wrapper responsibility | Canonical surface |
|------------------------|-------------------|
| Checkout + fetch `origin/main` | GitHub Actions only |
| Python 3.12 + pip install | GitHub Actions only (`run.py` installs nothing) |
| Surreal CLI on `PATH` | enables governance without Docker |
| `python ci/scripts/run.py --profile fast` | lint → unit → docs → governance → report |

GitHub-native remainder (not replaced by local orchestrator):

- `surrealdb-validate` job in `ci.yml` (path-filtered early SurrealQL syntax check)
- `.github/workflows/policy-gate.yml` (full PR/label/permission evaluation)

Do **not** treat the job name `ci (Unit/Integration + Lint gesammelt)` as the live
required context. Live required context is Commit Status `cdb-local-ci`.

## Architecture

```
pwsh/make/bash → ci/scripts/run.py → ci/stages/* → ci/artifacts/<run_id>/
                 ↑
         ci/config/stages.yaml + resources.yaml
         ci/Dockerfile (Python 3.12; matches thin ci.yml wrapper)

GitHub Actions (ci.yml job ci):
  checkout/setup/pip/surreal → python ci/scripts/run.py --profile fast

optional:
pwsh/make → ci.publisher → GitHub Commit Status (exact SHA; fail-closed)
```

GitHub status writes are `gh api` only. Direct Python HTTP writes are forbidden;
publisher validation, redaction, exact-SHA binding and anti-replay remain
mandatory.

See also: [docs/ci/index.md](../docs/ci/index.md),
[docs/ci/local-status-publisher.md](../docs/ci/local-status-publisher.md),
[docs/runbooks/merge_policy_ci_gate.md](../docs/runbooks/merge_policy_ci_gate.md).
