# Documentation Hierarchy & Guidelines

**Created**: 2025-11-21
**Status**: Active
**Purpose**: Define clear documentation structure and prevent redundancy

---

## 🎯 Single Source of Truth

**→ [`PROJECT_STATUS.md`](../PROJECT_STATUS.md)** ← **CANONICAL STATUS DOCUMENT**

This document is the **authoritative source** for:
- Current system status
- Active blockers & priorities
- Recent achievements
- Metrics & KPIs
- Next steps

**Rule**: When in doubt about project status, check `PROJECT_STATUS.md` first.

---

## 📁 Documentation Structure

### **Level 1: Repository Root**

**Purpose**: Entry points and essential project documents only.

**Allowed files**:
- `README.md` - Project overview & quick start
- `CLAUDE.md` - KI-Agent protocol (instructions for Claude)
- `ROADMAP.md` - Project roadmap & milestones
- `MILESTONES_README.md` - GitHub milestones documentation
- `.env.example` - Environment template
- `requirements.txt`, `requirements-dev.txt` - Dependencies
- Configuration files (`.gitignore`, `docker-compose.yml`, etc.)

**NOT allowed**:
- ❌ Status reports (→ `backoffice/docs/reports/`)
- ❌ Technical documentation (→ `backoffice/docs/`)
- ❌ Database docs (→ `backoffice/docs/database/`)
- ❌ Analysis documents (→ `backoffice/docs/analysis/`)

---

### **Level 2: backoffice/**

**Purpose**: Central documentation hub.

```
backoffice/
├── PROJECT_STATUS.md        ← 🔴 SINGLE SOURCE OF TRUTH
└── docs/                    ← All documentation
```

**Key file**: `PROJECT_STATUS.md`
- Current status, blockers, achievements
- Updated after every significant change
- Referenced by all other documents

---

### **Level 3: backoffice/docs/**

**Purpose**: Organized documentation by category.

```
backoffice/docs/
├── architecture/           ← System design documents
├── services/               ← Service-specific docs
├── testing/                ← Test documentation
├── runbooks/               ← Operational procedures
├── security/               ← Security docs
├── database/               ← Database docs
├── reports/                ← Status reports & summaries
├── analysis/               ← Code analysis
├── knowledge/              ← Knowledge extraction
├── provenance/             ← Audit trails
├── schema/                 ← Data schemas
├── DECISION_LOG.md         ← Architecture Decision Records
├── KODEX – Claire de Binare.md  ← Project principles
├── ISSUES_BACKLOG.md       ← Active issues & priorities
└── CI_CD_GUIDE.md          ← CI/CD pipeline documentation
```

---

## 📋 Document Categories & Rules

### **1. Architecture Documents** (`architecture/`)

**Purpose**: System design, architecture decisions, diagrams.

**Examples**:
- `N1_ARCHITEKTUR.md` - N1 phase architecture
- `SYSTEM_FLUSSDIAGRAMM.md` - Event flow diagrams

**Rules**:
- Must be versioned (N1, N2, etc.)
- Must include diagrams where applicable
- Must reference ADRs (in `DECISION_LOG.md`)

---

### **2. Service Documentation** (`services/`)

**Purpose**: Service-specific documentation, APIs, data flows.

**Examples**:
- `SERVICE_DATA_FLOWS.md` - Data flow patterns
- `RISK_ENGINE_SPEC.md` - Risk engine specification

**Rules**:
- One document per service or cross-service pattern
- Must include event types, data schemas
- Must reference architecture docs

---

### **3. Testing Documentation** (`testing/`)

**Purpose**: Test strategies, guides, reports.

**Examples**:
- `TESTING_GUIDE.md` - Complete testing guide
- `LOCAL_E2E_TESTS.md` - E2E test documentation
- `CI_CD_TROUBLESHOOTING.md` - CI/CD troubleshooting

**Rules**:
- Must be kept up-to-date with test changes
- Must include examples and commands
- Reports (completion, summaries) go to `reports/`

---

### **4. Runbooks** (`runbooks/`)

**Purpose**: Operational procedures, playbooks, workflows.

**Examples**:
- `CLAUDE_GORDON_WORKFLOW.md` - Claude → Gordon workflow
- `DEPLOYMENT_PLAYBOOK.md` - Deployment procedures

**Rules**:
- Must be step-by-step instructions
- Must include prerequisites and validation steps
- Must be executable without prior knowledge

---

### **5. Security Documentation** (`security/`)

**Purpose**: Security policies, hardening guides, audit reports.

**Examples**:
- `HARDENING.md` - Security hardening guide
- `SECURITY_AUDIT_2025-11.md` - Security audit report

**Rules**:
- Must follow security best practices
- No secrets or credentials
- Must include remediation steps

---

### **6. Database Documentation** (`database/`)

**Purpose**: Database schemas, migrations, analysis.

**Examples**:
- `DATABASE_SCHEMA.sql` - PostgreSQL schema
- `DATABASE_READINESS_REPORT.md` - DB readiness report
- `DATABASE_TRACKING_ANALYSIS.md` - Data tracking analysis

**Rules**:
- Schema must be versioned
- Migrations must be documented
- Reports include performance metrics

---

### **7. Reports & Summaries** (`reports/`)

**Purpose**: Status reports, completion summaries, session notes.

**Examples**:
- `COMPLETION_SUMMARY.md` - CI/CD completion summary
- `PR_BODY.md` - Pull request template
- `SESSION_SUMMARY_2025-11-20.md` - Session summary
- `E2E_PAPER_TEST_REPORT.md` - E2E test completion report

**Rules**:
- Must include date in filename (YYYY-MM-DD)
- Reports are **snapshots** (not updated after creation)
- For current status, refer to `PROJECT_STATUS.md`

**Naming Convention**:
```
<TYPE>_<SUBJECT>_<DATE>.md
COMPLETION_SUMMARY_2025-11-21.md
SESSION_SUMMARY_2025-11-20.md
```

---

### **8. Analysis Documents** (`analysis/`)

**Purpose**: Code analysis, technical reviews, investigations.

**Examples**:
- `risk_engine_todo_analysis.md` - Risk engine TODO analysis
- `performance_bottleneck_analysis.md` - Performance analysis

**Rules**:
- Must include methodology
- Must have clear conclusions
- Must link to relevant code

---

### **9. Decision Log** (`DECISION_LOG.md`)

**Purpose**: Architecture Decision Records (ADRs).

**Format**:
```markdown
## ADR-XXX: Decision Title

**Datum**: YYYY-MM-DD
**Status**: ✅ Akzeptiert / 🟡 Vorgeschlagen / ❌ Abgelehnt
**Verantwortlicher**: Name

### Kontext
[Problem description]

### Entscheidung
[Decision made]

### Konsequenzen
[Positive, Neutral, Negative consequences]

### Alternativen
[Considered alternatives]

### Compliance
[KODEX, Standards compliance]
```

**Rules**:
- ADRs are numbered sequentially
- Decisions are immutable (create new ADR to supersede)
- Must follow standard format

---

### **10. Issue Backlog** (`ISSUES_BACKLOG.md`)

**Purpose**: Active issues, blockers, priorities.

**Format**:
```markdown
### Issue #X: Title
**Status**: 🔴/🟡/🟢
**Priorität**: P0/P1/P2/P3
**Effort**: X hours

**Beschreibung**:
[Description]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2

**Remote machbar**: ✅/🟡/❌
```

**Rules**:
- Issues numbered sequentially (#1, #2, etc.)
- Must include priority and effort
- Must specify if remote-executable
- Closed issues archived, not deleted

---

## 🚫 Anti-Patterns to Avoid

### **1. Status Duplication**

❌ **DON'T**: Create multiple status documents
```
SYSTEM_STATUS.md          ← Duplicate
PROJECT_STATUS.md         ← Duplicate
CURRENT_STATUS.md         ← Duplicate
```

✅ **DO**: Use single source of truth
```
backoffice/PROJECT_STATUS.md  ← Only this
```

### **2. Orphaned Documents**

❌ **DON'T**: Leave documents without clear purpose
```
notes.md
temp_analysis.md
untitled.md
```

✅ **DO**: Every document has a category
```
backoffice/docs/analysis/risk_engine_analysis.md
backoffice/docs/reports/SESSION_2025-11-20.md
```

### **3. Root Clutter**

❌ **DON'T**: Put everything in root
```
/
├── analysis1.md
├── report1.md
├── notes.md
├── TODO.md
```

✅ **DO**: Organize by category
```
/backoffice/docs/
├── analysis/analysis1.md
├── reports/report1.md
```

### **4. Unclear Naming**

❌ **DON'T**: Generic names
```
doc.md
file1.md
new.md
```

✅ **DO**: Descriptive names
```
DATABASE_READINESS_REPORT.md
RISK_ENGINE_TODO_ANALYSIS.md
SESSION_SUMMARY_2025-11-20.md
```

---

## ✅ Document Lifecycle

### **Creating New Documents**

1. **Choose category** (architecture, services, testing, etc.)
2. **Use descriptive name** (SUBJECT_TYPE_DATE.md)
3. **Include metadata**:
   ```markdown
   **Created**: YYYY-MM-DD
   **Status**: Draft/Active/Archived
   **Purpose**: [One-line description]
   ```
4. **Add to README.md** if essential

### **Updating Documents**

1. **Living documents** (TESTING_GUIDE.md):
   - Update in place
   - Add "Last Updated" timestamp

2. **Snapshots** (reports):
   - Never update after creation
   - Create new document for new status

3. **PROJECT_STATUS.md**:
   - Update after every significant change
   - Always includes date/version

### **Archiving Documents**

1. **When to archive**:
   - Document outdated
   - Superseded by newer document
   - No longer relevant

2. **How to archive**:
   - Move to `backoffice/docs/archive/YYYY/`
   - Add note in original location pointing to archive

---

## 📊 Document Review Checklist

Before committing any documentation:

- [ ] Document is in correct category
- [ ] Filename follows naming convention
- [ ] Metadata included (Created, Status, Purpose)
- [ ] Links to related documents work
- [ ] Referenced in README.md (if essential)
- [ ] No duplicate information
- [ ] No secrets or credentials
- [ ] Markdown linting passes

---

## 🔄 Migration from Old Structure

**Completed**: 2025-11-21

**Actions taken**:
1. ✅ Created `reports/`, `database/`, `analysis/` directories
2. ✅ Moved 7 report files to `reports/`
3. ✅ Moved 4 database files to `database/`
4. ✅ Moved 1 analysis file to `analysis/`
5. ✅ Moved `ISSUES_BACKLOG.md` to `docs/`
6. ✅ Updated `README.md` with new structure
7. ✅ Established `PROJECT_STATUS.md` as SSOT

**Result**:
- Root: 4 essential files (was 15)
- Docs: Organized in 9 categories
- Clear hierarchy established

---

## 📞 Questions?

**Where does document X go?**
- Check categories above
- Follow naming convention
- When in doubt: `reports/` for snapshots, `docs/` for living documents

**How to reference other documents?**
- Use relative paths: `[Link](../architecture/N1_ARCHITEKTUR.md)`
- Always test links

**What's the difference between PROJECT_STATUS.md and reports?**
- `PROJECT_STATUS.md`: **Current** status (updated regularly)
- `reports/`: **Historical** snapshots (never updated)

---

**Maintainer**: Claude (AI Assistant)
**Last Updated**: 2025-11-21
**Version**: 1.0
