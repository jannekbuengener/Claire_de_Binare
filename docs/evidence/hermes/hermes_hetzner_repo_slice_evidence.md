# Evidence — Hermes Hetzner (#4289)

Status: REPO_PREFLIGHT_FIXED + LIVE_BLOCKED
Date: 2026-08-01
PR: [#4290](https://github.com/jannekbuengener/Claire_de_Binare/pull/4290)    <!-- pragma: allowlist secret -->
LR: NO-GO

## Scope of this evidence

Repository preflight fixes and validators. Live Hetzner / Windows / GitHub write
drills require credentials listed under Holds.

## Pin (verified)

| Field | Value |
|---|---|
| git_ref | `v2026.7.30` |
| git_commit | `cc4cab2f592e60a197e796506de9168f74baf3ea` |
| release | Hermes Agent v0.19.1 |
| install.sh sha256 | `f493957fc9700b8f05470fc620efade5122595ebdba0df455a8b5ebaa0558128` |
| dashboard entrypoint | `hermes dashboard --host 127.0.0.1 --port <N> --no-open --isolated` |
| cost estimate | 14.89 EUR/mo (CPX21 + IPv4 + backups) |

## Preflight fixes landed

| Finding | Fix |
|---|---|
| Shared port 9119 | Distinct ports 9119 / 9120 (+ unit `--isolated`) |
| `bootstrap.sh` `|| true` | Hard fail on service start |
| Windows user not created | `setup-workspace.ps1` creates non-admin `hermes-win` |
| YAML intent only | `provision.sh` via `hcloud` |
| Empty pin accepted for live | `pin-check --require-pinned` exit 2 |
| hermes in sudo group | cloud-init limited sudoers.d |
| `--print-token` stdout | removed; `--token-file` 0600 only |
| App 4410232 reuse | fail-closed without compatible write perms |
| `hermes serve` unit | replaced by `hermes-dashboard@.service` |
| Backup/update/rollback | `backup.sh` / `restore.sh` / `update.sh` / `rollback.sh` |

## Commands

```bash
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops policy-check --profile cdb-engineer --action github_write_branch_pr --expect allow
python -m tools.hermes_ops policy-check --profile jannek-assistant --action windows_shell --expect deny
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run
python -m tools.hermes_ops pin-check --require-pinned
pytest -q tests/unit/hermes_ops
ruff check tools/hermes_ops tests/unit/hermes_ops
```

## Live drill matrix (session)

| Drill | Result |
|---|---|
| Bootstrap on empty VM | NOT_RUN (hcloud token unauthorized) |
| Idempotent second bootstrap | NOT_RUN |
| VM reboot + auto start | NOT_RUN |
| External portscan | NOT_RUN |
| Concurrent profiles | NOT_RUN (repo unit/port contract only) |
| Profile/memory isolation | NOT_RUN |
| Windows ACL allow/deny | NOT_RUN (needs elevated UAC) |
| Windows kill-switch | NOT_RUN |
| GitHub token mint/allow/revoke | NOT_RUN (no compatible App) |
| Backup + restore probe | NOT_RUN |
| Update + rollback | NOT_RUN |
| Secret/PII scan of redacted evidence | PASS (repo secret-scan) |

## Holds (exact Human action)

1. Provide valid Hetzner Cloud API token for `hcloud` context (current: unauthorized).
2. Create/install a **dedicated** GitHub App (do not expand `4410232`) with:
   `contents:write`, `pull_requests:write`, `issues:write`, `metadata:read`; no `checks:write`.
3. Optional: UAC elevation for Windows user creation; Tailscale auth; Hermes model/provider (prefer existing Nous/OAuth — no new pay-as-you-go OpenAI).
