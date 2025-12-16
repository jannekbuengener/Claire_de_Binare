# Docs Hub PR Checklist (Canonical)
> Purpose: Keep the Docs Hub as the single source of truth for governance/knowledge/agents.

## 1) Change type (tick one)
- [ ] Governance (policy / constitution / safety)
- [ ] Knowledge (hub, runbook, operating rules)
- [ ] Agents (roles, prompts, charters, policies)
- [ ] Docs / misc (non-canonical documentation)
- [ ] Automation (.github, workflows)

## 2) Invariants (must be true)
- [ ] No secrets were added (tokens, keys, passwords, private URLs).
- [ ] No runtime artifacts were added (logs, caches, __pycache__, *.pyc, .pytest_cache).
- [ ] Working Repo was not modified as part of this Docs Hub PR.
- [ ] If governance changed: impact is reflected in `knowledge/CDB_KNOWLEDGE_HUB.md` (decision log/topology if applicable).

## 3) Relations & navigation
- [ ] New/changed docs include a `relations:` header (or the change does not require one).
- [ ] Links were checked (no broken relative paths).

## 4) Review request
- Reviewer(s): @maintainers
