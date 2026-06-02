# SurrealDB Context MCP Access — Agent Runbook

**Status**: Draft
**Authority**: Issue #2101 / Wave 12 Parent #2091 / Epic #1976
**Scope**: Local/dev only. Document how agents access the Context MCP Bridge layer safely, with read-only semantics and fail-closed guardrails.

This runbook is **not** a production activation guide. It does not authorize live trading, does not change Live-Readiness, and does not enable any write path.

---

## 1. Purpose and Scope

This runbook describes how agents use the **Context MCP Bridge** (`tools/mcp/`) to access the SurrealDB Context Intelligence System through a read-only MCP-compatible tool layer.

Use cases:
- Search the context knowledge base
- Trace decision and event lineage
- Explain provenance of context sources
- Package context artifacts for agent handoff
- Assess action readiness before starting work
- Resolve stop conditions and required reads
- Generate structured briefings for session start

Out of scope for this runbook:
- Production SurrealDB activation
- Any write operations (CREATE, UPDATE, DELETE, etc.)
- Trading-state, risk, execution, governance, or runtime state
- Live-trading, Live-Readiness, or Echtgeld authorization
- Context import pipeline (see `surrealdb_context_import.md`)
- Context query CLI (see `surrealdb_context_query.md`)

---

## 1.5. MCP Capability Resolution Protocol

**Before relying on any tool in this runbook, resolve capability explicitly.**

Repo-defined tools are not automatically available to agents. A tool is available
only when the active MCP surface exposes it and invocation dispatches a real handler.

**Capability beats assumption. Repo presence is not MCP availability.**

| Check | Pass criterion | Fail action |
|---|---|---|
| Active MCP inventory | Required tool appears in the active MCP tool list | Stop and report missing surface/config |
| Dispatch | Tool call reaches a real handler | Stop on `unknown_tool` or `not_implemented` |
| Read-only contract | Response reports `metadata.read_only == true` where applicable | Stop and report contract violation |
| DB-backed mode | SurrealDB is accessed only when `adapter_config_path` is explicitly passed | Stop if DB access is implicit |
| Local DB boundary | Remote DB URLs are rejected | Stop and report boundary failure |
| Write/admin guard | Write/admin statements fail closed before network access | Stop and report guard failure |

For repo-native Context MCP access, `claire-de-binare.mcp.json` must expose the
`cdb_context` server entry under the top-level `mcpServers` object:

```json
{
  "mcpServers": {
    "cdb_context": {
      "enabled": true,
      "command": ".venv/Scripts/python.exe",
      "args": ["-m", "tools.mcp.server"],
      "type": "stdio"
    }
  }
}
```

Windows-local CDB uses the repo `.venv` interpreter (relative path). Linux/macOS:
`.venv/bin/python` with the same args. The MCP host must invoke the server from the
repository root so that `tools.*` module paths resolve correctly. Stdio from repo root
is the primary path — not HTTP `127.0.0.1:8811`.

If any capability check fails:
- Do not switch to a raw/external SurrealDB MCP server.
- Report the exact missing layer.
- Propose the smallest CDB-native read-only fix after Human-GO.

Established by PR #2559 (`a35d7728`). Cross-reference: `cdb-session-start` skill, step 5.

### 1.5.1. Agent MCP Installation Matrix

This matrix defines how every active agent surface accesses the CDB Context MCP.
Repo presence is not MCP availability. Each surface must be verified independently.

**Five-level distinction:**

| Level | Criterion | How to verify |
|---|---|---|---|
| L1 | Config file exists | `claire-de-binare.mcp.json` present in repo root |
| L2 | Agent host knows config | Host MCP config references `cdb_context` server entry |
| L3 | MCP server starts | L3a: bridge import (`create_bridge()` works); L3b: stdio server import (`import tools.mcp.server` — bounded, no event loop). If bridge works but stdio is blocked by env, report WARN — bridge-level access is available, host integration needs env fix. |
| L4 | Tool inventory exposes target | `context.briefing` appears in active MCP tool list |
| L5 | Actual invocation works | `context.briefing({...})` returns valid response |

**Per-surface status:**

| Agent Surface | L1 Config | L2 Host | L3 Server | L4 Inventory | L5 Invocation | Overall Status |
|---|---|---|---|---|---|---|---|
| **Codex** | ✓ verified | via host agent (OpenCode or Claude) | ⚠️ blocked (env: pydantic-core mismatch) | ✓ bridge verified | ✓ bridge verified | reference in agents/templates/codex_mcp_config.md |
| **OpenCode** | ✓ verified | ✓ host-active verified | ✓ host-active verified | ✓ bridge verified | ✓ bridge verified | repo-tracked config (`opencode.jsonc`) + host-active; cdb_context server connected in OpenCode UI |
| **Claude / Cloud Code** | ✓ verified | template in `agents/templates/claude_mcp.json.template` | needs host-specific test | needs host-specific test | needs host-specific test | template exists; needs host-specific copy to user-level `.mcp.json` |
| **Gemini** | ✓ verified | template in `agents/templates/gemini_mcp_config.yml.template` | needs host-specific test | needs host-specific test | needs host-specific test | template exists; needs host-specific embed in workflow YAML |
| **Onboarding / new agent** | ✓ verified | setup script in `agents/templates/onboarding_mcp_setup.ps1` | ⚠️ blocked (env: pydantic-core mismatch) | ✓ bridge verified | ✓ bridge verified | setup script validates L1/L3/L4/L5; L2 requires manual host config |

**Status key:**
- `✓ verified` — directly confirmed in this repo session
- `✓ repo-tracked config` — actual config file tracked in repo, auto-loaded by agent host
- `✓ host-active verified` — agent host loaded and connected the MCP server (green in host UI)
- `via host agent` — covered by calling agent's MCP config
- `template in ...` — tracked template file; requires manual copy/embed
- `setup script in ...` — executable validation script
- `⚠️ blocked (env)` — local environment dependency conflict (pydantic-core version); not a code defect
- `needs host-specific test` — requires the specific agent host to be running with the config registered

**Validation commands (bridge-level, works regardless of MCP SDK):**

```bash
# Bridge creates successfully — returns tool count (Windows-local venv)
.venv/Scripts/python.exe -c "from tools.mcp.context_bridge import create_bridge; b=create_bridge(); print(len(b.list_tools()))"
# Expected: 27

# Key tool present in inventory
.venv/Scripts/python.exe -c "from tools.mcp.context_bridge import create_bridge; b=create_bridge(); print('context.briefing' in [t['name'] for t in b.list_tools()])"
# Expected: True
```

Active bridge inventory (`create_bridge().list_tools()`): **27** read-only tools.
The count delta vs. the pre-#2704 inventory of 26 is **`cdb_context_memory_write_intent`**
(dry-run Human-GO gate evaluation only; no DB adapter; not a Wave-15–20 surface).
Inspect with:

```bash
python -c "from tools.mcp.context_bridge import create_bridge; print([t['name'] for t in create_bridge().list_tools()])"
```

Linux/macOS: use `.venv/bin/python` instead of `.venv/Scripts/python.exe`.

**Validation command (stdio server import — bounded, does not enter event loop):**

```bash
.venv/Scripts/python.exe -c "import tools.mcp.server; print('STDIO IMPORT OK')"
# If blocked by pydantic-core version mismatch, fix:
# pip install 'pydantic>=2.0,<3.0' 'pydantic-core==2.46.4'
```

> **Note on OpenCode command:** The tracked `opencode.jsonc` uses portable `python` so Linux/macOS/Cloud Agent checkouts work out of the box. Windows-local CDB may override to `.venv/Scripts/python.exe` in user-level `~/.config/opencode/opencode.jsonc` when system Python lacks project deps.
>
> **Note on config naming:** OpenCode's project-level config must be named `opencode.jsonc` or `opencode.json` (no leading dot). The repo tracked config was renamed from `.opencode.jsonc` to `opencode.jsonc` to match this requirement. Pre-existing user-level config at `~/.config/opencode/opencode.jsonc` is loaded alongside and merged per OpenCode's config precedence rules.
>
> **Note on server naming:** The repo defines server name `cdb_context`. If a user-level or remote config defines a different server named `cdb`, it is a separate server entry. Both coexist in the OpenCode MCP list. The `cdb` (remote) failure shown in OpenCode is pre-existing and unrelated to the repo baseline — it targets `http://127.0.0.1:8812/mcp` and requires a separate MCP server on that port.

**Repo-tracked configs and templates:**

| Surface | File | Type | Location |
|---------|------|------|----------|
| OpenCode | `opencode.jsonc` | repo-tracked config (auto-loaded) | repo root |
| Claude / Cloud Code | `claude_mcp.json.template` | template (copy to user-level `.mcp.json`) | `agents/templates/` |
| Gemini | `gemini_mcp_config.yml.template` | template (embed in workflow YAML) | `agents/templates/` |
| Codex | `codex_mcp_config.md` | reference (no separate MCP surface) | `agents/templates/` |
| Any surface | `onboarding_mcp_setup.ps1` | validation script (run from repo root) | `agents/templates/` |

Run the onboarding script to validate your setup:

```bash
pwsh -File agents/templates/onboarding_mcp_setup.ps1
```

**Context onboarding doctor** (#2642) — zusätzlicher read-only Preflight für Secrets,
lokale Config, SurrealDB und optionalen MCP-HTTP-Port:

```bash
make context-doctor
python -m tools.surrealdb.context_onboarding_doctor --format json
```

- Repo-stdio-MCP: `cdb_context` in `claire-de-binare.mcp.json` (kein TCP-Port nötig).
- Issue #2642 prüft optional `127.0.0.1:8811` (HTTP MCP host).
- Separater remote `cdb`-Server in OpenCode nutzt laut Runbook-Hinweis `127.0.0.1:8812/mcp` — nicht mit #2642 verwechseln.

**Context operator certification** (#2776) — wiederholbarer read-only Proof Pack
für Bridge/Registry/Permission-Guard (kein produktiver DB-Smoke, kein `--apply`):

```bash
make context-certify
python -m tools.surrealdb.context_certify --format json
python -m tools.surrealdb.context_certify --format markdown --output context-certify.md
```

| Exit code | Meaning |
| --- | --- |
| `0` | `final_verdict: certified` — static registry/guard gates pass |
| `1` | Blocking failure (e.g. non-read-only tool in registry) |
| `2` | CLI or output validation error |

Default behavior:
- Emits JSON (with `--format json`) or markdown/text summary including `gate_matrix`,
  `skipped_checks_with_reason`, `safety_flags`, and `lr_note: NO-GO`.
- Does **not** run `make context-smoke-db`, `make context-smoke`, or any `--apply` path.
- Live MCP/SurrealDB probes are **skipped** unless `--include-live-checks` (non-blocking).

Safety boundary: `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`; LR remains **NO-GO**;
Phase-2 (#2778) is not activated by certification alone.

**Operator flow — certification → readiness (#2801):**

1. `make context-doctor` (inventory / optional live checks)
2. `make context-certify` (or `--format json`) — redact secrets before sharing proof
3. Embed a subset of the proof pack in the readiness bundle as `operator_certification`
   (alias: `context_certification`)
4. Evaluate via `cdb_agent_os_readiness` MCP tool or `evaluate_agent_os_readiness_v1`

Windows canonical surface: PowerShell onboarding
(`agents/templates/onboarding_mcp_setup.ps1`) plus the Makefile targets above.
CI does **not** require live SurrealDB for certification or readiness evaluation.

**Certification adoption matrix (PASS / WARN / FAIL / BLOCKED / SKIPPED):**

| Signal | Source | Agent OS readiness effect | Adoption claims | Unrelated PRs |
| --- | --- | --- | --- | --- |
| **PASS** | `final_verdict: certified`, no blocking gates | No certification findings | Allowed with redacted proof | Not blocked |
| **WARN** | Non-blocking gate `fail`, or `adoption_status: warn` | Weak finding + validation step | Only with documented caveat | Not blocked |
| **SKIPPED** | Non-empty `skipped_checks_with_reason` | Weak finding + validation step | Require documented skip reasons | Not blocked |
| **FAIL** | `final_verdict: fail` or blocking gate `fail` | Blocking finding | **Blocked** | Not blocked |
| **BLOCKED** | `blocked_checks_with_reason` or gate `status: blocked` | Blocking finding | **Blocked** | Not blocked |
| **missing** | No `operator_certification` in bundle | Listed in `missing_inputs` only | No adoption claim without certify | Not blocked |
| **invalid** | Non-mapping or unknown verdict | Weak finding (fail-closed) | No silent green | Not blocked |

Agent OS Readiness is a **signal**, not an authorization. Certification is an
**adoption gate**, not LR-Go. Missing certification must not block unrelated PR
work or general readiness checks that do not claim operator adoption.

Expected output (best case — bridge + stdio both work):
```
=== CDB Context MCP Capability Validation ===
[L1] Config file exists... PASS
[L2] Host knows config (manual check)... SKIP (manual)
[L3] Bridge and stdio server check... PASS
       Bridge: 27 tools, Stdio import: OK
[L4] context.briefing in tool inventory... PASS
[L5] context.briefing invocation... PASS
=== Results: 4 passed, 0 warnings, 0 failed ===
CDB Context MCP is available.
```

Expected output (bridge works, stdio blocked by env):
```
=== CDB Context MCP Capability Validation ===
[L1] Config file exists... PASS
[L2] Host knows config (manual check)... SKIP (manual)
[L3] Bridge and stdio server check... BRIDGE OK — STDIO BLOCKED
       Bridge: 27 tools, Stdio import: BLOCKED
       STDIO WARN: <error details>
       This is a local environment blocker (pydantic-core version mismatch),
       not a #2619 config defect. Bridge-level tool access works.
       Fix: pip install 'pydantic>=2.0,<3.0' 'pydantic-core==2.46.4'
[L4] context.briefing in tool inventory... PASS
[L5] context.briefing invocation... PASS
=== Results: 4 passed, 1 warnings, 0 failed ===
CDB Context MCP is available (bridge); warnings above.
```

**Capability Resolution Rules (all surfaces):**

When scope includes Context, MCP, SurrealDB, ContextBridge, DB-backed Memory, or Evidence:

**Source priority** (SSOT: `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`):
live GitHub → repo files → SurrealDB context package (guarded adapter only) →
ledger (`CURRENT_STATUS.md` not live truth) → fallback. Context/MCP/briefing
output does not authorize automatic code, issue, or productive DB writes.

1. Run MCP Capability Resolution before planning — verify active tool inventory, not config file presence.
2. If `context.briefing` or required MCP tools are unavailable: stop or explicitly degrade to repo-only.
3. Do not claim DB-backed Brain/Evidence/Memory unless `surrealdb-local` or equivalent DB-backed source is actually available and usable.
4. For Wave-14 read-only MCP tools, `metadata.source` must come only from guarded adapter evidence; caller-supplied `source`, `brain_source`, `brain_status`, or nested `metadata.source` values are not DB proof.
5. Non-DB fallback must not report DB-backed `brain_status="used"`.
6. Missing MCP access must be reported as `brain_source=unavailable` or explicit `repo-only` / `brain_status=not-used` fallback.
7. Repo-wide fallback for any surface that cannot verify MCP access: `brain_source=repo-only`, `brain_status=not-used`, repo evidence under `records_or_results`.

---

## 2. Non-Goals (Anti-Criteria)

This runbook explicitly does **not** establish or imply any of the following:

- No production default. The MCP Bridge uses mocked/in-memory adapters (NoopQueryAdapter); no live SurrealDB.
- No write path. All tools are read-only; three-layer defense blocks write attempts.
- No Repo/FS write. Tools do not create, modify, or delete repo files.
- No GitHub action. Tools do not create/close issues, PRs, comments, or trigger workflows.
- No Runtime action. Tools do not execute deploys, docker commands, or environment changes.
- No DB/Memory write. Tools do not write to SurrealDB tables, agent memory, or any persistent store.
- No Live-Readiness change. LR verdict remains **NO-GO** for live trading independent of this runbook.
- No Echtgeld-Go. Wave 12 completion does not authorize real capital.
- No Board-Stage override. `trade-capable` is a Board artefact; it does not authorize live access.

---

## 3. Prerequisites

Required:
- Python 3.12 (matches repo target; see `pyproject.toml`)
- Local repository checkout of `Claire_de_Binare` on a Wave-12 or later commit
- The MCP bridge is pure Python (no compiled dependencies, no system packages)

Not required:
- **Docker is not required.** The default adapter is in-memory (NoopQueryAdapter) and offline.
- **SurrealDB is not required.** The bridge never opens a real network connection.
- **Context Import is optional.** Tools return mocked responses without imported data. For real data, see `surrealdb_context_import.md`.

---

## 4. Bridge Instantiation

```python
from tools.mcp.context_bridge import create_bridge

bridge = create_bridge()
tools = bridge.list_tools()
tool_names = [t["name"] for t in tools]

print(f"Loaded {len(tools)} tools: {', '.join(tool_names)}")
```

The bridge initializes with real handler implementations (not registry stubs) and asserts read-only consistency on construction. All tools return structured dictionaries with `"tool"`, `"status"` (either `"ok"` or `"error"`), and tool-specific fields.

As of #2704, `create_bridge().list_tools()` returns **27** tools (all `read_only: true`). The inventory includes Wave-14 evidence/memory/decision handlers, Wave-15–20 bundle adapters, and `cdb_context_memory_write_intent` (dry-run gate scaffold; no persistence path).

Call a tool:

```python
result = bridge.execute_tool("context.search", {"query": "risk governance"})
print(result["status"])  # "ok" or "error"
```

---

## 5. Available Tools

| Tool | Status | Description |
|------|--------|-------------|
| `context.search` | Full | Search the context knowledge base (keyword + structured queries). Returns results with confidence scores and warnings. |
| `context.trace` | Full | Trace decision or event lineage through the context graph. Returns root node and lineage chain. |
| `context.explain_source` | Full | Resolve provenance for a registered tool or existing repo-relative file path. Repo-/registry-only, deterministic, no DB/network, rejects absolute and traversal paths. |
| `context.package` | Full | Package context artifacts for handoff between agents or sessions. Capped at 10 items. Includes stop conditions. |
| `context.readiness` | Full | Assess agent action readiness for a given task scope. Returns one of 6 readiness status values. Requires task_scope and operation_mode. |
| `context.self_explain` | Full | Generate structured self-explanation for governance-relevant conditions. 9 explanation types supported. |
| `context.briefing` | Full | Generate structured briefing for agent handoff or session start. Delegates to readiness and package handlers. |
| `context.stop_resolver` | Full | Map stop condition strings to resolved severity/action. Handles S1–S10 and H1–H5. |
| `context.required_reads` | Full | Resolve which canonical files an agent must read before starting work. 7-layer resolution. |
| `context.show_snapshot` | Full | Deterministic registry snapshot (tool inventory + read-only flags). No DB/network/GitHub. |
| `context.show_audit` | Full | Deterministic registry audit snapshot for a target tool (schema keys + handler wiring status). No DB/network/GitHub. |

All 11 tools are registered as `read_only: true`. `context.show_snapshot`, `context.show_audit`, and `context.explain_source` are deterministic repo-/registry-only views (no DB-backed trail).

---

## 6. Permission Guardrails (Three-Layer Defense)

The MCP Bridge enforces read-only access through three gates (`#2099`):

### 6.1 Registry Gate
- `ContextToolRegistry.register()` rejects any `ToolDefinition` with `read_only=False`.
- `assert_read_only_consistency()` runs on `ContextBridge.__init__()` to catch post-init tampering.

### 6.2 Execute Gate
- `execute_tool()` validates the tool exists and is read-only before dispatch.
- Non-dict parameters (list, string, int, None) return `invalid_parameters` error without reaching the handler.

### 6.3 Input Gate
- **Scan tools** (free-text parameters scanned for mutation keywords): `context.search`, `context.trace`, `context.explain_source`, `context.package`, `context.show_snapshot`, `context.show_audit`
- **Exempt tools** (structural tools with validated enums, no free-text scan needed): `context.readiness`, `context.briefing`, `context.self_explain`, `context.stop_resolver`, `context.required_reads`

**Blocked keywords** (16 standalone): `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `MUTATE`, `REPLACE`, `REMOVE`, `MERGE`, `RELATE`, `DEFINE`, `REBUILD`, `TRUNCATE`, `GRANT`, `REVOKE`

**Blocked query patterns** (14 regexes): e.g. `INSERT INTO`, `UPDATE ... SET`, `CREATE TABLE`

**Blocked runtime operations** (26 strings): e.g. `git_commit`, `git_push`, `docker_build`, `deploy`, `release`, `pr_create`, `issue_create`

Input scanning uses word-boundary regex and recursive parameter walking (dicts and lists). Violations return agent-readable error codes: `forbidden_keyword`, `forbidden_query_pattern`, `forbidden_runtime_operation`.

---

## 7. Tool Usage Examples

`context.search` examples below still use mocked/in-memory responses. `context.trace` is read-only and fail-closed, but in the current repo-/in-memory bridge mode it does not invent provenance or lineage. `context.package`, `context.explain_source`, `context.show_snapshot`, and `context.show_audit` are deterministic repo-/registry-only handlers. For real SurrealDB data, a future Wave will provide a real adapter where applicable.

### 7.1 context.search

```python
result = bridge.execute_tool("context.search", {
    "query": "risk governance decisions",
    "limit": 5,
    "filters": {"source_types": ["decision", "evidence"]}
})
```

Response (ok):
```json
{
    "tool": "context.search",
    "status": "ok",
    "results": [],
    "metadata": {"query_time_ms": 0, "total_hits": 0}
}
```

Error (invalid query):
```json
{
    "tool": "context.search",
    "status": "error",
    "error": {
        "code": "invalid_query",
        "message": "query is required and must be a non-empty string"
    }
}
```

### 7.2 context.trace

```python
result = bridge.execute_tool("context.trace", {
    "target_id": "evt_001",
    "depth": 5
})
```

Response:
```json
{
    "tool": "context.trace",
    "status": "ok",
    "trace": {
        "root": {"id": "evt_001", "type": "unknown", "title": "Trace target: evt_001"},
        "lineage": []
    }
}
```

Maximum depth is 20. `depth_exceeded` error returned above 20. In the current read-only bridge mode, lineage stays empty unless a future evidence-backed resolver is available.

### 7.3 context.explain_source

```python
result = bridge.execute_tool("context.explain_source", {
    "source_ref": "context.readiness",
    "include_chain": True
})
```

Supported refs: exact tool name, `tool:<tool-name>`, repo-relative file path, or
`path:<repo-relative-path>`. Prefixes are strict: `tool:` only checks the registry,
`path:` only checks repo files. Unknown refs fail closed with `source_not_found`.
Absolute paths, Windows drive paths, UNC paths, and `..` traversal fail closed with
`invalid_source_ref`. File outputs always use repo-relative paths only.

Response:
```json
{
    "tool": "context.explain_source",
    "status": "ok",
    "explanation": {
        "source_ref": "context.readiness",
        "source_type": "tool",
        "provenance": {
            "tool_name": "context.readiness",
            "read_only": true,
            "handler_status": "implemented",
            "input_schema_keys": [
                "operation_mode",
                "required_reads",
                "stop_conditions",
                "task_scope"
            ],
            "output_schema_keys": [
                "human_go_required",
                "reasons",
                "required_next_reads",
                "status",
                "warnings"
            ],
            "resolver": "registry",
            "chain": [
                {"step": "input_normalized", "source_ref": "context.readiness"},
                {"step": "registry_checked", "tool_name": "context.readiness", "matched": true},
                {"step": "resolved", "source_type": "tool", "resolver": "registry"}
            ]
        },
        "source_refs": [
            {"ref": "resolver:registry", "type": "resolver"},
            {"ref": "tool:context.readiness", "type": "tool"}
        ],
        "confidence": 1.0,
        "warnings": [],
        "stale": false,
        "tombstone": false
    },
    "metadata": {
        "include_chain": true,
        "resolution_mode": "repo_registry_only"
    }
}
```

### 7.4 context.package

```python
result = bridge.execute_tool("context.package", {
    "artifacts": [
        "context.readiness",
        "docs/runbooks/surrealdb_context_mcp_access.md"
    ],
    "format": "json",
    "include_metadata": True
})
```

Response (ok):
```json
{
    "tool": "context.package",
    "status": "ok",
    "package": {
        "format": "json",
        "items": [
            {
                "id": "context.readiness",
                "type": "tool",
                "summary": "Registry tool context.readiness",
                "source_refs": ["tool:context.readiness"],
                "confidence": null,
                "freshness": null,
                "metadata": {
                    "read_only": true,
                    "handler_status": "implemented"
                }
            },
            {
                "id": "docs/runbooks/surrealdb_context_mcp_access.md",
                "type": "file",
                "summary": "Repo file docs/runbooks/surrealdb_context_mcp_access.md",
                "source_refs": ["path:docs/runbooks/surrealdb_context_mcp_access.md"],
                "confidence": null,
                "freshness": null,
                "metadata": {
                    "repo_relative_path": "docs/runbooks/surrealdb_context_mcp_access.md"
                }
            }
        ],
        "created_at": null,
        "package_id": "pkg_<deterministic_hash_prefix>",
        "warnings": [],
        "stale_flags": [],
        "missing_context": [],
        "source_refs": [
            "path:docs/runbooks/surrealdb_context_mcp_access.md",
            "tool:context.readiness"
        ],
        "stop_conditions": [
            "no_live_go",
            "no_echtgeld_authorization",
            "no_risk_approval"
        ],
        "metadata": {
            "include_metadata": true,
            "scope": "default",
            "truncated": false,
            "total_requested": 2,
            "total_resolved": 2,
            "total_missing": 0,
            "resolver": "repo-registry"
        }
    }
}
```

Artifacts are capped at 10 items (truncation warning added). Missing/non-list/empty artifacts returns `invalid_artifacts`. The package is repo-/registry-only: it does not read or write SurrealDB, does not create persistent handoff records, and does not imply Live-Go/LR.

### 7.5 context.readiness

**Example: Read-only review:**

```python
result = bridge.execute_tool("context.readiness", {
    "task_scope": "review risk service documentation",
    "operation_mode": "read_only",
    "stop_conditions": ["S10"],
    "required_reads": [
        "AGENTS.md",
        "agents/AGENTS.md",
        "agents/OPEN_CODE_AGENTS.md",
        "docs/runbooks/CONTROL_REGISTER.md",
        "CURRENT_STATUS.md",
        "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"
    ]
})
```

Response:
```json
{
    "tool": "context.readiness",
    "status": "ok",
    "readiness": {
        "status": "ready_for_read_only",
        "reasons": ["Read-only scope, no writes required."],
        "required_next_reads": [],
        "human_go_required": false,
        "stop_conditions": ["S10"],
        "missing_context": [],
        "missing_evidence": [],
        "scope_drift_findings": [],
        "uncertainties": [],
        "guardrails": [
            "No writes. No issue comments. No PR creation.",
            "Readiness is not authorization. LR remains NO-GO. Board stage (trade-capable) is orthogonal."
        ]
    }
}
```

**Example: Write without evidence:**

```python
result = bridge.execute_tool("context.readiness", {
    "task_scope": "fix order handler precision bug",
    "operation_mode": "write (code/docs)",
    "target_paths": ["services/execution/order_handler.py"],
    "required_reads": [
        "AGENTS.md", "agents/AGENTS.md", "agents/OPEN_CODE_AGENTS.md",
        "docs/runbooks/CONTROL_REGISTER.md", "CURRENT_STATUS.md",
        "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"
    ],
    "impact_refs": ["services/execution/", "services/risk/"],
    "evidence_refs": [],  # Missing evidence
    "stop_conditions": ["S7: execution scope"]
})
```

Response (blocked):
```json
{
    "tool": "context.readiness",
    "status": "ok",
    "readiness": {
        "status": "blocked_missing_evidence",
        "reasons": ["Missing evidence for core assumptions"],
        "required_next_reads": [],
        "human_go_required": true,
        "stop_conditions": ["S4: core assumptions lack evidence", "S7: execution scope"],
        "missing_context": [],
        "missing_evidence": ["write operation without evidence refs"],
        "scope_drift_findings": [],
        "uncertainties": [],
        "guardrails": [
            "Do not proceed. Evidence is missing.",
            "Readiness is not authorization. LR remains NO-GO. Board stage (trade-capable) is orthogonal."
        ]
    }
}
```

### 7.6 context.briefing

```python
result = bridge.execute_tool("context.briefing", {
    "task_id": "task_review_001",
    "target_issue": None,
    "task_scope": "review risk governance documentation",
    "requested_depth": "quick",
    "operation_mode": "read_only"
})
```

Response includes `briefing_id` (16-char hex, deterministic), `scope_summary`, `required_reads`, `guardrails` (7 mandatory), `stop_conditions`, `validation_plan`, `human_go_required`. Depths: `quick` (summary only), `standard` (with artifacts), `deep` (with mock uncertainty warnings). If `target_issue` is omitted it defaults to `null`; if `requested_depth` is omitted it defaults to `quick`.

`briefing.session_context` is the canonical short-term/session-memory handoff surface for Context/MCP work. It is always `working_memory` with `session_only=true`, remains read-only, and must not be treated as persistent SurrealDB memory. `brain_source` / `brain_status` are derived, not trusted from caller claims:

- `adapter_config_path` (+ `secrets_path` when required by the config) triggers a real Wave-14 trust-summary read through the existing adapter layer. Only `metadata.source="surrealdb-local"` enables DB-backed briefing claims.
- Inline `evidence_records` / `claim_records` / `decision_events` / `memory_records` derive `brain_source="in_memory"` with `db_claims_allowed=false`.
- No DB path and no inline records derive `brain_source="repo-only"` and `brain_status="not-used"`.
- Caller-supplied `brain_source` / `brain_status` are ignored and surfaced only as limitations when present.

### 7.7 Local Wave-14 `surrealdb-local` Proof Smoke

The committed fixture slice for the real local proof lives under:

- `tests/fixtures/surrealdb/wave14_real_smoke/evidence_refs.jsonl`
- `tests/fixtures/surrealdb/wave14_real_smoke/claims.jsonl`
- `tests/fixtures/surrealdb/wave14_real_smoke/agent_memories.jsonl`
- `tests/fixtures/surrealdb/wave14_real_smoke/decision_events.jsonl`

These four files are the only committed seed artifacts. The local-only smoke test
materializes the remaining importer bundle files as empty temp files at runtime,
because `tools.surrealdb.context_importer` fail-closes when any expected JSONL
artifact is missing.

Hard preflight before any real DB-backed Wave-14 claim:

```powershell
Invoke-WebRequest http://127.0.0.1:8010/health
Invoke-WebRequest http://127.0.0.1:8010/version
Test-Path infrastructure/config/surrealdb/context_query.local.yaml
[bool]$env:CDB_CONTEXT_SECRETS_PATH
[bool]$env:SECRETS_PATH
```

Fail-closed rules:

- If `/health` or `/version` is not `200`, stop.
- If `infrastructure/config/surrealdb/context_query.local.yaml` is missing, run
  `make context-query-config-init` first; stop if that init fails.
- Resolve secrets dir in this order (never print the path, check existence only):
  - `CDB_CONTEXT_SECRETS_PATH` if set (override)
  - `SECRETS_PATH` if set (canon)
  - Windows default: `%USERPROFILE%\Documents\.secrets\.cdb` (canon)
  - Linux/Mac default: `$HOME/Documents/.secrets/.cdb` (canon)
- If no secrets dir resolves, or if `SURREALDB_ENV` is missing inside it, stop.
- If only `context_query.local.example.yaml` exists and init was not run, status
  stays `BLOCKED_NEEDS_AUTH_CONFIG`.
- Never print secret file contents. The smoke only checks the config path and the
  presence of env flags and required secret file existence.

Opt-in execution:

```powershell
$env:CDB_RUN_REAL_SURREALDB_SMOKE = "1"
pytest -v tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py
pytest -v tests/unit/tools/mcp/test_context_bridge.py
pytest -v -m local_only tests/local/tools/mcp/test_wave14_real_surrealdb_smoke.py
```

What the local smoke does:

1. Re-checks the same preflight gates and skips fail-closed if they are missing.
2. Generates a unique `run_id` per invocation (`{timestamp}-{pid}` by default, or
   optional override via `CDB_WAVE14_SMOKE_RUN_ID`).
3. Materializes run-scoped record IDs from the four committed seed files (for example
   `ev-wave14-real-{run_tag}-001`) without mutating committed fixtures.
4. Asserts pre-import that run-scoped IDs and `.tmp/wave14-real-smoke/{run_id}` are
   absent; fails closed if stale records remain.
5. Builds a temporary full JSONL bundle from the materialized Wave-14 seed records.
6. Applies that bundle to the local Context DB through the existing importer using:
   - `--adapter surrealdb-local`
   - `--apply --apply-mode local-dev`
   - `--config infrastructure/config/surrealdb/context_import.local.example.yaml`
   - explicit `--secrets-path`
7. Calls all six Wave-14 MCP handlers with:
   - `adapter_config_path=infrastructure/config/surrealdb/context_query.local.yaml`
   - `secrets_path=<resolved secrets dir>` (see resolution order above; `CDB_CONTEXT_SECRETS_PATH` is an override, not a new default)
8. Asserts for each tool:
   - `status == "ok"`
   - `metadata.source == "surrealdb-local"`
   - `metadata.read_only == true`
   - expected result payload is non-empty
   - no secret-like auth values are echoed back
9. Cleans up only the run-scoped DB record IDs and removes
   `.tmp/wave14-real-smoke/{run_id}` after the module finishes; repeated local runs
   must not accumulate stale rows or temp artifacts.

This smoke is `local_only`, opt-in via `CDB_RUN_REAL_SURREALDB_SMOKE=1`, and is not
part of CI by default.

Tool coverage in the real local smoke:

- `cdb_context_memory_get` → seeded `agent_memory`
- `cdb_context_evidence_resolve` → seeded `evidence_ref`
- `cdb_context_claim_resolve` → seeded `claim`
- `cdb_context_trust_summary` → seeded `evidence_ref` + `claim` + `agent_memory` + `decision_event`
- `cdb_context_decision_history` → seeded `decision_event`
- `cdb_context_decision_replay` → seeded `decision_event`

### 7.8 Wave-15–20 Closure Proof Policy

Wave-14 tools that may emit `metadata.source="surrealdb-local"` have a documented real local
DB proof path in §7.7 (#2639, #2649, #2650). **Wave-15–20 tools do not use
`SurrealDBLocalQueryAdapter` and do not open a SurrealDB connection.** They are bundle-driven
adapters over in-memory domain services; default bridge mode remains `NoopQueryAdapter` /
`in_memory`. Caller-supplied `metadata.source` or `brain_*` fields are not DB proof (#2638).

**Closure rule for Wave-15–20:** `closure_without_real_db_proof_allowed` when handler wiring,
unit-test evidence, and this runbook policy are satisfied. **Do not** require §7.7 local DB
smoke for Wave-15–20 closure. If a future change adds adapter-backed reads or
`surrealdb-local` claims to any Wave-15–20 handler, stop and open a follow-up slice with an
explicit `real_db_proof_required_before_closure` policy before marking the tool complete.

| Tool | Wave | Purpose | Closure policy | DB-backed claims | Required closure evidence |
|------|------|---------|----------------|------------------|---------------------------|
| `cdb_context_contradictions` | 15 | Detect contradictions across in-memory record bundles (signal only; no auto-fix). | `closure_without_real_db_proof_allowed` | No — `metadata.source` stays `in_memory`; no adapter path. | Handler: `tools/mcp/context_contradiction_tools.py`; unit: `tests/unit/tools/mcp/test_mcp_contradiction_tool.py`; bridge/guard registration; this §7.8 row. |
| `cdb_context_stale` | 16 | Scan stale knowledge markers in a supplied bundle (artifact/decision/evidence/memory/edge scopes). | `closure_without_real_db_proof_allowed` | No — bundle input required; fails closed without bundle. | Handler: `tools/mcp/stale_context_tools.py`; unit: `tests/unit/tools/mcp/test_mcp_stale_context_tool.py`; bridge/guard registration; this §7.8 row. |
| `cdb_context_scope_drift` | 17 | Detect scope-drift firewall findings from an in-memory bundle; optional blocking output. | `closure_without_real_db_proof_allowed` | No — bundle input required; no filesystem/DB backfill. | Handler: `tools/mcp/scope_drift_tools.py`; unit: `tests/unit/tools/mcp/test_scope_drift_tools.py`; bridge/guard registration; this §7.8 row. |
| `cdb_context_quality_score` | 18 | Score knowledge-quality dimensions from an in-memory bundle. | `closure_without_real_db_proof_allowed` | No — `metadata.source="in_memory"` only. | Handler: `tools/mcp/quality_scoring_tools.py`; unit: `tests/unit/tools/mcp/test_quality_scoring_tools.py` + domain tests in `tests/unit/surrealdb/test_quality_scoring.py`; bridge/guard registration; this §7.8 row. |
| `cdb_context_architect_signals` | 18 | Emit architect signals (watch/blocking) from bundle dependency/quality inputs. | `closure_without_real_db_proof_allowed` | No — bundle input required; no DB/network. | Handler: `tools/mcp/architect_signal_tools.py`; domain unit: `tests/unit/surrealdb/test_quality_scoring.py` (architect signal cases); bridge/guard registration; this §7.8 row. Optional local DB smoke: **not required**. |
| `cdb_control_room_view` | 19 | Build read-only control-room views (9 view types) from an in-memory bundle. | `closure_without_real_db_proof_allowed` | No — no runtime/trading console; bundle-only. | Handler: `tools/mcp/control_room_tools.py`; unit: `tests/unit/tools/mcp/test_control_room_tools.py` + `tests/unit/surrealdb/test_control_room_view_builder.py`; bridge/guard registration; this §7.8 row. |
| `cdb_agent_os_readiness` | 20 | Evaluate Agent OS readiness level and optional markdown report from a bundle. | `closure_without_real_db_proof_allowed` | No — bundle-only; no Live-Go/Echtgeld semantics. | Handler: `tools/mcp/agent_os_readiness_tools.py`; unit: `tests/unit/tools/mcp/test_agent_os_readiness_tools.py` + `tests/unit/surrealdb/test_agent_os_readiness.py`; bridge/guard registration; this §7.8 row. |

**Wave-15–20 validation (CI-safe, no Real-DB smoke):**

```bash
pytest tests/unit/tools/mcp/test_context_bridge.py tests/unit/tools/mcp/test_permission_guard.py \
  tests/unit/tools/mcp/test_mcp_wave14_tools.py \
  tests/unit/tools/mcp/test_mcp_contradiction_tool.py tests/unit/tools/mcp/test_mcp_stale_context_tool.py \
  tests/unit/tools/mcp/test_scope_drift_tools.py tests/unit/tools/mcp/test_quality_scoring_tools.py \
  tests/unit/tools/mcp/test_control_room_tools.py tests/unit/tools/mcp/test_agent_os_readiness_tools.py -v
python -c "from tools.mcp.context_bridge import create_bridge; b=create_bridge(); assert len(b.list_tools())==27; assert all(t.get('readOnly') for t in b.list_tools())"
```

**HOLD gap (none for current handlers):** No Wave-15–20 handler currently emits guarded
`surrealdb-local` claims. If implementation drifts to adapter-backed reads, treat as
`real_db_proof_required_before_closure` and block #2605 epic closure until a Wave-14-style
proof slice lands.

### Memory contract DB read proof (#2606 Slice 4)

Separate opt-in gate for contract-compliant `agent_memory` rows (not the pre-contract Wave-14 fixture):

```powershell
$env:CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE = "1"
pytest -v -m local_only tests/local/surrealdb/test_memory_db_read_proof.py
```

Requires the same local SurrealDB preflight as Wave-14 (`context_query.local.yaml`, secrets, `127.0.0.1:8010` health). Not part of CI by default.

Deterministic repo-only example with explicit session state inputs:

```python
result = bridge.execute_tool("context.briefing", {
    "task_id": "task_review_2607",
    "target_issue": "#2607",
    "task_scope": "review session-context handoff behavior",
    "requested_depth": "quick",
    "operation_mode": "read_only",
    "repo_state": {
        "branch": "fix/2613-noise-freeze-remaining-push-triggers",
        "commit": "f345cf0c",
        "working_tree": "dirty"
    },
    "github_state": {
        "target_issue": "#2607",
        "related_prs": [],
        "open_epics": ["#2607"]
    },
    "working_assumptions": [
        "repo-only verification is sufficient for this handoff"
    ]
})
```

Expected abbreviated output:

```json
{
  "tool": "context.briefing",
  "status": "ok",
  "briefing": {
    "session_context": {
      "memory_type": "working_memory",
      "session_only": true,
      "ttl_seconds": 14400,
      "brain_source": "repo-only",
      "brain_status": "not-used",
      "repo_state": {
        "branch": "fix/2613-noise-freeze-remaining-push-triggers",
        "commit": "f345cf0c",
        "working_tree": "dirty"
      },
      "github_state": {
        "target_issue": "#2607",
        "related_prs": [],
        "open_epics": ["#2607"]
      },
      "agent_operating_mode": {
        "operation_mode": "read_only",
        "human_go_required": false,
        "db_claims_allowed": false
      },
      "working_assumptions": [
        "repo-only verification is sufficient for this handoff"
      ]
    }
  }
}
```

Brain Evidence mapping from `briefing.session_context`:

- `brain_source <- briefing.session_context.brain_source`
- `brain_status <- briefing.session_context.brain_status`
- `tools_or_queries <- caller-provided MCP/tool reads or, if absent, conservative session limitations`
- `records_or_results <- briefing.session_context.repo_state + briefing.session_context.github_state`
- `repo_crosscheck <- briefing.session_context.repo_state + briefing.required_reads + request target paths/symbols when present`
- `impact_on_plan <- briefing.session_context.working_assumptions + briefing.session_context.limitations`
- `limitations <- briefing.session_context.limitations`

Canonical Brain Evidence block derived from the example above:

```text
## Brain Evidence
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - context.briefing(task_review_2607)
  - repo-only verification is sufficient for this handoff
records_or_results:
  - branch=fix/2613-noise-freeze-remaining-push-triggers
  - commit=f345cf0c
  - working_tree=dirty
  - target_issue=#2607
  - related_prs=[]
  - open_epics=[#2607]
repo_crosscheck:
  - briefing.required_reads
  - branch=fix/2613-noise-freeze-remaining-push-triggers
  - commit=f345cf0c
impact_on_plan:
  - repo-only verification is sufficient for this handoff
  - repo-only brain source; no DB-backed memory or evidence claims
limitations:
  - repo-only brain source; no DB-backed memory or evidence claims
```

### #2607 Short-Term Session Context Acceptance

- Structured `session_context` preserves `branch`, `commit`, and `working_tree` when caller-provided.
- Issue/PR state can be handed off through `github_state` (`target_issue`, `related_prs`, `open_epics`).
- `working_assumptions` are temporary session hints only because `session_only=true`.
- `ttl_seconds` is bounded to `<= 14400` (4h) for this MCP handoff surface.
- `repo-only` and `in_memory` are not DB-backed and must keep `db_claims_allowed=false`.
- Persistent Brain or memory claims require a real adapter-backed read that returns `metadata.source="surrealdb-local"`; briefing fails closed when DB-backed mode is requested but config/auth/adapter source cannot prove that path.
- `session_context` does not authorize any automatic long-term memory write or persistent DB write.
- A full Brain Evidence block can be generated from `briefing.session_context` plus the sibling briefing fields such as `required_reads`.

### 7.7 context.stop_resolver

```python
result = bridge.execute_tool("context.stop_resolver", {
    "stop_conditions": ["S7", "S8"],
    "operation_mode": "write (code/docs)"
})
```

Resolved entries include `type`, `severity` (`warning`/`blocking`), `reason`, `required_action`, `human_go_required`. S7 severity depends on operation mode.

### 7.8 context.required_reads

```python
result = bridge.execute_tool("context.required_reads", {
    "task_scope": "review risk limits",
    "target_issue": None,
    "operation_mode": "read_only"
})
```

Resolves through 7 layers: minimum baseline, domain-specific, issue-driven, path-driven, symbol-driven, concept-driven, and write-mode governance reads. Each resolved read has `path`, `priority` (`must_read`, `should_read`, `may_read`), `reason`, `source_ref`, `available`, and optional `warning`.

---

## 8. Readiness Check Deep Dive

### 8.1 Status Values

| Status | Meaning |
|--------|---------|
| `ready_for_read_only` | Agent may read files, search code, and analyze context. No writes of any kind are permitted. |
| `ready_for_dry_run` | Agent may simulate, plan, diff, or generate previews. No write without explicit Human-GO. |
| `ready_for_human_go` | Agent has sufficient context to proceed but MUST stop and request explicit Human-GO before any write. |
| `blocked_missing_context` | Execution blocked. One or more required inputs are missing. |
| `blocked_missing_evidence` | Execution blocked. One or more core assumptions lack committed evidence. |
| `blocked_scope_drift` | Execution blocked. Requested task diverges from defined scope or scope is ambiguous. |

Status derivation is deterministic: same inputs produce same status.

### 8.2 Operation Modes

| Mode | Description |
|------|-------------|
| `read_only` | Read files, search code, analyze context. No writes. |
| `dry_run` | Plan, simulate, preview. No writes without Human-GO. |
| `write (code/docs)` | Write to repo files (documentation, test code). |
| `write (config/infra)` | Write configuration or infrastructure files. |
| `write (DB/migration)` | Write database migrations or DB state. |
| `write (MCP live)` | Live MCP action (e.g. PR creation, issue comment). |

Invalid or missing `operation_mode` returns `blocked_missing_context`. Any `write` mode sets `human_go_required: true`.

### 8.3 Minimum Required Reads

Every readiness assessment requires these files present:
- `AGENTS.md`
- `agents/AGENTS.md`
- `agents/OPEN_CODE_AGENTS.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `CURRENT_STATUS.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`

Missing any of these produces `blocked_missing_context` with specific stop conditions.

---

## 9. Stop Conditions and Human-GO

### 9.1 Stop Conditions (S1–S10)

| Code | Severity | Description |
|------|----------|-------------|
| S1 | blocking | Task scope is missing, empty, or ambiguous. |
| S2 | blocking | No Context Package and no required reads. |
| S3 | blocking | One or more minimum required reads are unavailable. |
| S4 | blocking | Core assumptions lack evidence. |
| S5 | blocking | Scope does not match defined targets. |
| S6 | blocking | Write operation without impact report. |
| S7 | blocking (write) / warning (read_only) | Task touches trading/risk/execution surface. |
| S8 | blocking | Live/Echtgeld/production claims outside LR SSOT. |
| S9 | warning | Contradiction risk — conflicting evidence or signals. |
| S10 | warning | STOP signal encountered in canonical control surfaces. |

### 9.2 Human-GO Rules (H1–H5)

| Code | Description |
|------|-------------|
| H1 | Any `write` operation mode requires Human-GO. |
| H2 | Runtime surface touched (docker, deploy, secrets). |
| H3 | Secrets rotation or write. |
| H4 | GitHub control-plane mutation (PR merge, issue close). |
| H5 | Trading/risk/execution state change. |

Even when `status: ready_for_human_go`, the agent MUST stop and wait for explicit human approval. Readiness is not authorization.

---

## 10. Troubleshooting

| Symptom | Error Code | Cause | Action |
|---------|------------|-------|--------|
| `"unknown_tool"` | `unknown_tool` | Tool name not in registry | Check spelling. Use `bridge.list_tool_names()`. |
| `"not_implemented"` | `not_implemented` | Tool handler scaffold placeholder | The target tool is still wired to a scaffold handler. Use `context.show_audit` to audit `handler_status` and confirm wiring, then stop and report which tool remains stubbed. |
| `"invalid_query"` | `invalid_query` | Missing, empty, or non-string query | Provide a non-empty string in the `query` field. |
| `"invalid_artifacts"` | `invalid_artifacts` | Missing or non-list artifacts | Provide a non-empty list of artifact ID strings. |
| `"invalid_parameters"` | `invalid_parameters` | Parameters not a dict | Pass parameters as `dict`, not list/string/int. |
| `"forbidden_keyword"` | `forbidden_keyword` | SQL/SurrealQL mutation keyword in query params | Remove INSERT, UPDATE, DELETE, etc. from query text. |
| `"forbidden_query_pattern"` | `forbidden_query_pattern` | Mutation query pattern detected | Remove SQL/SurrealQL write statements from parameters. |
| `"forbidden_runtime_operation"` | `forbidden_runtime_operation` | Runtime operation keyword in query tool params | Avoid git/docker/deploy keywords in scan-tool parameters. |
| `"blocked_missing_context"` | (readiness check) | Missing required inputs | Add missing required_reads, stop_conditions, or impact_refs. |
| `"blocked_scope_drift"` | (readiness check) | Task scope diverges from targets | Narrow scope or update stop conditions. |
| `"blocked_missing_evidence"` | (readiness check) | Write operation without evidence_refs | Supply evidence references before proceeding. |

---

## 11. References

| Resource | Path |
|----------|------|
| Context Tool Contracts v0 | `docs/surrealdb/context-tool-contracts-v0.md` |
| Context Tool Contracts v1 | `docs/surrealdb/context-tool-contracts-v1.md` |
| Action Readiness Contract | `docs/surrealdb/context-action-readiness-contract.md` |
| Context Import Runbook | `docs/runbooks/surrealdb_context_import.md` |
| Context Query Runbook | `docs/runbooks/surrealdb_context_query.md` |
| MCP Bridge (source) | `tools/mcp/context_bridge.py` |
| MCP Registry (source) | `tools/mcp/registry.py` |
| Permission Guard (source) | `tools/mcp/permission_guard.py` |
| Bridge Tests | `tests/unit/tools/mcp/test_context_bridge.py` |
| Permission Guard Tests | `tests/unit/tools/mcp/test_permission_guard.py` |
| Package Handler Tests | `tests/unit/tools/mcp/test_context_package_handler.py` |
| Context Package v2 Model | `docs/surrealdb/context-package-model-v2.md` |
| Context Package v2 Builder Tests | `tests/unit/surrealdb/test_context_package_v2.py` |
| Output Contract Tests | `tests/unit/tools/mcp/test_output_contracts.py` |
| Control Register | `docs/runbooks/CONTROL_REGISTER.md` |

---

## 12. Clearances and Verdict

| Item | Status |
|------|--------|
| LR Verdict | **NO-GO** (unchanged) |
| Board Stage | `trade-capable` (orthogonal) |
| Echtgeld | Not authorized |
| Write Path | Disabled (three-layer defense) |
| Runtime/MCP Live | Not authorized |
| Memory Write | Not authorized |

---

## 13. Closing Reminder

- All examples use **mocked/in-memory responses**. No real SurrealDB is contacted.
- The three-layer defense (Registry + Execute + Input gates) blocks writes at every level.
- The bridge returns **fail-closed**: invalid input returns `status: "error"` with an agent-readable error code.
- Live-Readiness remains **NO-GO**. Wave 12 completion does not change Echtgeld posture.
- `ready_for_human_go` is a status, not a permission. Agents MUST stop and wait for explicit Human-GO.
