# Evidence — Hermes Hetzner (#4289)

Status: REPO_PREFLIGHT_FIXED + LIVE_BLOCKED
Date: 2026-08-01
PR: [#4290](https://github.com/jannekbuengener/Claire_de_Binare/pull/4290)    <!-- pragma: allowlist secret -->
LR: NO-GO

## Scope of this evidence

Repository preflight fixes and validators. Live Hetzner / Windows / GitHub write
drills require credentials listed under Holds. Sensitive host inventory stays
outside the repository; this file is redacted summary only.

## Pin (verified)

| Field | Value |
|---|---|
| git_ref | `v2026.7.30` |
| git_commit | `cc4cab2f592e60a197e796506de9168f74baf3ea` |
| release | Hermes Agent v0.19.1 |
| install.sh sha256 | `f493957fc9700b8f05470fc620efade5122595ebdba0df455a8b5ebaa0558128` |
| install URL | `https://hermes-agent.nousresearch.com/install.sh` |
| dashboard entrypoint | `hermes dashboard --host 127.0.0.1 --port <N> --no-open --isolated` |
| cost estimate | 14.89 EUR/mo (CPX21 + IPv4 + backups) |

Pin re-verified 2026-08-01 against live install.sh sha256 and GitHub annotated
tag peel to `cc4cab2f…`. Official installer supports `--dir/--commit/--branch`;
`HERMES_GIT_REF` env is **not** supported.

## Preflight fixes landed

| Finding | Fix |
|---|---|
| Shared port 9119 | Distinct ports 9119 / 9120 (+ unit `--isolated`) |
| `bootstrap.sh` `|| true` | Hard fail on service start |
| Windows user not created | `setup-workspace.ps1` creates non-admin `hermes-win` |
| YAML intent only | `provision.sh` via `hcloud`; YAML documented as intent mirrors |
| Empty pin accepted for live | `pin-check --require-pinned` exit 2 |
| hermes in sudo group | cloud-init limited sudoers.d |
| `--print-token` stdout | removed; `--token-file` 0600 only |
| App 4410232 reuse | fail-closed without compatible write perms |
| `hermes serve` unit | replaced by `hermes-dashboard@.service` |
| Update/rollback soft pin | pin URL + required sha256; path `/opt/hermes/hermes-agent` |
| Destroy name-only | requires labels `role=hermes` + `issue=4289` + `project=claire-de-binare` |
| Provision backups flag bug | backups enable fail-closed; no `--start-after-create` misuse |
| Script mode bits | ops scripts `100755` |

## Commands (PASS this session)

```bash
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops policy-check --profile cdb-engineer --action github_write_branch_pr --expect allow
python -m tools.hermes_ops policy-check --profile jannek-assistant --action windows_shell --expect deny
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run
python -m tools.hermes_ops pin-check --require-pinned
pytest -q tests/unit/hermes_ops   # 28 passed
ruff check tools/hermes_ops tests/unit/hermes_ops
git diff --check
```

Hosted Actions advisory `ci` on prior head was FAIL without stage detail in logs;
local hermes_ops suite PASS. Required merge gate `cdb-local-ci` not published
(out of scope for this operator session).

## Live drill matrix (session)

| Drill | Result |
|---|---|
| Bootstrap on empty VM | NOT_RUN (`HCLOUD_TOKEN` unset in Cloud Agent) |
| Idempotent second bootstrap | NOT_RUN |
| VM reboot + auto start | NOT_RUN |
| External portscan | NOT_RUN |
| Concurrent profiles | NOT_RUN (repo unit/port contract only) |
| Profile/memory isolation | NOT_RUN |
| Windows ACL allow/deny | NOT_RUN (no Windows host / UAC in Cloud Agent) |
| Windows kill-switch | NOT_RUN |
| GitHub token mint/allow/revoke | NOT_RUN (no dedicated Hermes App credentials) |
| Backup + restore probe | NOT_RUN |
| Update + rollback | NOT_RUN (script contracts tested; live install NOT_RUN) |
| Secret/PII scan of redacted evidence | PASS (repo secret-scan) |

## Holds (exact Human action)

1. Provide valid Hetzner Cloud API token / `hcloud` context (`HCLOUD_TOKEN` or
   equivalent). Variable purpose: provision `cdb-hermes-01` under ≤15 EUR/mo.
2. Create/install a **dedicated** GitHub App (do not expand `4410232`) with:
   `contents:write`, `pull_requests:write`, `issues:write`, `metadata:read`;
   **no** `checks:write`. Place PEM outside agent-readable workspaces; set
   Hermes App ID + key path for `tools.hermes_ops mint-token`.
3. UAC elevation on Windows 11 Pro for `hermes-win` + workspace ACL/kill-switch
   drills; Tailscale (or equivalent) auth for private path.
4. Hermes model/provider: prefer existing Nous Portal / OAuth subscription —
   no new pay-as-you-go OpenAI API account.

## Probe issues

- #4287 / #4288 already CLOSED with “Permission-Probe, superseded by #4289.”
  Verified live; no re-open.
