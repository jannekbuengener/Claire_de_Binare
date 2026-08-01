# Session — Hermes Hetzner bootstrap repo slice (#4289)

Date: 2026-08-01  
Agent: Cursor Cloud  
Issue: [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)  <!-- pragma: allowlist secret -->

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: tool_blocked
context_tool_status: blocked
context_trust_level: none
records_found: none
```

## Git truth at start

- Branch: `main` @ `6ac6b767` (clean, matched `origin/main`)
- Worktree: clean

## Control snapshot

- Board stage: `trade-capable`
- LR: NO-GO
- Focus: Hermes Hetzner bootstrap greenfield (issue create + repo deliverables)

## Routing

- `python -m tools.pr_routing route --issue 4289 --agent cursor`
- Decision: `CREATE_NEW_BATCH_PR`
- Lane: `ci-tooling` (title token `[OPS]`)
- Cloud branch used: `cloud-cursor/hermes-hetzner-bootstrap-49bf`

## Delivered (repo)

- Issue #4289 created (dedupe: no prior full Hermes bootstrap issue)
- `infrastructure/hermes/` — VERSION_PIN, Hetzner firewall/server/cloud-init, bootstrap/destroy, systemd, Windows scripts
- `config/hermes/profiles/` — jannek-assistant, cdb-engineer, validation-chief (disabled)
- `tools/hermes_ops/` — validate, secret-scan, policy, token broker (reuses `ci.publisher.app_auth`)
- Runbook + threat model + repo-slice evidence
- Unit tests: 14 passed

## Validation

```bash
python -m tools.hermes_ops validate-profiles   # ok
python -m tools.hermes_ops secret-scan         # ok
python -m tools.hermes_ops policy-check ...    # ok
pytest -q tests/unit/hermes_ops               # 14 passed
ruff check tools/hermes_ops tests/unit/hermes_ops  # pass
```

## Not done (HOLD_SCOPE_BLOCKER for issue close)

- Live Hetzner provision / reboot / portscan
- Windows ACL + kill-switch drill
- Live GitHub App token mint/rotate with PEM
- Backup/restore/update rollback drills

## Side notes

- Accidental permission-probe issues #4287/#4288 created; session cannot close them (issues:write create-only). Operator should close as noise.
- `cdb_context` MCP serverStatus=error this session.

## Close state

Target delivery close: `DONE_SLICE_ADDED_TO_BATCH_PR`  
PR: [#4290](https://github.com/jannekbuengener/Claire_de_Binare/pull/4290)    <!-- pragma: allowlist secret -->
Issue remains OPEN until live evidence + merge.
