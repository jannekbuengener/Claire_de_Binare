# Issue #1146 - docs_hub_snapshot Retention Handoff

Stand: 2026-03-13
Audience: Claude Code
Scope: read-only analysis completed; no implementation performed here

## Ist-Analyse

- The meta docs already define the intended direction: `docs/archive/docs_hub_snapshot/` is a local read-only archive for provenance plus a narrow compatibility core, not a second active docs home. That framing is already present in `docs/meta/DOCS_HUB_POST_DELETE_STATUS.md`, `docs/meta/DOCS_HUB_DELETE_READINESS.md`, and `docs/meta/DOCS_HUB_RETIREMENT_HANDOFF.md`.
- The snapshot still contains clear low-signal retained areas with no visible active references in the working repo, especially `docs/archive/docs_hub_snapshot/mcp_navpack_docs_hub*` and `docs/archive/docs_hub_snapshot/_archive/discussion_pipeline/`. The multi-generation navpacks are the clearest redundancy cluster.
- The strongest repo drift is not the existence of the snapshot, but contradictory signposting inside it. `docs/archive/docs_hub_snapshot/DOCS_HUB_INDEX.md` still presents itself as `status: canonical` and "Single Source of Truth". `docs/archive/docs_hub_snapshot/README.md` is still an old docs-hub entry README. `_legacy_quarantine/README.md` still says the contents are "Safe to delete", while the current meta docs treat quarantine as retained provenance until an explicit later decision.
- The currently visible load-bearing archive surface is narrower than the retained tree suggests. Active repo references point mainly into `docs/archive/docs_hub_snapshot/knowledge/...` and the archive root index files documented in `infrastructure/docs/DOCS_HUB_RAG_ADAPTERS.md`. The bulk of the retained snapshot looks like historical ballast rather than active recovery core.
- The strongest keep candidates inside the snapshot are specific audit/recovery areas, not the tree as a whole: `knowledge/agent_trust/`, `knowledge/logs/sessions/`, `knowledge/operations/disaster_recovery/`, `knowledge/playbooks/`, `knowledge/runbooks/`, `knowledge/reviews/`, `knowledge/audits/`, and `verlosung/VERLOSUNG_SECRET_MANIFEST.md`.
- The strongest review-target ballast is also concrete: `mcp_navpack_docs_hub*` alone outweigh the full archived `knowledge/` tree, `_archive/discussion_pipeline/` is bulk from a deprecated path, `cdb_docs_index.yaml` is a mixed legacy generator artifact, `agents/roles/` mirrors large parts of `agents/`, and parts of `knowledge/archive/docs_legacy/` plus `_legacy_quarantine/` contain obvious duplicates.
- There is a boundary drift with active pointer wording: `docs/meta/WORKING_REPO_CANON.md` and `mcp_navpack_working_repo/DOCS_HUB.pointer.*` still talk about "recovery" more broadly than the meta-retention docs. For `#1146`, treat that as a risk note and hard boundary, not as default implementation scope, otherwise the issue bleeds back into `#1145`.

## Minimaler Zielzustand fuer #1146

- Make the retention policy explicit without broad archive deletion.
- Align the snapshot entry documents with the already-declared retention reality: archive/provenance, non-default, no active canon claim.
- Distinguish three buckets clearly:
  - retained core: audit/provenance material and the narrow compatibility surface that is still intentionally referenced, especially the snapshot `knowledge/` audit/recovery zones and the secret-manifest provenance
  - retained but review-target: redundant or low-signal archive areas such as `mcp_navpack_docs_hub*`, `_archive/discussion_pipeline/`, `_legacy_quarantine/`, duplicate-heavy legacy agent/material mirrors, and one-off root dumps like `issues.md`
  - not in this issue: actual subtree deletion, archive reorg, or behavior-bearing compatibility changes
- Resolve the explicit quarantine contradiction: `_legacy_quarantine/` is not active input, but it is also not a silent "delete now" action for this issue.

## Dateiliste fuer Claude Code

Touch only this minimal set unless a hard contradiction forces one adjacent edit:

- `docs/meta/DOCS_HUB_DELETE_READINESS.md`
- `docs/meta/DOCS_HUB_POST_DELETE_STATUS.md`
- `docs/meta/DOCS_HUB_MIGRATION_MATRIX.md`
- `docs/archive/docs_hub_snapshot/DOCS_HUB_INDEX.md`
- `docs/archive/docs_hub_snapshot/README.md`
- `docs/archive/docs_hub_snapshot/_legacy_quarantine/README.md`

Do not default to touching these, even though they are related context:

- `docs/meta/WORKING_REPO_CANON.md`
- `mcp_navpack_working_repo/DOCS_HUB.pointer.md`
- `mcp_navpack_working_repo/DOCS_HUB.pointer.json`
- `infrastructure/scripts/docs_hub_rag_adapter.py`
- `infrastructure/scripts/discussion_pipeline/utils/config_loader.py`
- `docs/archive/docs_hub_snapshot/**` payload directories

## Risiken, Annahmen, offene Punkte

- Assumption: `mcp_navpack_docs_hub*` are retained history only. Current repo search shows no active working-repo references outside the meta docs themselves, but this issue should still avoid deleting them.
- Assumption: the real retention core is narrower than the full snapshot tree and currently centers on provenance plus specific historically referenced files under `knowledge/` and the archive root marker files.
- Open point: `cdb_docs_index.yaml` is explicitly classified as obsolete in the migration matrix, but `infrastructure/scripts/docs_hub_rag_adapter.py` still enumerates it as an archive root index candidate. Because that is behavior-bearing compatibility, `#1146` should document the constraint, not change it.
- Open point: the broader "compatibility recovery" wording in active pointer files is real drift, but changing it here risks overlap with `#1145`. Keep it as a boundary note unless retention wording cannot otherwise be made coherent.
- Risk: once Claude Code starts deleting or moving archive subtrees, the issue will lose its minimal maintenance profile and drift into a larger archival cleanup project. Do not cross that line in `#1146`.

## Nicht-Ziele

- No broad deletion inside `docs/archive/docs_hub_snapshot/`
- No archive reorganization
- No changes to active canon docs except where retention wording absolutely requires a one-line boundary clarification
- No changes to behavior-bearing shims, adapters, CLI flags, env vars, or fallback code
- No runtime, compose, LR, CI, or general docs-hub migration cleanup
- No hidden continuation of `#1145`

## Claude-Code-Handoff

### Ziel

Sharpen the docs-only retention policy for `docs_hub_snapshot` so the repo clearly communicates what is intentionally kept, what is only retained pending later review, and what is explicitly out of scope for this issue. Do this without deleting archive payloads and without reopening active docs-hub compatibility work.

### Betroffene Dateien

- `docs/meta/DOCS_HUB_DELETE_READINESS.md`
- `docs/meta/DOCS_HUB_POST_DELETE_STATUS.md`
- `docs/meta/DOCS_HUB_MIGRATION_MATRIX.md`
- `docs/archive/docs_hub_snapshot/DOCS_HUB_INDEX.md`
- `docs/archive/docs_hub_snapshot/README.md`
- `docs/archive/docs_hub_snapshot/_legacy_quarantine/README.md`

### Minimale Aenderungen

- In the three meta docs, make the retention buckets explicit:
  - what is retained as provenance / narrow compatibility core
  - what remains retained but is only a later review target
  - what this issue will not delete or reorganize
- In `docs/archive/docs_hub_snapshot/DOCS_HUB_INDEX.md`, remove the remaining active-canon framing and restate it as an archive index for historical lookup only.
- In `docs/archive/docs_hub_snapshot/README.md`, align the entrypoint wording with the current post-migration reality: local archive, read-only, non-default.
- In `_legacy_quarantine/README.md`, replace the implicit deletion instruction with wording that matches the current retention stance: quarantined provenance, no active references, later explicit prune decision if any.
- Do not touch archive payload directories, navpack contents, or adapter code.

### Validierung

- Check that the touched snapshot entry docs no longer claim canon or SSOT:

```powershell
rg -n "canonical|Single Source of Truth|Docs Hub = Canon|Working Repo = Execution" docs/archive/docs_hub_snapshot/DOCS_HUB_INDEX.md docs/archive/docs_hub_snapshot/README.md
```

- Check that the retention language is consistent across meta docs and quarantine wording:

```powershell
rg -n "provenance|narrow compatibility core|review target|not active input|Safe to delete" docs/meta/DOCS_HUB_DELETE_READINESS.md docs/meta/DOCS_HUB_POST_DELETE_STATUS.md docs/meta/DOCS_HUB_MIGRATION_MATRIX.md docs/archive/docs_hub_snapshot/_legacy_quarantine/README.md
```

- Check that no behavior-bearing compatibility files were pulled into the diff:

```powershell
git diff --name-only -- docs/meta docs/archive/docs_hub_snapshot infrastructure/scripts mcp_navpack_working_repo
```

Expected result: only the six target docs above are changed.

### Rollback / Sicherheitsgrenzen

- This issue should remain docs-only. If a proposed change requires deleting archive content, moving snapshot directories, or editing compatibility code, stop and cut scope instead.
- If wording changes create ambiguity around active pointer behavior, revert only the archive/meta wording edits from this issue and push the remaining pointer drift back to `#1145` or a dedicated follow-up.
- Leave generated navpacks, discussion-pipeline archive content, and root historical dumps physically untouched in `#1146`.

## Harter Cut nach #1146

After the minimal retention clarification is in place, stop. Do not use this issue to start a broad archive thinning pass, navpack purge, quarantine sweep, or docs-hub compatibility rewrite.
