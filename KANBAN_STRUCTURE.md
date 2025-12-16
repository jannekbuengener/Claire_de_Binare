# Kanban Structure — CDB Project Management

**Status:** Active  
**Owner:** CDB_GITHUB_MANAGER  
**Last Updated:** 2025-12-16

---

## Board Structure

### Column Flow

```
Backlog → Ready → In Progress → Review → Done
```

**Backlog:**
- New issues (auto-created)
- Ideas / proposals
- Not yet prioritized
- **Label:** `status:backlog` (optional)

**Ready:**
- Acceptance criteria clear
- Dependencies resolved
- Assigned to milestone
- **Label:** `status:ready`

**In Progress:**
- Actively worked on
- Assignee set
- Updates expected
- **Label:** (none, inferred from assignee)

**Review:**
- PR created
- Awaiting review/approval
- CI must be green
- **Label:** `status:in-review`

**Done:**
- Merged to main
- Tests pass
- Documented
- **Closed:** Yes

---

## Issue Workflow

### 1. Creation (Backlog)
- User creates issue via template
- Auto-labeled (type/scope/prio)
- Appears in Backlog column

### 2. Triage (Backlog → Ready)
**Who:** Session Lead (Claude) / Product Owner  
**Actions:**
- Validate scope
- Assign milestone
- Assign priority
- Add `status:ready` label

### 3. Assignment (Ready → In Progress)
**Who:** Developer / Agent  
**Actions:**
- Self-assign or assigned by lead
- Remove `status:ready`
- Start work
- Move to "In Progress"

### 4. Review (In Progress → Review)
**Who:** Developer  
**Actions:**
- Create PR
- Link issue with "Closes #XX"
- Add `status:in-review` label
- Request reviewers

### 5. Merge (Review → Done)
**Who:** Reviewer / Lead  
**Actions:**
- CI green
- Review approved
- Merge PR
- Issue auto-closed
- Moved to "Done"

---

## Label-Based Automation

### Auto-Move Rules

**Backlog → Ready:**
- Trigger: `status:ready` label added
- Action: Move to "Ready" column

**Ready → In Progress:**
- Trigger: Assignee added
- Action: Move to "In Progress"

**In Progress → Review:**
- Trigger: `status:in-review` label added
- Action: Move to "Review" column

**Review → Done:**
- Trigger: Issue closed
- Action: Move to "Done" column

---

## Milestone-Specific Views

### M1 - GitHub & CI Baseline
**Focus:** Repository structure, CI/CD foundation  
**Target:** Complete (baseline)

### M2 - Infra & Security Hardening
**Focus:** Docker, secrets, network isolation  
**Target:** Q1 2026

### M3 - Risk Layer
**Status:** 2 closed issues  
**Target:** Complete

### M4 - Automation & Observability
**Focus:** Monitoring, dashboards, alerting  
**Issues:** #96 (Grafana Dashboards)  
**Target:** Q1 2026

### M5 - Persistenz
**Focus:** Database, event-store, replay  
**Issues:** #43 (Bug: query_analytics.py)  
**Target:** Q4 2025

### M6 - Docker
**Status:** Clean (0 open issues)  
**Target:** Complete

### M7 - Testnet (Paper Trading)
**Focus:** E2E tests, performance baselines  
**Issues:** Epic #91 + Sub-Issues #92-#94  
**Target:** Q1 2026

### M8 - Production Hardening & Security
**Focus:** Penetration testing, incident response, OWASP audit  
**Issues:** #95 (Resilience) + #97-#105 (Security)  
**Target:** Q2 2026

### M9 - Release 1.0
**Focus:** Final security sign-off, production deployment  
**Target:** Q2 2026

---

## Priority Lanes

### Swim Lane 1: Critical (prio:must)
- **Color:** Red
- **SLA:** Start within 24h
- **Examples:**
  - #94 E2E Paper Trading Tests (P0)
  - #97 Container Security Scanning
  - #100 Network Isolation

### Swim Lane 2: High (prio:should)
- **Color:** Orange
- **SLA:** Start within 1 week
- **Examples:**
  - #92 Paper Trading Research
  - #93 Performance Baselines
  - #96 Grafana Dashboards

### Swim Lane 3: Nice (prio:nice)
- **Color:** Green
- **SLA:** Best effort
- **Examples:**
  - #95 Resilience Tests

---

## Filters & Views

### View 1: All Issues
- Shows: All open issues
- Columns: Backlog, Ready, In Progress, Review
- Sort: Priority (must → should → nice)

### View 2: By Milestone
- Group by: Milestone (M1-M9)
- Shows: Status distribution per milestone
- Use: Roadmap planning

### View 3: By Type
- Group by: type:bug / type:feature / type:security / type:testing
- Shows: Work distribution by type
- Use: Capacity planning

### View 4: Security Focus
- Filter: `label:type:security OR label:scope:security`
- Shows: All security-related items
- Use: M8 Security Roadmap tracking

### View 5: My Work
- Filter: `assignee:@me`
- Shows: User's assigned issues
- Use: Personal task list

---

## WIP Limits

**Per Person:**
- Max 3 issues "In Progress" simultaneously
- Prevents context switching
- Encourages focus

**Per Column:**
- **Backlog:** Unlimited
- **Ready:** Max 20 (forces prioritization)
- **In Progress:** Max 10 (team capacity)
- **Review:** Max 5 (review bottleneck indicator)
- **Done:** Unlimited

---

## Metrics & Health

### Lead Time
**Definition:** Backlog → Done  
**Target:** <14 days (average)

### Cycle Time
**Definition:** In Progress → Done  
**Target:** <7 days (average)

### Throughput
**Definition:** Issues closed per week  
**Target:** 5-10 issues/week (stable velocity)

### WIP Ratio
**Definition:** In Progress / Ready  
**Target:** <0.5 (more ready than active)

### Review Time
**Definition:** PR created → Merged  
**Target:** <24 hours (critical), <48 hours (normal)

---

## Automation Hooks

### Stale Bot
- Issues inactive 90d → `stale` label
- Stale + 14d → Auto-close
- PRs inactive 90d → `stale` label
- Stale PR + 7d → Auto-close

### Auto-Label
- Keywords in title/body → Auto-label
- `bug` → `type:bug`
- `feature` → `type:feature`
- `security` → `type:security`

### Auto-Assign
- Issue labeled `scope:infra` → Assign to Infrastructure Team
- Issue labeled `scope:ci` → Assign to CI/CD Maintainer
- (Requires team definitions in GitHub)

### PR Checks
- CI must pass (lint, test, security)
- At least 1 approval required
- No merge without green CI

---

## Templates & Conventions

### Issue Title Format
```
[Type] Scope: Brief Description
```

**Examples:**
- `[Bug] Analytics: query_analytics.py crashes at line 222`
- `[Feature] Monitoring: Grafana Dashboard for Risk Metrics`
- `[Security] Infra: Container Image Scanning with Trivy`

### PR Title Format
```
type(scope): brief description
```

**Examples:**
- `fix(analytics): handle missing data in query_analytics.py`
- `feat(monitoring): add Grafana risk metrics dashboard`
- `security(infra): implement Trivy container scanning`

### Commit Message Format
```
type(scope): imperative verb + what changed

- Bullet point details
- Another detail

Closes #42
```

---

## Board Access & Permissions

### Public (Team)
- View all columns
- Create issues
- Comment on issues
- Self-assign to "Ready" issues

### Maintainers
- Move issues between columns
- Edit labels/milestones
- Merge PRs
- Close issues

### Admins
- Archive projects
- Change board settings
- Manage automation

---

## References

- GitHub Projects Documentation: https://docs.github.com/en/issues/planning-and-tracking-with-projects
- Kanban Guide: https://www.atlassian.com/agile/kanban
- CDB Governance: `CDB_GOVERNANCE.md`

---

**Status:** 🚀 **ACTIVE**  
**Next Review:** Monthly (first Monday)
