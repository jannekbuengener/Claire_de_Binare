# Agent Brain Parity / Dual Run / E2E (#18)

Status: Claire consumer evidence pack for [agent-brain#18](https://github.com/jannekbuengener/agent-brain/issues/18)  
Claire tracking: #4615  
Pin: Agent Brain `v0.2.0`

## Goal exit

`CLAIRE_PARITY_DUAL_RUN_GO`

## Architecture under test

```text
Same DualRunCase fixture
        ├─→ LegacyContextPath → tools.surrealdb.context_package_v2
        └─→ AgentBrainAdapter → agent_brain.protocol (pinned 0.2.0)
                    ↓
            normalize_package_for_compare
                    ↓
         EXACT / SEMANTIC / ACCEPTED / FAIL
```

## Harness entry points

| Module | Role |
|---|---|
| `tools.agent_brain.parity` | Dual-run compare + classification |
| `tools.agent_brain.parity_fixtures` | Representative same-input cases |
| `tools.agent_brain.e2e_proof` | Context/Evidence/Memory/Trust/Rollback E2E |
| `tools.agent_brain.cleanup_go` | #19 Cleanup-Go matrix writer |

## Parity classes

`EXACT_PARITY` · `SEMANTIC_PARITY` · `ACCEPTED_CONTRACT_CHANGE` · `LEGACY_BUG_FIXED` · `UNACCEPTED_DELTA` · `UNCOMPARABLE`

Hard gate: `UNACCEPTED_DELTA = 0` and no mandatory `UNCOMPARABLE`.

## Accepted contract changes

See `docs/evidence/agent_brain_slice18_accepted_deltas.v1.json`.

Primary accepted deltas:

- Artifact wire shape: flat `artifact_id` (legacy) vs `artifact-ref/v1` (Agent Brain)
- Field aliases: `evidence_links`→`evidence_refs`, `decision_replay_links`→`decision_refs`
- Pin metadata only on agent_brain path

## Cleanup-Go

`docs/evidence/agent_brain_slice18_cleanup_go.v1.json` — #19 may delete only `SAFE_TO_REMOVE`.

## Non-goals

- Altcode cleanup / genericity proof → agent-brain#19
- Live-Go / Echtgeld / productive memory writes
