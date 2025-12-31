# Architecture Design: PR Review & Labeling Optimization (Issue #144)

**Document Version:** 1.0
**Date:** 2025-12-27
**Issue Reference:** #144
**Foundation:** Issue #145 (Smart PR Auto-Labeling System - COMPLETED)
**Role:** system-architect

---

## Executive Summary

This document outlines the architecture for **blocking PR checks and enforcement mechanisms** that build upon the smart labeling foundation from Issue #145. The goal is to prevent PRs with governance violations from being merged while maintaining developer velocity and avoiding unnecessary blockage.

**Key Principles:**
- **Fork-safe:** All checks must work securely with pull_request_target
- **Non-blocking MVP:** Phase 1 uses informational checks; blocking comes in Phase 2
- **Configurable:** All rules defined in YAML for easy maintenance
- **Incremental:** Builds on existing #145 infrastructure without breaking changes

---

## 1. System Overview

### 1.1 Current State (Issue #145 - COMPLETED)

```
┌─────────────────────────────────────────────────────────┐
│  PR Event (opened, synchronize, edited, etc.)          │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  .github/workflows/pr-auto-label.yml                    │
│  (pull_request_target - fork-safe)                      │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  .github/scripts/pr_auto_label.py                       │
│  - Analyzes files changed                               │
│  - Applies labels (area, type, priority, size, review)  │
│  - Detects governance violations                        │
│  - Posts informational comment if violations found      │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Configuration: .github/pr-labels.yml                    │
│  - area_labels, title_labels                            │
│  - governance.rules                                      │
│  - size.thresholds                                       │
│  - review.draft_label/ready_label                       │
└─────────────────────────────────────────────────────────┘

OUTPUTS:
✓ Labels applied automatically
✓ Governance violations flagged with comment
✗ No blocking mechanism
✗ No reviewer assignment
✗ No merge enforcement
```

### 1.2 Target State (Issue #144 - THIS DESIGN)

```
┌─────────────────────────────────────────────────────────┐
│  PR Event                                                │
└───────┬─────────────────────────────────┬───────────────┘
        │                                 │
        ▼                                 ▼
┌───────────────────┐           ┌─────────────────────────┐
│ pr-auto-label.yml │           │ pr-governance-check.yml │
│ (EXISTING #145)   │           │ (NEW - BLOCKING)        │
│ - Apply labels    │           │ - Enforce rules         │
│ - Detect issues   │           │ - Set check status      │
│ - Comment         │           │ - Block if needed       │
└─────────┬─────────┘           └──────────┬──────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│         pr-reviewer-assignment.yml (NEW)                 │
│         - Auto-assign reviewers based on labels          │
│         - Respect CODEOWNERS                             │
│         - Add to review queue                            │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│  Branch Protection Rules (GitHub Settings)               │
│  - Require "Governance Check" status                     │
│  - Require "PR Template Check" status                    │
│  - Require N reviewers (based on labels/size)            │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Component Design

### 2.1 New Workflow: `pr-governance-check.yml`

**Purpose:** Blocking status check for governance violations and PR template compliance

**Trigger:**
```yaml
on:
  pull_request_target:
    types: [opened, reopened, synchronize, edited, ready_for_review]
```

**Jobs:**

#### Job 1: `governance-enforcement`
- **Reads:** PR labels (applied by #145)
- **Checks:** If `governance:review-required` label exists
- **Action:**
  - ✅ PASS if no governance label
  - ⚠️ WARN if governance label + has reviewer approval
  - ❌ FAIL if governance label + no approval override
- **Override mechanism:** Special comment `/governance-override @maintainer-name` (requires maintainer permissions)

#### Job 2: `pr-template-check`
- **Reads:** PR body
- **Checks:** Required template sections present
- **Action:**
  - ✅ PASS if all sections present
  - ❌ FAIL if missing required sections
- **Reuses:** Existing `branch-policy.yml` logic (lines 83-116)

#### Job 3: `size-gate`
- **Reads:** `size:*` label
- **Checks:** PR size against configured thresholds
- **Action:**
  - ✅ PASS if size <= L
  - ⚠️ WARN if size = XL (requires extra reviewer)
  - ❌ FAIL if size = XL + no justification comment

**Configuration:** Extends `.github/pr-labels.yml` with new `enforcement` section

### 2.2 New Workflow: `pr-reviewer-assignment.yml`

**Purpose:** Auto-assign reviewers based on labels and CODEOWNERS

**Trigger:**
```yaml
on:
  pull_request:
    types: [opened, reopened, ready_for_review]
  pull_request_target:
    types: [labeled]
```

**Logic:**
1. Read PR labels (from #145)
2. Match labels to reviewer mapping in config
3. Respect CODEOWNERS for path-based reviews
4. Avoid duplicate assignments
5. Add reviewers via GitHub API
6. Post comment with reviewer rationale

**Reviewer Mapping (in `.github/pr-labels.yml`):**
```yaml
reviewer_assignment:
  enabled: true
  mappings:
    - labels: ["area:ci", "area:infra"]
      reviewers: ["@maintainers"]
    - labels: ["governance:review-required"]
      reviewers: ["@maintainers"]
      required_count: 2
    - labels: ["size:XL"]
      additional_reviewers: 1
```

### 2.3 New Script: `.github/scripts/pr_governance_check.py`

**Purpose:** Blocking check logic separated from labeling logic

**Key Functions:**
```python
def check_governance_status() -> bool:
    """Returns True if PR passes governance check"""
    labels = get_pr_labels()
    if "governance:review-required" not in labels:
        return True

    # Check for override comment
    if has_governance_override():
        return True

    return False

def check_template_compliance() -> bool:
    """Returns True if PR template is complete"""
    pr_body = get_pr_body()
    required_sections = load_required_sections()
    return all(section in pr_body for section in required_sections)

def check_size_gate() -> bool:
    """Returns True if PR size is acceptable"""
    labels = get_pr_labels()
    if "size:XL" in labels:
        # Check for justification comment
        return has_size_justification()
    return True

def set_check_status(check_name: str, state: str, description: str):
    """Set GitHub check run status"""
    # Uses Checks API to set blocking status
```

**Exit Codes:**
- `0` = PASS (green check)
- `1` = FAIL (red X, blocks merge)
- `78` = NEUTRAL (yellow dot, informational)

### 2.4 Configuration Extension: `.github/pr-labels.yml`

**New Section:**
```yaml
enforcement:
  enabled: true

  # Governance enforcement
  governance_blocking: false  # MVP: false, Phase 2: true
  governance_override_command: "/governance-override"
  governance_override_permissions: ["write", "admin"]

  # Template enforcement
  template_blocking: true
  required_sections:
    - "## Feature Overview"
    - "## Technical Overview"
    - "## Test Evidence"
    - "## Code Quality"
    - "## Deployment & Rollback"
    - "## Documentation"
    - "## Agent Approvals"

  # Size enforcement
  size_blocking: false  # MVP: false, Phase 2: true
  xl_requires_justification: true
  xl_justification_command: "/size-xl-justified"

# Reviewer assignment (NEW)
reviewer_assignment:
  enabled: true
  respect_codeowners: true

  mappings:
    - labels: ["area:ci", "area:infra", ".github"]
      reviewers: ["@maintainers"]
      required_count: 1

    - labels: ["governance:review-required"]
      reviewers: ["@maintainers"]
      required_count: 2

    - labels: ["area:core", "area:services"]
      reviewers: ["@maintainers"]
      required_count: 1

    - labels: ["size:XL"]
      additional_reviewers: 1

    - labels: ["priority:high"]
      reviewers: ["@maintainers"]
      required_count: 1
```

---

## 3. Implementation Phases

### Phase 1: MVP (Non-Blocking Informational)

**Goal:** Gather data, validate rules, avoid blocking developers unnecessarily

**Duration:** 2-4 weeks

**Components:**
1. ✅ **pr-governance-check.yml** - Always returns success, posts warnings
2. ✅ **pr-reviewer-assignment.yml** - Auto-assigns reviewers (non-blocking)
3. ✅ **pr_governance_check.py** - Validation logic ready
4. ✅ **Configuration** - `enforcement.governance_blocking: false`

**Success Criteria:**
- No false positives in governance detection
- Reviewer assignments working correctly
- Zero developer complaints about broken workflow
- Metrics: 90%+ PRs have correct labels and reviewers

**Metrics to Collect:**
- Governance violation detection accuracy
- False positive rate
- Reviewer assignment relevance
- PR merge time impact

### Phase 2: Blocking Enforcement (After MVP validation)

**Goal:** Enable blocking for validated rules

**Prerequisites:**
- Phase 1 metrics show <5% false positive rate
- Team agrees on governance rules
- Rollback plan tested

**Changes:**
1. **Configuration change:**
   ```yaml
   enforcement:
     governance_blocking: true
     size_blocking: true
   ```

2. **Branch protection update:**
   - Require "Governance Check" status
   - Require "PR Template Check" status

3. **Monitoring:**
   - Alert if >10% PRs blocked
   - Weekly review of blocked PRs

**Rollback Strategy:**
- Single config change to disable blocking
- GitHub branch protection can be toggled via UI
- Workflow disable via GitHub Actions UI

### Phase 3: Advanced Features (Future)

**Post-MVP enhancements:**
- Auto-merge for qualifying PRs
- Smart reviewer rotation
- Integration with external review tools
- ML-based label suggestion
- Automated governance exception tracking

---

## 4. Integration with Existing Systems

### 4.1 Integration with Issue #145 (pr-auto-label.yml)

**No Changes Required:**
- #145 workflow remains untouched
- Runs independently and labels PRs
- #144 workflows consume those labels

**Dependency:**
- #144 workflows wait for labels to be applied
- Use `needs: []` to ensure label job completes first

### 4.2 Integration with CI Pipeline (ci.yaml)

**Relationship:**
- CI checks (lint, test, security) run independently
- Governance checks run in parallel
- All must pass for merge

**No Conflicts:**
- Different trigger events
- Different permissions
- Different exit criteria

### 4.3 Integration with Branch Policy (branch-policy.yml)

**Reuse:**
- Template check logic from lines 83-116
- Extract to shared script if needed

**Coordination:**
- Both enforce branch naming
- Both check PR template
- Governance check adds blocking capability

### 4.4 Integration with CODEOWNERS

**Enhancement:**
- Reviewer assignment respects CODEOWNERS
- Adds label-based reviewers ON TOP of CODEOWNERS
- Does not replace or override CODEOWNERS

**Logic:**
```
Final Reviewers = CODEOWNERS + Label-based + Size-based
```

---

## 5. Risk Assessment and Mitigation

### Risk 1: False Positives Blocking Valid PRs

**Likelihood:** HIGH (especially in Phase 2)
**Impact:** HIGH (developer frustration, velocity loss)

**Mitigation:**
- Phase 1 is non-blocking (data collection)
- Override commands available (`/governance-override`)
- Weekly review of blocked PRs
- Metrics dashboard for false positive rate
- Clear escalation path in PR comments

### Risk 2: Forked PR Security Issues

**Likelihood:** MEDIUM (malicious fork bypasses checks)
**Impact:** CRITICAL (code execution, secrets leak)

**Mitigation:**
- Use `pull_request_target` (already done in #145)
- Never checkout PR code in blocking checks
- Only read PR metadata via API
- Permissions restricted to `read` + `write:checks`
- Regular security audits of workflow files

### Risk 3: Reviewer Assignment Spam

**Likelihood:** MEDIUM (too many reviewers assigned)
**Impact:** MEDIUM (reviewer fatigue, ignored assignments)

**Mitigation:**
- Limit max reviewers per PR (config: `max_reviewers: 3`)
- Smart deduplication (don't assign if already a reviewer)
- Rotation logic to spread load
- Opt-out mechanism for reviewers
- Weekly metrics on assignment distribution

### Risk 4: Configuration Drift

**Likelihood:** MEDIUM (config gets out of sync with reality)
**Impact:** MEDIUM (rules don't match team practices)

**Mitigation:**
- Version control for all config changes
- Monthly review of governance rules
- Automated tests for config schema validation
- Change log in config file
- PR review required for config changes (CODEOWNERS)

### Risk 5: Workflow Performance

**Likelihood:** LOW (checks run too slowly)
**Impact:** MEDIUM (delayed PR feedback)

**Mitigation:**
- Run checks in parallel
- Cache Python dependencies
- Limit API calls (use batching)
- Timeout after 2 minutes
- Performance monitoring in GITHUB_STEP_SUMMARY

### Risk 6: Breaking Existing PR Flow

**Likelihood:** MEDIUM (new checks break old PRs)
**Impact:** HIGH (blocks in-flight work)

**Mitigation:**
- MVP is non-blocking by default
- Gradual rollout (enable per-repo)
- Exempt existing PRs (check PR creation date)
- Clear communication before Phase 2
- Rollback plan tested and documented

---

## 6. Definition of Done (DoD) - MVP

### MVP Completion Criteria:

#### Code & Workflows
- [ ] `.github/workflows/pr-governance-check.yml` created and tested
- [ ] `.github/workflows/pr-reviewer-assignment.yml` created and tested
- [ ] `.github/scripts/pr_governance_check.py` implemented
- [ ] `.github/pr-labels.yml` extended with `enforcement` and `reviewer_assignment` sections
- [ ] All workflows pass on test PR

#### Testing
- [ ] Test PR with governance violation (verify warning posted)
- [ ] Test PR without violations (verify passes)
- [ ] Test PR with missing template sections (verify fails)
- [ ] Test PR with XL size (verify warning + reviewer assignment)
- [ ] Test forked PR (verify fork-safe operation)
- [ ] Test override commands work correctly

#### Documentation
- [ ] Architecture document (this file) in `.github/`
- [ ] Runbook entry for governance override process
- [ ] Update PR template with override command instructions
- [ ] Team communication sent about new checks

#### Configuration
- [ ] `enforcement.governance_blocking: false` (MVP default)
- [ ] `enforcement.template_blocking: true`
- [ ] `enforcement.size_blocking: false` (MVP default)
- [ ] Reviewer mappings configured
- [ ] Branch protection rules updated (non-blocking status checks)

#### Monitoring
- [ ] Metrics collection in GITHUB_STEP_SUMMARY
- [ ] Weekly review process documented
- [ ] Alert thresholds defined
- [ ] Rollback procedure tested

#### Acceptance
- [ ] 3 real PRs processed without issues
- [ ] Zero false positive complaints
- [ ] Reviewer assignments are relevant
- [ ] Team approval to proceed to Phase 2

---

## 7. File Structure Summary

```
.github/
├── workflows/
│   ├── pr-auto-label.yml              # EXISTING (#145)
│   ├── pr-governance-check.yml        # NEW (#144) - blocking checks
│   └── pr-reviewer-assignment.yml     # NEW (#144) - auto-assign reviewers
├── scripts/
│   ├── pr_auto_label.py               # EXISTING (#145)
│   └── pr_governance_check.py         # NEW (#144) - check logic
├── pr-labels.yml                      # EXTENDED (#144) - add enforcement section
├── ARCHITECTURE_ISSUE_144.md          # THIS DOCUMENT
└── CODEOWNERS                         # EXISTING (no changes)
```

---

## 8. Technical Specifications

### 8.1 Workflow Permissions

**pr-governance-check.yml:**
```yaml
permissions:
  contents: read          # Read repo files
  pull-requests: write    # Post comments
  checks: write           # Set check status
  statuses: write         # Set commit status
```

**pr-reviewer-assignment.yml:**
```yaml
permissions:
  contents: read          # Read repo files
  pull-requests: write    # Assign reviewers, post comments
  issues: write           # Read labels
```

### 8.2 API Rate Limits

**Estimated API Calls per PR:**
- Get PR details: 1
- List PR files: 1-3 (paginated)
- Get PR labels: 1
- List PR comments: 1-2 (paginated)
- Post comment: 0-1 (if needed)
- Assign reviewers: 0-1 (if needed)
- Set check status: 1-3 (per check)

**Total:** ~10-15 calls per PR event
**GitHub Rate Limit:** 5000/hour for GITHUB_TOKEN
**Safety:** Well within limits (can handle 300+ PR events/hour)

### 8.3 Performance Targets

- **Check duration:** < 30 seconds per workflow
- **Total PR labeling + checking:** < 90 seconds
- **Comment posting:** < 5 seconds
- **Reviewer assignment:** < 10 seconds

### 8.4 Error Handling

**Retry Logic:**
- API calls: 3 retries with exponential backoff
- Timeout: 120 seconds per workflow

**Failure Modes:**
- API failure → NEUTRAL status (don't block)
- Config parse error → FAIL status (block, fix config)
- Script error → NEUTRAL status (log, alert)

---

## 9. Migration Plan

### Pre-MVP (Preparation)
1. Review and approve this architecture document
2. Create feature branch `feature/pr-review-optimization`
3. Update `.github/pr-labels.yml` with new sections (non-blocking)
4. Create new workflow files
5. Create new Python script

### MVP Deployment (Phase 1)
1. Merge feature branch to main
2. Monitor first 10 PRs closely
3. Collect metrics for 2 weeks
4. Review false positive rate
5. Adjust rules based on data

### Blocking Enforcement (Phase 2)
1. Team review of Phase 1 metrics
2. Go/No-Go decision
3. Update config: `governance_blocking: true`
4. Update branch protection rules
5. Monitor first week closely
6. Have rollback ready

### Rollback Procedure
1. **Immediate:** Disable workflows via GitHub UI
2. **Quick:** Set `enforcement.*_blocking: false`
3. **Clean:** Revert branch protection rules
4. **Analysis:** Review what went wrong
5. **Fix:** Address issues before re-enabling

---

## 10. Open Questions and Decisions Needed

### Questions for Product Owner / Team:

1. **Governance Blocking:** Should Phase 2 block ALL governance violations, or only specific types?
2. **Reviewer Pool:** Who should be in `@maintainers` team for reviewer assignment?
3. **XL PR Policy:** Should XL PRs always require justification, or only for certain areas?
4. **Override Authority:** Who can use `/governance-override` command? (Current: write+ permissions)
5. **Metrics Review:** Who owns weekly review of blocked PRs and false positives?

### Decisions Made (System Architect):

- ✅ Use `pull_request_target` for fork safety
- ✅ MVP is non-blocking to gather data
- ✅ Separate labeling (#145) from enforcement (#144)
- ✅ Template check is blocking from MVP (low risk)
- ✅ Governance and size checks are non-blocking in MVP

---

## 11. Success Metrics

### MVP Phase (Phase 1)
- **Adoption:** 100% of PRs processed by new workflows
- **Accuracy:** <5% false positive rate on governance violations
- **Performance:** <90 seconds total check time
- **Developer Satisfaction:** Zero workflow-related complaints

### Enforcement Phase (Phase 2)
- **Merge Quality:** Zero governance violations merged
- **Velocity Impact:** <10% increase in PR merge time
- **Override Rate:** <5% of PRs require governance override
- **Reviewer Load:** Evenly distributed (±20% variance)

### Long-term (Post Phase 2)
- **Automation Rate:** 80%+ PRs get correct reviewers automatically
- **Review Time:** 20% reduction in time-to-first-review
- **Quality:** 50% reduction in governance-related rework

---

## 12. Appendices

### Appendix A: Example Override Comment

```markdown
/governance-override @jannekbuengener

**Justification:** This PR updates root documentation intentionally for the working repo README.
The Docs Hub will be synced separately via Issue #150.

**Risk:** Low - only affects README.md, no code changes.
```

### Appendix B: Example Size Justification Comment

```markdown
/size-xl-justified

**Reason:** Bulk refactoring of test files to new framework. Each file is simple, but many files.

**Review Strategy:** Can review by directory:
- `tests/unit/` - 20 files
- `tests/integration/` - 15 files
- `tests/e2e/` - 10 files

**Verification:** All tests pass, coverage unchanged.
```

### Appendix C: Configuration Schema

```yaml
# .github/pr-labels.yml FULL SCHEMA

version: 1

# EXISTING (#145)
area_labels: [...]
title_labels: [...]
governance: [...]
review: [...]
size: [...]

# NEW (#144)
enforcement:
  enabled: boolean
  governance_blocking: boolean
  governance_override_command: string
  governance_override_permissions: [string]
  template_blocking: boolean
  required_sections: [string]
  size_blocking: boolean
  xl_requires_justification: boolean
  xl_justification_command: string

reviewer_assignment:
  enabled: boolean
  respect_codeowners: boolean
  max_reviewers: integer
  mappings:
    - labels: [string]
      reviewers: [string]
      required_count: integer
      additional_reviewers: integer
```

---

## Document Change Log

| Version | Date       | Author           | Changes                     |
|---------|------------|------------------|-----------------------------|
| 1.0     | 2025-12-27 | system-architect | Initial architecture design |

---

## Approval and Next Steps

**Architecture Review Required By:**
- [ ] Product Owner
- [ ] Tech Lead
- [ ] DevOps Engineer
- [ ] Security Engineer (for fork-safety validation)

**Next Steps After Approval:**
1. Create tracking issues for MVP implementation
2. Assign implementation to appropriate agent (code-reviewer)
3. Schedule MVP deployment date
4. Plan Phase 2 timeline based on MVP metrics

**Estimated Implementation Time:**
- MVP (Phase 1): 8-16 hours development + 2 weeks validation
- Phase 2: 2-4 hours (config change + monitoring)
- Phase 3: TBD (future roadmap)

---

**End of Architecture Document**
