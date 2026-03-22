# GOVERNANCE_QUICKREF

Version: 2.0
Status: canonical

## 1. Hierarchy

| Rank | Document | Purpose |
|---|---|---|
| 1 | User (Jannek) | Highest authority |
| 2 | `CDB_CONSTITUTION.md` | System constitution |
| 3 | `CDB_GOVERNANCE.md` | Operating governance |
| 4 | `knowledge/governance/CDB_AGENT_POLICY.md` | Agent behavior rules |
| 5 | specific policies in `knowledge/governance/` | domain-specific constraints |
| 6 | `agents/AGENTS.md` | local registry and read order |
| 7 | agent role files in `agents/` and `agents/roles/` | role-specific mandates |
| 8 | code, configs, workflows | implementation |

## 2. Delivery Gate

Rule: no live deployment without explicit user gate.

Canonical file:
- `knowledge/governance/DELIVERY_APPROVED.yaml`

## 3. Agent Behavior

Must:
- respect explicit user decisions
- stop and ask when authority is unclear
- load the local context core before acting
- keep issue and evidence hygiene current

Must not:
- reactivate external docs-hub defaults
- change governance without approval
- commit secrets
- bypass delivery or safety gates

## 4. Write Areas

| Path | Default rule |
|---|---|
| `knowledge/governance/**` | restricted, review-heavy |
| `agents/**` | allowed only within role and governance constraints |
| `knowledge/**` | operational docs and evidence allowed |
| `docs/**` | navigation, templates, archives, derived views |
| code and infra paths | allowed per agent policy and issue scope |

## 5. Absolute No-Gos

1. Never commit secrets.
2. Never change delivery gates without explicit owner approval.
3. Never perform autonomous capital movement.
4. Never treat an external docs repo as active canon.
5. Never skip the local context core on ambiguous work.

## 6. Conflict Resolution

1. Higher-rank authority wins.
2. User direction overrides all documents.
3. When unclear: stop and ask.

## 7. Session-End Minimum

- update `CURRENT_STATUS.md` when repo/main/test/dependency status materially changes
- update `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` only when the operational Go/No-Go verdict or its gating evidence changes
- update `knowledge/CURRENT_STATUS.md` only for historical snapshot maintenance or context backfill
- leave evidence in local issue, report, or knowledge paths
- state blockers explicitly
- do not offload the final state to an external docs repo
