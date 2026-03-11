# CODEX – Context Core Verification

## ROLE
You are CODEX, the deterministic verification agent for the project **Claire de Binare**.

## MISSION
Verify the **Context Core** (not only the Docker stack) against ground truth in the repositories.
This is a **read-only verification**. You MUST NOT modify any files.

The Context Core defines what every agent must load to avoid architectural,
governance, and operational mistakes.

---

## AUTHORITATIVE INPUTS

### Docs Repository (Context Core)
- knowledge/ARCHITECTURE_MAP.md
- governance/SERVICE_CATALOG.md
- knowledge/GOVERNANCE_QUICKREF.md
- knowledge/SYSTEM_INVARIANTS.md
- knowledge/OPERATIONS_RUNBOOK.md
- knowledge/CURRENT_STATUS.md

### Working Repository
- docker-compose.base.yml
- infrastructure/compose/base.yml
- infrastructure/compose/dev.yml
- infrastructure/compose/prod.yml
- infrastructure/compose/tls.yml

### Scripts
- stack_up.ps1
- infrastructure/scripts/stack_up.ps1
- infrastructure/scripts/stack_verify.ps1

### Code
- services/** (Dockerfiles, entrypoints, service code)

---

## VERIFICATION TASKS

### 1. CONTEXT CORE COMPLETENESS
Verify that all Context Core files exist and are referenced where required:
- AGENTS.md autoload list
- CLAUDE.md session-start rules

Flag any missing or unreferenced file as **MUST FIX**.

---

### 2. SERVICES – SOLL vs REALITY
For every service listed in:
- ARCHITECTURE_MAP.md
- SERVICE_CATALOG.md

Verify:
- Compose service exists OR
- Explicitly marked as non-container/module

Flag any:
- Code/Dockerfile without compose entry
- Compose service without catalog entry

---

### 3. GOVERNANCE & SAFETY CONTRACTS
Verify that:
- GOVERNANCE_QUICKREF.md reflects actual write-gates and forbidden zones
- SYSTEM_INVARIANTS.md do not contradict compose, scripts, or code behavior
- No Context Core rule conflicts with DELIVERY_APPROVED.yaml semantics

---

### 4. OPERATIONS & VERIFICATION
Verify that:
- OPERATIONS_RUNBOOK.md commands exist and match scripts
- Healthcheck and verification steps are executable
- stack_verify.ps1 enforces SERVICE_CATALOG consistency

---

## OUTPUT (FINAL REPORT ONLY)

### VERDICT
PASS / PASS WITH WARNINGS / FAIL

### MUST FINDINGS
Blocking inconsistencies or missing context

### SHOULD FINDINGS
Important but non-blocking gaps

### EVIDENCE TABLE
| Claim | Evidence (file path + line/section) | Status |

### DRIFT LIST
| Severity | Description | Location | Impact |

### NEXT ACTIONS
Actionable steps (no code).

---

## HARD RULES
- No file edits.
- No commits or PRs.
- No assumptions without marking **UNVERIFIED**.

---

## VERIFICATION REPORT (CODEX)

### VERDICT
FAIL

### MUST FINDINGS
- Context Core Service Catalog path mismatch: AGENTS/CLAUDE require `governance/SERVICE_CATALOG.md` in Docs Hub, but the file exists only in the Working Repo at `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\governance\SERVICE_CATALOG.md`.
- Delivery Gate semantics conflict: Quickref example uses top-level `approved`/`mode`, while the canonical gate uses `delivery.approved`.
- Authoritative inputs list is stale: `docker-compose.base.yml` and root `stack_up.ps1` are listed but do not exist.

### SHOULD FINDINGS
- Healthcheck invariant requires compose healthchecks, but `cdb_risk` and `cdb_execution` in `dev.yml` lack healthcheck blocks.
- Signal port drift: Dockerfile/README still use 8001, while compose sets 8005.
- ARCHITECTURE_MAP known drifts list `cdb_core` for prod/tls and 8001 in CLAUDE, but prod/tls now use `cdb_signal` and CLAUDE lists 8005.
- Logging version drift: catalog lists Loki/Promtail 2.9.0 while compose uses 2.9.3.
- dev.yml comment says Market service has no `service.py`, but `services/market/service.py` exists.
- stack_up.ps1 still comments a `cdb_signal` GAP even though compose defines it.

### EVIDENCE TABLE
| Claim | Evidence (file path + line/section) | Status |
| --- | --- | --- |
| AGENTS/CLAUDE require Docs Hub Service Catalog | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\agents\AGENTS.md:159`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\agents\CLAUDE.md:9` | FAIL |
| Service Catalog exists in Working Repo | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\governance\SERVICE_CATALOG.md:1` | FAIL |
| Quickref uses top-level approved/mode | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\GOVERNANCE_QUICKREF.md:32`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\GOVERNANCE_QUICKREF.md:36` | FAIL |
| Canonical gate uses delivery.approved | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\governance\DELIVERY_APPROVED.yaml:18` | FAIL |
| Inputs list legacy docker-compose.base.yml | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\context_build\CODEX_CONTEXT_CORE_VERIFICATION.md:26`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\LEGACY_FILES.md:275` | FAIL |
| Inputs list root stack_up.ps1 | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\context_build\CODEX_CONTEXT_CORE_VERIFICATION.md:33` | FAIL |
| Healthcheck invariant vs dev.yml | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\SYSTEM_INVARIANTS.md:89`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\dev.yml:83` | WARN |
| Signal port drift Dockerfile vs compose | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\services\signal\Dockerfile:32`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\dev.yml:67` | WARN |
| ARCHITECTURE_MAP known drifts outdated | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\ARCHITECTURE_MAP.md:140`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\prod.yml:59` | WARN |
| Logging version drift | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\governance\SERVICE_CATALOG.md:45`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\logging.yml:7` | WARN |
| Market comment vs code | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\dev.yml:185`; `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\services\market\service.py:37` | WARN |
| stack_up.ps1 comment says cdb_signal GAP | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\scripts\stack_up.ps1:101` | WARN |

### DRIFT LIST
| Severity | Description | Location | Impact |
| --- | --- | --- | --- |
| HIGH | Service Catalog not in Docs Hub | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\agents\AGENTS.md:159` | Autoload/Context Core breaks |
| HIGH | Delivery Gate schema mismatch | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\GOVERNANCE_QUICKREF.md:32` | Governance/CI ambiguity |
| HIGH | Stale inputs listed | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\context_build\CODEX_CONTEXT_CORE_VERIFICATION.md:26` | Verification list not reliable |
| MEDIUM | Signal port/name drift (cdb_core/8001) | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\services\signal\Dockerfile:32` | Ops/monitoring targets wrong |
| MEDIUM | Healthcheck invariant vs compose | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\knowledge\SYSTEM_INVARIANTS.md:89` | Health status inconsistent |
| LOW | Logging image version drift | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\logging.yml:7` | Doc vs runtime mismatch |
| LOW | Market service comment mismatch | `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\infrastructure\compose\dev.yml:185` | Confusing enablement notes |

### NEXT ACTIONS
- Decide canonical location for Service Catalog, then align AGENTS/CLAUDE/ARCHITECTURE_MAP and the actual file path.
- Unify Delivery Gate schema (Quickref + canonical gate + CI).
- Update verification inputs list to remove legacy files or reintroduce wrappers.
- Resolve signal port/name drift across Dockerfile/README/ops scripts.
- Align healthcheck policy (add compose healthchecks or adjust invariant wording).
