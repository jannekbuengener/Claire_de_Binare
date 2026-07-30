# CDB Decision Surface Matrix

Use this matrix before issuing a verdict.

| Surface | Primary question | Canon anchor | Typical failure mode |
|---|---|---|---|
| Stage-System | Is a Board-stage claim or transition justified? | `#1445`, newest weekly comment, `#1492` when relevant, `docs/runbooks/CONTROL_REGISTER.md` | Stage is silently promoted into LR |
| LR-System | Is a live-readiness claim justified? | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | `CURRENT_STATUS.md` is misread as LR authority |
| Repo/Engineering-Status | Is the repo, PR, or engineering ledger claim justified? | `CURRENT_STATUS.md` | closed issue or merged code is overstated as broader proof |
| Runtime/Operator-Reality | Is the system operable or fail-closed in practice? | current runbooks, committed artifacts, direct runtime evidence | dashboards or stories substitute for technical checks |
| CI/Workflow-Reality | Is a workflow, gate, or ruleset claim justified? | workflows, rulesets, current GitHub state | green status hides skipped or soft-failed gates |
| Data-contract/persistence-reality | Is a field or metadata claim proven end-to-end? | producer, consumer, tests, persisted artifacts | one layer mentions a field and the rest is assumed |
| Documentation/reporting quality | Is the defect only phrasing or actually technical? | report text plus the canon it references | reporting artifact is inflated into system defect |

Rule:
- If more than one surface is involved, separate them.
- Never let one verdict class overwrite another surface.
