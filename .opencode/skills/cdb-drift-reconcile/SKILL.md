---
name: cdb-drift-reconcile
description: >
  Reconcile known Claire_de_Binare drift vectors against the current canon and
  produce a conservative findings report. Use when Codex must inspect
  documentation, runbooks, discovery surfaces, architecture maps, stack and
  secrets references, or service catalogs for canon drift, classify each area
  as belegt, unklar, or kein Befund, and separate documentation drift from
  operational drift without expanding scope. Use this for bounded canon-drift
  reconciliation, not for generic docs cleanup.
---

# CDB drift reconcile

Check known drift vectors against the current canon and return a bounded reconciliation finding, not a broad cleanup campaign.

## Inputs

- A drift-check request, drift suspicion, or maintenance pass over canon surfaces.
- Working repo at `D:\Dev\Workspaces\Repos\Claire_de_Binare`.
- Access to `docs/runbooks/CONTROL_REGISTER.md` and the repo surfaces it points to.

## Required Drift Areas

Always check these areas unless the request explicitly narrows scope further:

- Solo-Maintainer-Drift in SOPs
- Terminologie-Drift: use `Risk Service` / `cdb_risk` consistently; avoid stale service terminology
- Stack-Canon-Drift: `BLUE/RED` instead of legacy single-compose language
- Secrets-Canon-Drift
- SSOT-Grenzen between `CURRENT_STATUS.md` and `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Discovery-Surfaces / EntryPoints / Cheatsheets
- `ARCHITECTURE_MAP` / `SERVICE_CATALOG` when service changes are implicated

## Workflow

1. Read `docs/runbooks/CONTROL_REGISTER.md` first.
2. Build the search and review matrix from the drift vectors defined there:
   - Do not invent new drift categories unless the control source itself requires them.
   - Use the required drift areas above as the minimum matrix.
3. Inspect only the repo surfaces needed to evaluate the active matrix:
   - Runbooks, SOPs, status files, architecture maps, service catalogs, discovery docs, cheatsheets, and stack or secrets references.
   - Pull service maps only when the suspected drift touches service naming, boundaries, or runtime topology.
   - Keep historical snapshots and archive paths out of scope unless needed to confirm that something is merely historical.
4. Classify every checked area with exactly one finding state:
   - `belegt`
   - `unklar`
   - `kein Befund`
5. For every `belegt` or `unklar` finding, separate the impact type:
   - Documentation drift only
   - Operational drift
   - Blocker-relevant operational drift
6. Reconcile conservatively:
   - Treat historical anchors as historical unless current canon still points to them as active.
   - Treat canon-boundary uncertainty as unresolved, not as clean.
   - Do not convert every drift finding into a follow-up issue or workflow change.
   - Keep Board stage separate from LR status at all times.

## Classification Rules

- `belegt` means the repo surface directly contradicts or lags the current canon.
- `unklar` means the evidence is incomplete, ambiguous, or canon boundaries are not stable enough to call clean.
- `kein Befund` means the checked surface matches the current canon closely enough for the reviewed vector.
- Documentation drift only means wording, pointers, naming, or navigation are stale but the live operational path or enforced runtime behavior is not changed by the drift.
- Operational drift means the stale canon can misroute execution, verification, secrets handling, stack invocation, or service understanding in current work.
- Blocker-relevant operational drift means the drift can directly compromise safe operation, safe validation, or correct control interpretation and should be treated as a blocker until reconciled.

## Fail-Closed Rules

- If `CONTROL_REGISTER.md` cannot be read, stop and report reconciliation blocked.
- If canon boundaries between active docs and historical snapshots cannot be determined confidently, classify the area as `unklar`.
- If a surface looks stale but the active canon source is not identifiable, do not normalize it away; keep the finding conservative.
- If service topology, secrets canon, or status-source boundaries may be affected and the relevant maps cannot be confirmed, do not downgrade below `unklar`.
- If a finding appears historical only, but current entrypoints still route users there, classify it as active drift rather than archive noise.

## Output

Return the result in this structure:

```md
Drift-Befund
- Area: belegt | unklar | kein Befund

Betroffene Dateien / Artefakte
- ...

Schweregrad
- low | medium | high

Drift-Typ
- Dokumentationsdrift | operative Drift | blocker-relevante operative Drift

Empfohlene naechste Schritte
- ...

Nicht im Scope
- ...
```

## Anti-Patterns

- Do not turn every stale reference into a new issue.
- Do not create meta-management work that is not justified by current canon.
- Do not treat historical anchors as active tasks by default.
- Do not expand from one drift vector into a full repo rewrite.
- Do not read Board stage as LR-GO or use LR files to redefine Board stage.
