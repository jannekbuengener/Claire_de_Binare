# Agent Brain Consumer Cutover (#13)

Status: active cutover surface for Slice 13  
Upstream: [agent-brain#13](https://github.com/jannekbuengener/agent-brain/issues/13)

## Architecture

```text
Claire de Binare
      ↓
tools.agent_brain (adapter / path selection / Claire policy)
      ↓
agent_brain.protocol (public #12 surface)
      ↓
Agent Brain core
```

## Pin

- Version: `0.2.0` (includes #12; **not** `v0.1.0`)
- Requirement file: `requirements-agent-brain.txt`
- Config: `config/agent-brain/consumer_cutover.v1.json`

Forbidden pins: `main`, branches, `latest`, local workspace paths.

## Path selection

| Path | Meaning |
|---|---|
| `legacy` | Existing Claire Context Package / Surreal tooling (`tools.surrealdb.*`) |
| `agent_brain` | Pinned Agent Brain public protocol consumer |

Default: `legacy` (safe). Override via config `consumer_path` or env `CDB_AGENT_BRAIN_CONSUMER_PATH`.

Rollback: set path back to `legacy` (explicit switch; not a silent fallback; not a git revert).

## Non-goals (#13)

- No Dual Run / Parity Proof → #18 (see `docs/onboarding/agent_brain_parity_dual_run.md`)
- No Altcode cleanup → #19
- No Live-Go / Echtgeld-Go
- No productive memory writes

## Slice #18 follow-on

Parity / Dual Run / E2E evidence lives under:

- `tools/agent_brain/parity.py`
- `tools/agent_brain/e2e_proof.py`
- `docs/evidence/agent_brain_slice18_*.json`
