# Logs Concept Analysis: logs/ vs. Docs Hub logs/

**Date:** 2025-12-27
**Purpose:** Decision basis for conceptual separation between runtime logs and knowledge artifacts
**Scope:** Read-only analysis (no decision made)
**Related Issue:** #124

---

## Executive Summary

**Current State:**
- **Two** distinct `logs/` directories exist across repositories
- **Working Repo** `logs/`: Runtime operational logs (4.3 MB, 10+ active log files)
- **Docs Hub** `logs/`: Knowledge artifacts (archived reports, session notes)
- **Overlap:** Both contain paper trading logs, creating ambiguity

**Key Finding:** Conceptual separation exists but is **not enforced** or **documented**

**Analysis Scope:**
- Directory structure and file types surveyed
- Comparison table created (Purpose, Canon Status, Audience, Contents)
- 3 target models documented with pros/cons
- **No recommendation made** (decision-ready, not decided)

---

## Survey: Current Usage

### Working Repo: logs/

**Location:** `Claire_de_Binare/logs/`
**Total Size:** ~4.3 MB (10 files + subdirectories)

**Directory Structure:**
```
logs/
├── agent_runs/           # Agent execution reports (JSON + Markdown)
│   ├── 3dc4b1143cf442ba/
│   │   ├── report.json
│   │   └── report.md
│   └── ... (6 runs total)
├── events/               # Event logs in JSONL format
│   ├── events_20251219.jsonl
│   ├── events_20251220.jsonl
│   └── ... (4 days)
├── infra/                # Infrastructure logs
├── services/             # Service-specific logs
├── paper_trading_20251219.log  # Operational paper trading logs
├── paper_trading_20251220.log  #  (5 files, Dec 19-27)
└── ... (5 log files total)
```

**File Types:**
| Extension | Count | Purpose | Typical Size |
|-----------|-------|---------|--------------|
| `.log` | 5 | Plain text operational logs | 24 KB - 2 MB |
| `.jsonl` | 4 | Structured event logs | ~200 KB/day |
| `.json` | 6 | Agent run reports (structured) | ~10 KB |
| `.md` | 6 | Agent run reports (human-readable) | ~15 KB |

**Purpose:** Runtime operational logs (ephemeral, rotated, not canonical)

**Target Audience:**
- Developers debugging live system
- Automated monitoring tools (Prometheus, Loki)
- Operational incident response

**Retention:** Implicit (no documented policy), appears to be ~7-14 days

---

### Docs Hub: logs/

**Location:** `Claire_de_Binare_Docs/logs/`
**Total Size:** ~6.5 KB (3 files + subdirectories)

**Directory Structure:**
```
logs/
├── audits/               # Historical audit logs (empty)
├── daily_reports/        # Daily operational summaries
│   └── report_20251214.md
├── paper_trading_20251213.log  # Archived paper trading log
├── README.md             # Directory purpose documentation
├── runs/                 # Historical run logs (empty)
├── sessions/             # Development session notes
│   └── execution-service-development-oct2025.md
├── system/               # System check outputs (empty)
├── systemcheck_20251214_212322.log  # Archived system check
├── trading/              # Trading-related logs (empty)
└── weekly_reports/       # Weekly summaries
    ├── weekly_report_20251216.md
    └── weekly_report_TEMPLATE.md
```

**File Types:**
| Extension | Count | Purpose | Typical Size |
|-----------|-------|---------|--------------|
| `.md` | 4 | Human-readable reports/summaries | ~2 KB |
| `.log` | 2 | Archived operational logs | ~2-4 KB |

**Purpose:** Knowledge artifacts (canonical, archived, historical)

**Target Audience:**
- Stakeholders reviewing historical performance
- Future developers onboarding to project
- Compliance/audit purposes

**Retention:** Permanent (canonical knowledge base)

---

## Comparison Table

| Aspect | Working Repo logs/ | Docs Hub logs/ |
|--------|-------------------|----------------|
| **Purpose** | Operational runtime logs | Knowledge artifacts / historical records |
| **Canon Status** | Non-canonical (ephemeral) | Canonical (permanent) |
| **Target Audience** | Developers, ops engineers, monitoring tools | Stakeholders, future devs, compliance |
| **Typical Contents** | Live service logs, events, debug output | Reports, summaries, archived logs, session notes |
| **Retention Policy** | Implicit rotation (~7-14 days) | Permanent (or explicit archive policy) |
| **Update Frequency** | Real-time (continuous) | Batch (daily/weekly summaries) |
| **File Size** | Large (MB), unbounded | Small (KB), curated |
| **Format** | Raw logs (`.log`, `.jsonl`) | Reports (`.md`), selected logs |
| **Git Tracking** | `.gitignore` (excluded) | Tracked (versioned) |
| **Write Permissions** | Services, agents (automated) | Agents, humans (curated) |
| **Access Pattern** | Recent access (last 7 days) | Historical access (months/years) |
| **Search Method** | grep, Loki, log aggregation | Git grep, full-text search |

---

## Overlap & Ambiguity

### Identified Overlaps

1. **Paper Trading Logs**
   - **Working Repo:** `paper_trading_20251219.log` to `paper_trading_20251227.log` (5 files, 4.3 MB)
   - **Docs Hub:** `paper_trading_20251213.log` (1 file, ~2 KB)
   - **Question:** Should archived paper trading logs move to Docs Hub?

2. **System Check Logs**
   - **Working Repo:** Not currently present (but likely generated)
   - **Docs Hub:** `systemcheck_20251214_212322.log`
   - **Question:** Where should future system checks be logged?

3. **Agent Run Reports**
   - **Working Repo:** `agent_runs/` (JSON + Markdown reports)
   - **Docs Hub:** No current storage (but session notes exist)
   - **Question:** Should agent runs be archived to Docs Hub after completion?

---

## Target Models

### Model A: Clear Separation (Runtime vs. Knowledge)

**Principle:** Strict separation based on lifecycle (ephemeral vs. canonical)

**Rules:**
- **Working Repo `logs/`:** Runtime logs only (continuous writes, auto-rotated, never committed)
- **Docs Hub `logs/`:** Knowledge artifacts only (curated reports, archived logs, versioned)
- **Migration:** Operational logs older than 14 days automatically archived to Docs Hub (selected, not all)

**Directory Structure:**

**Working Repo:**
```
logs/
├── services/              # Service logs (auto-rotated)
│   ├── risk/
│   ├── execution/
│   └── core/
├── events/                # Event streams (JSONL, auto-rotated)
├── infra/                 # Infrastructure logs (Redis, Postgres)
└── .rotation_policy.yml   # Retention rules (14 days default)
```

**Docs Hub:**
```
logs/
├── archived_logs/         # Selected operational logs (historical value)
│   ├── 2025-12/          # Monthly archive
│   │   ├── paper_trading_20251219.log (if noteworthy)
│   │   └── incident_20251220_circuit_breaker.log
│   └── README.md         # What gets archived and why
├── daily_reports/         # Daily summaries (auto-generated)
├── weekly_reports/        # Weekly summaries (auto-generated)
├── sessions/              # Development session notes (manual)
└── audits/                # Compliance audit logs
```

**Advantages:**
- ✅ Clear mental model (runtime vs. knowledge)
- ✅ No confusion about where to write
- ✅ Disk space managed (working repo stays small)
- ✅ Git history focused on knowledge (not noise)
- ✅ Automated archival possible (cron job or agent)

**Risks:**
- ⚠️ Archival automation required (adds complexity)
- ⚠️ Selection criteria needed (what logs are worth archiving?)
- ⚠️ Breaking change (existing logs need migration)
- ⚠️ Two places to search for logs (recent = working repo, old = Docs Hub)

**Impact on Agents:**
- Agents write runtime logs to **Working Repo `logs/`**
- Agents write reports/summaries to **Docs Hub `logs/`**
- Archive agent runs weekly archival job (selects noteworthy logs for Docs Hub)

---

### Model B: Consolidation (Single Location)

**Principle:** All logs (runtime + knowledge) in one location (Working Repo)

**Rules:**
- **Working Repo `logs/`:** All logs (runtime + knowledge artifacts)
- **Docs Hub `logs/`:** Deprecated (moved to Working Repo)
- **Retention:** Explicit `.gitignore` rules for ephemeral logs, track knowledge artifacts

**Directory Structure:**

**Working Repo:**
```
logs/
├── runtime/               # Ephemeral logs (.gitignore'd)
│   ├── services/
│   ├── events/
│   └── infra/
├── knowledge/             # Knowledge artifacts (tracked in git)
│   ├── daily_reports/
│   ├── weekly_reports/
│   ├── sessions/
│   └── audits/
└── README.md              # Clear rules: runtime vs. knowledge
```

**Advantages:**
- ✅ Single location (no ambiguity)
- ✅ Easier to search (one place)
- ✅ No cross-repo synchronization
- ✅ Simpler mental model (all logs together)

**Risks:**
- ⚠️ Git repo size grows (knowledge artifacts tracked)
- ⚠️ Disk cleanup harder (must distinguish runtime vs. knowledge in same tree)
- ⚠️ `.gitignore` complexity (track knowledge/, ignore runtime/)
- ⚠️ Violates "Working Repo = code only" principle (adds knowledge artifacts)

**Impact on Agents:**
- Agents write to **Working Repo `logs/runtime/`** (ephemeral)
- Agents write to **Working Repo `logs/knowledge/`** (canonical)
- Simpler (one location), but Working Repo becomes heavier

---

### Model C: Status Quo with Explicit Rules

**Principle:** Keep current structure, document rules clearly

**Rules:**
- **Working Repo `logs/`:** Runtime logs (documented, `.gitignore`'d)
- **Docs Hub `logs/`:** Knowledge artifacts (documented, versioned)
- **Documentation:** Add README.md to Working Repo `logs/` explaining separation
- **Policy:** Explicit rules for what goes where (documented in both READMEs)

**Directory Structure:**

**Working Repo:**
```
logs/
├── README.md              # NEW: Purpose, audience, retention policy
├── services/
├── events/
├── infra/
└── paper_trading_YYYYMMDD.log
```

**Docs Hub:**
```
logs/
├── README.md              # UPDATED: Clarify relationship to Working Repo logs/
├── daily_reports/
├── weekly_reports/
└── sessions/
```

**Advantages:**
- ✅ No breaking changes (minimal disruption)
- ✅ Clear rules via documentation
- ✅ Keeps existing workflows intact
- ✅ Quick to implement (2 README files)

**Risks:**
- ⚠️ Relies on human discipline (agents must follow rules)
- ⚠️ Overlap still possible (paper trading logs in both places)
- ⚠️ No enforcement (documentation can be ignored)
- ⚠️ Ambiguity persists (where do archived logs go?)

**Impact on Agents:**
- Agents follow documented rules (Working Repo = runtime, Docs Hub = knowledge)
- Requires agent prompt updates (reference README.md for guidance)
- Risk: Agents may violate rules if not explicitly enforced

---

## Decision Criteria (for Stakeholders)

| Criterion | Model A (Separation) | Model B (Consolidation) | Model C (Status Quo + Docs) |
|-----------|---------------------|------------------------|----------------------------|
| **Clarity** | High | Medium | Low-Medium |
| **Enforcement** | High (automation) | Medium (gitignore) | Low (documentation only) |
| **Breaking Change** | Yes (migration) | Yes (repo restructure) | No |
| **Disk Management** | Easy (auto-rotation) | Medium (manual cleanup) | Current state |
| **Search Complexity** | Medium (2 locations) | Low (1 location) | Current state |
| **Git Repo Size** | Optimal (knowledge only) | Grows (knowledge artifacts) | Current state |
| **Implementation Effort** | High (1-2 sessions) | Medium (1 session) | Low (30 min) |
| **Agent Impact** | Medium (new rules) | Medium (new structure) | Low (prompt update) |
| **Long-Term Maintenance** | Low (automated) | Medium (manual) | High (human discipline) |

---

## Open Questions (for Decision-Maker)

1. **Retention Policy:** How long should operational logs be kept in Working Repo before archival/deletion?
   - Suggested: 14 days (configurable)

2. **Archive Selection:** Which logs are worth archiving to Docs Hub?
   - Suggested: Incidents, paper trading results, compliance audit logs

3. **Automation:** Should archival be automated or manual?
   - Model A requires automation (cron job or agent)
   - Model C relies on manual curation

4. **Breaking Changes:** Is repo restructure acceptable?
   - Model A & B require migration
   - Model C preserves current structure

5. **Git Repo Size:** Should knowledge artifacts be tracked in Working Repo or Docs Hub?
   - Model A: Docs Hub (separate concern)
   - Model B: Working Repo (single location)
   - Model C: Docs Hub (current state)

---

## Recommendations Framework (Not a Decision)

**If priority is CLARITY:**
→ Model A (Clear Separation)

**If priority is SIMPLICITY:**
→ Model B (Consolidation)

**If priority is MINIMAL DISRUPTION:**
→ Model C (Status Quo + Docs)

**If priority is LONG-TERM MAINTAINABILITY:**
→ Model A (Clear Separation with automation)

**If priority is QUICK IMPLEMENTATION:**
→ Model C (Status Quo + Docs, 30 min)

---

## Next Steps (Decision-Dependent)

**If Model A selected:**
1. Create `.rotation_policy.yml` in Working Repo `logs/`
2. Implement archival agent (weekly cron job)
3. Migrate existing logs to Docs Hub (select noteworthy logs)
4. Update agent prompts (runtime vs. knowledge rules)
5. Document in both README.md files

**If Model B selected:**
1. Create `logs/runtime/` and `logs/knowledge/` in Working Repo
2. Update `.gitignore` (ignore runtime/, track knowledge/)
3. Move Docs Hub logs/ to Working Repo logs/knowledge/
4. Update agent prompts (single location, clear subdirectory rules)
5. Document in Working Repo logs/README.md

**If Model C selected:**
1. Create `logs/README.md` in Working Repo
2. Update `logs/README.md` in Docs Hub (clarify relationship)
3. Update agent prompts (reference README for guidance)
4. Document explicit rules (where to write what)

---

## Audit Methodology

**Tools Used:**
- `ls -la` for directory structure survey
- `find` for file type inventory
- Manual review of README.md (Docs Hub logs/)

**Files Reviewed:**
- Working Repo `logs/`: 10 files + 4 subdirectories
- Docs Hub `logs/`: 3 files + 6 subdirectories

**Time Spent:** 30 minutes

---

## Related Documentation

- Docs Hub `logs/README.md`: Purpose statement (knowledge artifacts)
- `.gitignore` (Working Repo): Logs exclusion pattern

---

**Status:** ✅ ANALYSIS COMPLETE (Decision-Ready)
**Created:** 2025-12-27
**Analyst:** Claude (Automated Analysis)
**Decision Required:** Yes (Stakeholder must select model)
