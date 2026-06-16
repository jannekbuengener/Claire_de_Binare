# Fresh-Clone Onboarding Rehearsal

## Status / Scope

- Status: docs-only onboarding rehearsal.
- Scope: fresh clone -> active onboarding surfaces -> optional local-confidence checks -> first safe issue/PR rehearsal.
- Authority boundary: docs/UI are orientation, not authority. GitHub live state, repo canon, governance docs, and LR-SSOT remain authoritative.
- Baseline mode: read-only by default. No Docker stack start is required.
- Safety reminder: LR remains NO-GO. Board stage `trade-capable` is not Live-Go. No Echtgeld-Go.

## Purpose

Use this rehearsal to prove that a zero-context developer can move from a fresh
clone to basic confidence without guessing the canon, printing secrets, starting
the stack, or touching runtime/trading scope.

Basic confidence means:

- you can find the active onboarding surfaces,
- you can explain the difference between Board stage and LR verdict,
- you can run the read-only onboarding doctor if needed,
- and you can describe the first safe issue/PR flow for a docs-only slice.

## Who should use this rehearsal

- A new developer entering CDB for the first time.
- A maintainer validating that onboarding links still form a usable path.
- An agent or prompt author who must point a contributor to the safest first path.

## Preconditions

- Mandatory baseline:
  - Git installed.
  - Access to clone the repo.
  - A text editor or browser for reading the onboarding surfaces.
- Optional local-confidence:
  - Python available for `python -m tools.onboarding_doctor`.
  - A local virtual environment and dev dependencies if you want lint/test smoke.
  - `gh` CLI if you want to rehearse the issue/PR workflow locally.
- Explicitly not required for the baseline:
  - Docker stack start.
  - Real secrets.
  - Runtime access.
  - DB writes.
  - MCP mutations.

## Step 1 — Fresh clone

Mode: Mandatory baseline.

Clone the repo and confirm that the checkout is sane before reading deeper docs.

```bash
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare
git status -sb
git branch --show-current
```

What good looks like:

- the repo clones without side steps,
- the working tree is clean after clone,
- and you know which branch you started from.

Record the branch and the current HEAD SHA in your notes or evidence doc.

## Step 2 — Start from README.md

Mode: Mandatory baseline.

Read [`../../README.md`](../../README.md) first.

Confirm that you can identify:

- the main new-developer entry points,
- the active safety boundary (`LR` remains `NO-GO`),
- the difference between repo/engineering status and live-readiness status,
- and the direct links into onboarding, tools, tests, and services.

Do not treat the README as the authority for runtime or go/no-go decisions. It is
the front door, not the final source of truth.

## Step 3 — Navigate docs/index.md

Mode: Mandatory baseline.

Read [`../index.md`](../index.md).

Use it as the shortest docs landing page and verify that you can find:

- the onboarding surfaces,
- the glossary,
- the visual start page,
- the developer onboarding guide,
- and the Repo Brain / Context Intelligence entry.

Important: `docs/index.md` is a pointer page. It helps you navigate the canon but
does not replace the source docs it links to.

## Step 4 — Read CDB glossary

Mode: Mandatory baseline.

Read [`cdb_glossary.md`](cdb_glossary.md) before interpreting unfamiliar terms.

At minimum, make sure you understand these terms in CDB context:

- `LR`
- `SSOT`
- `Board-Stage`
- `trade-capable`
- `Live-Go`
- `Echtgeld-Go`
- `BLUE`
- `RED`

If a later onboarding page uses a term you do not know, come back to the glossary
instead of inferring meaning from context.

## Step 5 — Use Developer Visual Start Here

Mode: Mandatory baseline.

Read [`DEVELOPER_VISUAL_START_HERE.md`](DEVELOPER_VISUAL_START_HERE.md).

Use it to build a mental map of:

- the human start path,
- the agent bootloader path,
- the authority boundary for docs/UI,
- and the example/template surfaces for a first contribution.

This page is especially useful when the repo feels large. It is still orientation,
not authority.

## Step 6 — Follow DEVELOPER_ONBOARDING.md

Mode: Mandatory baseline.

Read [`../../DEVELOPER_ONBOARDING.md`](../../DEVELOPER_ONBOARDING.md) with a narrow
goal: understand the safe baseline first, then the optional local setup path.

Prioritize these sections:

1. `Orientierung`
2. `Prerequisites`
3. `Initial Setup`
4. `Quick Verification`
5. `Development Workflow`

Do not treat `Running the Stack (Optional)` as part of the baseline. Only continue
there if your real task explicitly requires runtime work and the task scope allows it.

## Step 7 — Run onboarding doctor if available

Mode: Optional local-confidence.

If you want command-level confidence, run the read-only onboarding doctor.

```bash
python -m tools.onboarding_doctor
python -m tools.onboarding_doctor --format json
make onboarding-doctor
```

Windows PowerShell front door:

```powershell
.\tools\cdb.ps1 onboarding doctor
```

Expected behavior:

- no secret values are printed,
- no stack start is required,
- no DB write or MCP mutation occurs,
- and failures point to local setup gaps rather than runtime fixes.

If the doctor reports missing `.env` or `SECRETS_PATH`, follow
`DEVELOPER_ONBOARDING.md` for the safe local setup path. Do not paste secret values
into notes, issues, PRs, or terminal captures.

## Step 8 — Minimal safe local validation

Mode: Optional local-confidence.

Only run this step if you want extra confidence beyond the read-only baseline.

Suggested path:

1. Create and activate `.venv`.
2. Install the dev dependencies from `DEVELOPER_ONBOARDING.md`.
3. Run a small lint/test smoke without starting the stack.

```bash
ruff check .
pytest -q -k "not test_mcp_time_server_runtime"
```

Use this step to confirm that your clone is locally usable, not to prove runtime
readiness. Keep the scope local and safe.

## Step 9 — First safe issue/PR workflow rehearsal

Mode: Mandatory reading, optional execution.

Read the example flow:

- [`examples/first_issue_to_pr_flow.md`](examples/first_issue_to_pr_flow.md)

Rehearse the workflow for a tiny docs-only slice:

1. Verify the issue state on GitHub live.
2. Branch from current `main`.
3. Make the smallest scoped docs change.
4. Run the scoped validation for that slice.
5. Push and create the PR.
6. Set the required PR lock before any follow-up push or PR mutation:

```text
LOCK: agent=<agent-id> issue=#<issue> ts=<ISO8601> mode=single-writer
```

7. Wait for the repo-required checks to go green.
8. Squash-merge only if the diff stays inside the approved scope.
9. Comment the issue and close it only after the merged PR satisfies acceptance.

Stay out of runtime, Docker, trading, DB-write, memory-write, LR, or live-capital
scope for this first rehearsal.

## Evidence/report template

Suggested evidence path:

- `docs/evidence/onboarding_fresh_clone_rehearsal_<YYYY-MM-DD>.md`

Recommended starting point:

- [`templates/evidence_doc_template.md`](templates/evidence_doc_template.md)

Minimum content for the rehearsal report:

- clone date, branch, and HEAD SHA
- which mandatory steps were completed
- whether the onboarding doctor was run and what it reported
- whether optional lint/test smoke was run
- the first issue/PR flow you rehearsed or inspected
- open questions, limitations, and final confidence level

## Limitations

- This rehearsal does not prove runtime health.
- It does not prove Docker, exchange, replay, or full-stack readiness.
- It does not authorize Live-Go or Echtgeld-Go.
- It does not replace governance canon, GitHub live truth, or LR-SSOT.
- It does not create productive DB writes, memory writes, or MCP mutations.

## Safety boundaries

- Read-only by default.
- No Docker stack start as a mandatory step.
- No secret values displayed.
- No Live-Go.
- No Echtgeld-Go.
- No productive DB writes.
- No MCP mutations.
- Docs/UI are orientation, not authority.

## Troubleshooting

- If you cannot tell which status source wins, return to `AGENTS.md` ->
  `agents/AGENTS.md` and re-check the status-surface split.
- If `trade-capable` sounds like live permission, stop and re-read
  `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` plus
  `docs/runbooks/CONTROL_REGISTER.md`.
- If onboarding terms are unclear, use [`cdb_glossary.md`](cdb_glossary.md) first.
- If the onboarding doctor fails, classify the failure as a local setup gap until
  proven otherwise.
- If a step requires runtime, Docker, DB, or live behavior to continue, treat that
  as out of baseline scope and stop the rehearsal there.

## Sources

- [`../../README.md`](../../README.md)
- [`../index.md`](../index.md)
- [`cdb_glossary.md`](cdb_glossary.md)
- [`DEVELOPER_VISUAL_START_HERE.md`](DEVELOPER_VISUAL_START_HERE.md)
- [`../../DEVELOPER_ONBOARDING.md`](../../DEVELOPER_ONBOARDING.md)
- [`examples/first_issue_to_pr_flow.md`](examples/first_issue_to_pr_flow.md)
- [`templates/evidence_doc_template.md`](templates/evidence_doc_template.md)
- [`../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- [`../../docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md)
