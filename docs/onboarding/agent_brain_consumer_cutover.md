# Agent Brain Consumer Cutover

Status: active Claire consumer of immutable Agent Brain  
Upstream: [agent-brain#13](https://github.com/jannekbuengener/agent-brain/issues/13) · [agent-brain#18](https://github.com/jannekbuengener/agent-brain/issues/18) · [agent-brain#19](https://github.com/jannekbuengener/agent-brain/issues/19)

## Architecture

```text
Claire de Binare
      ↓
tools.agent_brain (adapter / path selection / Claire policy)
      ↓
agent_brain.protocol (public #12 surface)
      ↓
Agent Brain core (generic; no Claire/trading runtime)
```

## Pin

- Version: `0.2.1` (includes #12 protocol surface + #19 genericity)
- Requirement file: `requirements-agent-brain.txt`
- Config: `config/agent-brain/consumer_cutover.v1.json`

Forbidden pins: `main`, branches, `latest`, local workspace paths.

## Path selection

| Path | Meaning |
|---|---|
| `agent_brain` | Pinned Agent Brain public protocol consumer (**default**) |
| `legacy` | Existing Claire Context Package / Surreal tooling (`tools.surrealdb.*`) — rollback / dual-run only |

Override via config `consumer_path` or env `CDB_AGENT_BRAIN_CONSUMER_PATH`.

Rollback: set path back to `legacy` (explicit switch; not a silent fallback; not a git revert).

## Safety

- No Live-Go / Echtgeld-Go via this cutover
- No productive memory writes
- Claire-specific policy remains Claire-owned

## Related evidence

- Parity / Dual Run / E2E: `docs/evidence/agent_brain_slice18_*.json`
- Cleanup authority (#18): `docs/evidence/agent_brain_slice18_cleanup_go.v1.json`
- Genericity / Cleanup (#19): `docs/evidence/agent_brain_slice19_genericity_cleanup.v1.json`
