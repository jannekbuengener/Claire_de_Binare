# Evidence — Hermes Hetzner repo slice (#4289)

Status: REPO_SLICE (not live E2E)  
Date: 2026-08-01  
PR: [#4290](https://github.com/jannekbuengener/Claire_de_Binare/pull/4290)    <!-- pragma: allowlist secret -->
LR: NO-GO

## Scope of this evidence

Repository deliverables only. No Hetzner account mutation, no Windows host
mutation, no live GitHub App PEM usage in this cloud session.

## Commands

```bash
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops policy-check --profile cdb-engineer --action github_write_branch_pr
python -m tools.hermes_ops policy-check --profile jannek-assistant --action windows_shell --expect deny
python -m tools.hermes_ops mint-token --profile cdb-engineer --dry-run
python -m tools.hermes_ops pin-check
pytest -q tests/unit/hermes_ops
```

## Expected

- Profiles `jannek-assistant` and `cdb-engineer` validate; `validation-chief` disabled by contract.
- Secret-scan: zero findings on Hermes repo surfaces.
- `cdb-engineer` may plan scoped GitHub write; forbidden actions denied.
- `jannek-assistant` Windows shell denied.
- Token dry-run shows repo-scoped permissions without `checks:write`.
- VERSION_PIN present; live install still requires operator fill-in.

## Live drills still required (Human-GO / credentials)

- Empty-VM bootstrap + idempotent second run
- Reboot persistence
- Public portscan
- Profile isolation of memories/secrets
- Windows ACL + kill-switch
- Backup/restore + update/rollback
- Live token mint/rotate/revoke

Mark issue intermediate status `HOLD_SCOPE_BLOCKER` until those pass with redacted evidence.
