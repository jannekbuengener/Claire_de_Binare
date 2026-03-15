# Docs Hub Migration Matrix

Status: working-repo consolidation for Issue #1140
Source repo: `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs`
Target repo: `D:\Dev\Workspaces\Repos\Claire_de_Binare`
Archive snapshot: `docs/archive/docs_hub_snapshot/`

This matrix records how the remaining Docs-Hub content was classified for the
physical consolidation. Productive content is moved into active working-repo
paths; historical or broken material is kept only as local archive/quarantine.

## Root

| Source | Relevance | Target | Action | Rationale |
|---|---|---|---|---|
| `DOCS_HUB_INDEX.md` | historical | `docs/meta/WORKING_REPO_CANON.md` | merge | Its navigation model is useful, but the old docs-hub-as-canon statement is retired. |
| `README.md` | historical | `docs/archive/docs_hub_snapshot/README.md` | archive | Import-pack README, not the correct entrypoint for the consolidated repo. |
| `README_TEMPLATE_PACK.md` | productive | `docs/templates/README_TEMPLATE_PACK.md` | merge | Still useful as operator guidance for GitHub issue templates. |
| `index.yaml` | historical | `docs/archive/docs_hub_snapshot/index.yaml` | archive | Built for the docs-only structure and no longer authoritative. |
| `cdb_docs_index.yaml` | obsolete | `docs/archive/docs_hub_snapshot/cdb_docs_index.yaml` | quarantine/archive | Mixed or malformed legacy index; preserved only for provenance. |
| `issues.md` | historical | `docs/archive/docs_hub_snapshot/issues.md` | archive | Time-bound issue dump, not durable canon. |
| `notes_72h_papertrading_tools.md` | historical | `docs/archive/docs_hub_snapshot/notes_72h_papertrading_tools.md` | archive | Tactical move note from the split-repo era. |
| `VERLOSUNG_SLICE_C_PLAN.md` | historical | `docs/archive/docs_hub_snapshot/VERLOSUNG_SLICE_C_PLAN.md` | archive | One-off migration plan, valuable only as audit trace. |
| `.gitignore`, `.gitattributes`, `CODEOWNERS` | mixed | local equivalents or snapshot | merge/archive | Old docs-repo policy files were reviewed; only still-useful parts should survive locally. |

## Agents

| Source | Relevance | Target | Action | Rationale |
|---|---|---|---|---|
| `agents/AGENTS.md` | productive | `agents/AGENTS.md` | merge | Richest legacy registry; needed local-first rewrite to remove split assumptions. |
| `agents/AUTOLOAD_MANIFEST.yaml` | productive | `agents/AUTOLOAD_MANIFEST.yaml` | merge | Machine-readable bootstrap stays useful once base paths point local. |
| `agents/{CLAUDE,CODEX,COPILOT,GEMINI}.md` | productive | `agents/` and `agents/roles/` | merge | Role content remains relevant, but duplicate variants and old repo-routing must not stay active. |
| `agents/orchestrator.md` | productive | `agents/orchestrator.md` | keep | Local role doc is directly useful and repo-neutral enough to retain. |
| `agents/roles/{CODEX_SUPPORT_ROLE,GEMINI_SUPPORT_ROLE}.md` | unclarified but useful | `agents/roles/` | merge | Keep as local role supplements after consolidation. |
| `agents/prompts/` | historical | `docs/archive/docs_hub_snapshot/agents/prompts/` | archive | Prompt artifacts are process history, not active canon. |
| `agents/tasklists/` | historical | `docs/archive/docs_hub_snapshot/agents/tasklists/` | archive | Dated task plans and handoffs should not drive current navigation. |
| `agents/agent_orga/`, `AGENT_SETUP_GUIDE.md`, `AGENT_QUICKSTART.md`, `PLAN_AGENT_DOCS_ORCHESTRATION.md` | historical | `docs/archive/docs_hub_snapshot/agents/agent_orga/` | archive | These texts presuppose the retired docs-hub topology. |
| `agents/HV/` | historical | `docs/archive/docs_hub_snapshot/agents/HV/` | archive | Optional specialist mode, not part of the productive minimum canon. |

## Knowledge

| Source | Relevance | Target | Action | Rationale |
|---|---|---|---|---|
| `knowledge/governance/` core policy stack | productive | `knowledge/governance/` | merge | Constitution, governance, policy stack, trust config, and invariants are required locally. |
| `knowledge/agent_trust/` | productive | `knowledge/agent_trust/` | copy/merge | Schemas, rules, and ledgers remain part of the operating model. |
| `knowledge/discussions/` | productive | `knowledge/discussions/` | copy/merge | Discussion pipeline config and issue drafts are still operationally relevant. |
| `knowledge/runbooks/`, `knowledge/playbooks/`, `knowledge/operations/` | productive | `knowledge/` | copy/merge | Runbooks and operational notes belong in the consolidated repo. |
| `knowledge/roadmap/`, `knowledge/decisions/`, `knowledge/contracts/`, `knowledge/testing/`, `knowledge/security/` | productive | `knowledge/` | copy/merge | These are genuine planning and system-knowledge assets. |
| `knowledge/reviews/`, `knowledge/logs/`, `knowledge/archive/`, `knowledge/migrations/` | historical | `knowledge/` or `docs/archive/` | retain as local archive/history | Valuable for traceability, but not active canon. |
| `knowledge/root pointer files` such as `SYSTEM.CONTEXT.md`, `ACTIVE_ROADMAP.md`, `EXPANDED_ECOSYSTEM_ROADMAP.md` | productive | same local paths | rewrite | Old pointer stubs had to become real local entrypoints. |
| `knowledge/deep-issues-lab/` | productive but contextual | `knowledge/deep-issues-lab/` | copy | Useful design deep-dives; safe to keep local as reference corpus. |
| `knowledge/staging/`, `knowledge/content/`, `knowledge/context_build/` | mixed | same local paths plus archive | selective merge | Keep useful onboarding/context docs, but treat split-era verification artifacts as historical. |

## Meta And GitHub

| Source | Relevance | Target | Action | Rationale |
|---|---|---|---|---|
| `meta/github/{SECURITY,pull_request_template,LABELS,MILESTONES,bug_report,feature_request}.md` | obsolete duplicates | existing `.github/` paths | discard | Already present locally at productive paths. |
| `meta/github/ARCHITECTURE_ISSUE_144.md` | historical | `docs/archive/github/ARCHITECTURE_ISSUE_144.md` | archive with local pointer | Useful design evidence, but no longer an external pointer target. |
| `meta/github/BRANCH_TRIAGE_2026-01-08.md` | historical | `docs/archive/github/BRANCH_TRIAGE_2026-01-08.md` | archive with local pointer | Useful cleanup evidence, but not active canon. |
| `.github/ISSUE_TEMPLATE/{standard,meta_cluster,meta_phase,meta_governance,meta_tracking}.md` | productive | `.github/ISSUE_TEMPLATE/` | copy | Still-useful issue templates not yet present in the working repo. |
| `.github/ISSUE_TEMPLATE/config.yml` | productive | `.github/ISSUE_TEMPLATE/config.yml` | merge | Contact links should point to local guidance and local governance docs. |
| `.github/workflows/docs_conflict_guard.yml`, `.github/workflows/docs-ci.yml` | historical | `docs/archive/docs_hub_snapshot/.github/workflows/` | archive | These workflows guarded the old standalone docs repo, not the consolidated repo. |
| `meta/legacy/` | historical | `docs/archive/docs_hub_snapshot/meta/legacy/` | archive | Explains how the split happened and why it was retired. |
| `meta/migrations/` | historical | `docs/archive/docs_hub_snapshot/meta/migrations/` | archive | Migration plans are audit evidence, not live canon. |

## Scripts, Tools, Archives, And Misc

| Source | Relevance | Target | Action | Rationale |
|---|---|---|---|---|
| `scripts/translate.js` and `scripts/README_TRANSLATION_INTEGRATION.md` | unclarified | snapshot first | archive pending explicit reuse | Useful enough to preserve locally, but not required for current production docs flow. |
| `tools/enforce-root-baseline.README.md` | obsolete duplicate | `tools/enforce-root-baseline.README.md` | discard | Working-repo version already replaced the split-repo rule set. |
| `_archive/` | historical | `docs/archive/docs_hub_snapshot/_archive/` | archive | Old canon and snapshots must remain accessible, but only locally. |
| `_legacy_quarantine/` | historical | `docs/archive/docs_hub_snapshot/_legacy_quarantine/` | archive | Keep as quarantine provenance, not active input. |
| `mcp_navpack_docs_hub*` | historical | `docs/archive/docs_hub_snapshot/mcp_navpack_docs_hub*/` | archive | Captures the old navigation model; productive nav now lives in `mcp_navpack_working_repo/`. |
| `verlosung/` | historical | `docs/archive/docs_hub_snapshot/verlosung/` | archive | Experimental or one-off migration artifacts. |
| `.git/`, `.worktrees/`, `.local/`, `.cdb_local/` | non-product code state | none | exclude | Repository internals or machine-local state, not migration content. |

## Snapshot Retention Buckets (#1146)

After consolidation, the local snapshot at `docs/archive/docs_hub_snapshot/` is
classified as follows:

| Bucket | Contents | Status |
|---|---|---|
| Provenance / narrow compatibility core | `knowledge/` audit/recovery subtrees, secret-manifest provenance, root index files, `cdb_docs_index.yaml` (behavior-bearing compat) | Intentionally retained |
| Later review target | `mcp_navpack_docs_hub*`, `_archive/discussion_pipeline/`, `_legacy_quarantine/`, duplicate agent mirrors, `issues.md` | Retained, not active input |
| Not changed in #1146 | All archive content | No deletion or reorganization |

## Consolidation Result

- Productive canon now lives in the working repo under `agents/`, `knowledge/`,
  `docs/`, `.github/`, and selected root entrypoints.
- Historical material from the old docs repo is preserved locally through
  `docs/archive/docs_hub_snapshot/` plus targeted archive copies where faster
  navigation matters.
- The sibling repo `Claire_de_Binare_Docs` is no longer required as a runtime,
  navigation, or knowledge dependency after the remaining local rewrites land.
