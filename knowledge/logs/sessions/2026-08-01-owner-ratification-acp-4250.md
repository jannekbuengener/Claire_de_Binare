# Session 2026-08-01 — Owner Ratification of ACP Canon (#4250)

## Decision
Owner **Jannek Büngener** declared `Ratifizieren` / `RATIFY` for
`knowledge/governance/CDB_AGENT_CONTROL_PLANE.md` based on corrected commit
`c691a8d0469924cf233fd72965bb77b7f98bb9db` (2026-08-01 Europe/Berlin).

## Integrity
- Pre-ratification check: working-tree ACP content at session start was
  byte-identical to `c691a8d0` (`git diff --quiet`).
- Ratification documentation updates status/pointers only; Authority-/Truth-Order
  from `c691a8d0` remains the ratified normative content.
- Limits recorded in-canon: no merge, no `cdb-local-ci` publish, no Live-Go,
  no governance weakening, no auto-ratify of later material changes.

## Delivered in ratification commit
- Canon status flip Proposal → Canonical + Owner Ratification Record
- Pointer sync: `knowledge/governance/README.md`, `AGENTS.md`, `agents/AGENTS.md`,
  Execution Contract predecessor language

## Boundaries
- LR NO-GO
- Does not authorize `#4253`+ implementation by itself
- Material post-ratification edits require re-ratification
