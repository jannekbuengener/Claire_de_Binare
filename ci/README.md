# Local Docker CI (Phase 1)

Lokale, Docker-fähige CI-Ausführungsschicht für Claire_de_Binare.

## Status / Grenzen

- **Phase 1:** Scaffold + Evidence-Contract unter `ci/`.
- **Phase 3a + BP #4169:** Nach strikter Evidence-Validation setzt der
  Status-Publisher (`ci/publisher/`) den Required App Check Run `cdb-local-ci`
  (`app_id=4410232`, `--publisher-backend check-run`).
  Siehe [docs/ci/local-status-publisher.md](../docs/ci/local-status-publisher.md).
- **#4170 Phase A:** Explizites Check-Run-Backend
  (`--publisher-backend check-run`) ist code-ready; Branch Protection und der
  Default-Pfad bleiben Commit Status bis zum externen Cutover.
  Siehe [docs/runbooks/cdb_local_ci_app_check_run_cutover.md](../docs/runbooks/cdb_local_ci_app_check_run_cutover.md).
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

| Profile | Stages | Merge evidence? |
|---------|--------|-----------------|
| `fast` (default) | lint, unit, docs, governance (+ report) | Eligible after publish (`merge_evidence=true`) |
| `slice` (#4204) | same stages as fast; unit may use path-selected groups | **Never** (`merge_evidence=false`) |
| `heavy` | fast + integration, security, containers (+ report) | Eligible after publish when clean |

### Slice selection (#4204)

```bash
python ci/scripts/run.py --profile slice \
  --changed-path ci/lib/slice_selection.py \
  --routing-lane ci-tooling \
  --validation-profile ci-tooling-v1
```

Policy: `ci/config/slice_validation_policy.v1.yaml`. Selection report:
`ci/artifacts/<run_id>/reports/slice_selection.json`. Unknown paths and
policy errors fall back to the full Fast-CI unit selector. Timing evidence:
`--unit-durations 50` (default) writes `reports/unit_timing.json` and
`reports/stage_timing.json` without changing pass/fail.

## Stage commands (reuse-first)

| Stage | Wrapped commands |
|-------|------------------|
| lint | `ruff check .`; `python -m black --config pyproject.toml --check --workers 1` on sorted changed `*.py` vs `origin/main` (timeout-bound) |
| unit | `pytest -q -k "not test_mcp_time_server_runtime"` (SSOT; thin `ci.yml` delegates here) |
| docs | `python -m tools.validate_onboarding_docs`; `python -m tools.validate_readme_links`; `python -m tools.ci.docs_conflict_guard`; `python -m tools.ci.repository_canon_guard` |
| governance | MCP fixture validate; surreal validate; `scripts/governance/run_ci_drift_checks.py` (BP live when readable; offline baseline fallback + disclosure when gh API 403) |
| integration | 431B `base.yml` + `test.yml`, project `cdb_ci_<run_id>`, no host ports by default |
| security | gitleaks (if present) + ruff + bandit; opt-in trivy/pip-audit/codeql noted when missing |
| containers | `docker build -f ci/Dockerfile` only; no push |
| report | `reports/check-matrix.json` + fail-closed `manifest.json` |

### Black toolchain SSOT (#4206)

- **Versionsquelle:** `requirements-dev.txt` (`black==26.5.1`, `ruff==0.16.1`). Keine unversionierte Zweitinstallation in `ci/Dockerfile` oder `.github/workflows/ci.yml`.
- **Kanonischer Ausführungsweg:** `sys.executable -m black` (CI-Frontdoor-Interpreter), Config aus `pyproject.toml`, nur Changed-Files, `--workers 1`.
- **Timeout:** Default `300` Sekunden aus `ci/config/resources.yaml` (`black_timeout_seconds`); Override `CDB_BLACK_TIMEOUT_SECONDS` (Cap `900`). Hang → Stage-**FAIL** mit `reason_code=BLACK_TIMEOUT` und Exit 124 — niemals SKIP/PASS. Timeout und Version stehen in der Lint-Evidence.
- **Reason Codes:** `BLACK_TIMEOUT`, `BLACK_EXECUTABLE_MISSING`, `BLACK_EXECUTABLE_INVALID`, `BLACK_VERSION_MISMATCH`, `BLACK_EXECUTION_FAILED`.
- **Changed-File-Contract:** deterministisch sortiert; gelöschte Dateien ausgeschlossen; `.codex/**` / `.opencode/**` ausgeschlossen; Git-Fehler fail-closed; leerer Satz explizit geloggt.
- **Keine globale Python-3.14-Abhängigkeit.**

`CDB_BLACK_EXECUTABLE` bleibt ein strikt validierter Escape Hatch (kein Default):
existierende reguläre Datei, keine Shell-Argumente, `black --version` muss exakt
dem Pin aus `requirements-dev.txt` entsprechen. Override-Nutzung wird mit
`$HOME`-Redaktion in der Evidence ausgewiesen. Abweichungen enden fail-closed.

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

## Temp-root preflight (#4205)

Before unit/pytest stages, the orchestrator probes a run-scoped temp root at
`ci/artifacts/<run_id>/tmp` (create/read/rename/delete). Failure stops the run
with a stable reason code (`TEMP_ROOT_*`) and writes
`reports/temp_preflight.json` (redacted paths only — no user-home absolutes).
On success, `TEMP`/`TMP`/`TMPDIR` and pytest `--basetemp` / `cache_dir` point
at that controlled root. No global ACL changes, no foreign-temp cleanup, no
`.wslconfig` edits.

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
| Branch Protection | — | required: `cdb-local-ci` (App Check Run `app_id=4410232`) |
| Local evidence | advisory artifacts until publish | — |
| Status publisher (Phase 3a/#4170) | App Check Run after validation | required `cdb-local-ci` (`app_id=4410232`) |

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
required context. Live required context is App Check Run `cdb-local-ci` (`app_id=4410232`).

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
