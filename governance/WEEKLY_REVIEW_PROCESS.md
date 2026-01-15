# Weekly Governance Review Process

**Owner**: Project Maintainer (Jannek Buengener)
**Frequency**: Every Monday, 10:00 CET
**Duration**: 30 minutes
**Location**: GitHub Issues + PR comments
**Established**: 2026-01-15

---

## Purpose

Ensure consistent governance oversight and timely resolution of security, compliance, and operational concerns through structured weekly reviews.

---

## Schedule

- **Day**: Every Monday
- **Time**: 10:00 CET
- **Duration**: 30 minutes
- **Interface**: GitHub web interface + CLI tools
- **Documentation**: Review notes in Issue #328 comments

---

## Scope

### 1. Security Findings Review

**Tools**:
- Trivy scan results (`.github/workflows/trivy.yml`)
- Gitleaks findings (`gitleaks.log`)
- Security-scan workflow results
- Dependabot alerts

**Actions**:
- Review all HIGH/CRITICAL vulnerabilities
- Triage new security findings
- Track remediation progress
- Update security policy if needed

**Threshold**: Zero HIGH/CRITICAL vulnerabilities tolerated >7 days

---

### 2. Pull Request Health

**Criteria**:
- PRs open >7 days without review
- Blocked PRs awaiting delivery gate approval
- Draft PRs open >14 days
- Stale PRs (>30 days no activity)

**Actions**:
- Review long-running PRs
- Request reviews from appropriate owners
- Close stale or abandoned PRs
- Update delivery gate approvals

**Command**:
```bash
gh pr list --state open --json number,title,createdAt,updatedAt,isDraft
```

---

### 3. Milestone Progress

**Milestones**:
- M1-M9 progress tracking
- Q1 2026 milestone status
- Blocked issues preventing milestone completion

**Actions**:
- Review milestone completion percentage
- Identify blocking issues
- Reassign or re-scope if necessary
- Update roadmap documentation

**Command**:
```bash
gh issue list --milestone "M1" --state open
```

---

### 4. Policy Violations

**Checks**:
- Emoji usage in commit messages (emoji-bot alerts)
- Delivery gate bypasses (exception label usage)
- Pre-commit hook failures in CI
- Test coverage drops below 80%

**Actions**:
- Review policy violation alerts
- Follow up with contributors
- Update policies if systematic issues found
- Document exceptions

---

### 5. Stale Issues

**Criteria**:
- Issues open >30 days with no activity
- Issues with `status:parked` >90 days
- Issues without milestone assignment
- Duplicate or obsolete issues

**Actions**:
- Close obsolete issues
- Re-assign stale issues
- Add context to parked issues
- Convert to discussions if appropriate

**Command**:
```bash
gh issue list --state open --json number,title,updatedAt --jq '.[] | select((.updatedAt | fromdateiso8601) < (now - 2592000)) | "\(.number): \(.title)"'
```

---

## Review Checklist

Use this checklist during each weekly review:

### Pre-Review Setup
- [ ] Open GitHub repository in browser
- [ ] Terminal with `gh` CLI ready
- [ ] Review previous week's action items

### Security Review
- [ ] Check Trivy scan results (last 7 days)
- [ ] Review gitleaks findings
- [ ] Check Dependabot alerts
- [ ] Verify no HIGH/CRITICAL vulnerabilities >7 days old
- [ ] Document any new security concerns

### PR Health Check
- [ ] List PRs open >7 days: `gh pr list --state open`
- [ ] Review draft PRs >14 days
- [ ] Check delivery gate blocked PRs
- [ ] Close or request reviews as needed

### Milestone Progress
- [ ] Check current milestone (e.g., M1): `gh issue list --milestone "M1"`
- [ ] Identify blocking issues
- [ ] Update milestone assignments if needed
- [ ] Review completion percentage

### Policy Compliance
- [ ] Check emoji-bot alerts (last 7 days)
- [ ] Review delivery gate exception usage
- [ ] Verify test coverage maintained >80%
- [ ] Check for pre-commit hook bypass attempts

### Stale Issue Cleanup
- [ ] List issues updated >30 days ago
- [ ] Review `status:parked` issues >90 days
- [ ] Close obsolete/duplicate issues
- [ ] Add milestone to unassigned issues

### Post-Review Documentation
- [ ] Comment on Issue #328 with review summary
- [ ] Create action items for follow-up
- [ ] Update roadmap if milestones changed
- [ ] Schedule next week's review

---

## Action Item Tracking

Document action items in Issue #328 using this format:

```markdown
## Weekly Review - 2026-01-XX

### Action Items
- [ ] #123: Review security finding in aiohttp dependency (Owner: Maintainer, Due: 2026-01-XX)
- [ ] #456: Close stale PR (Owner: Bot, Due: Immediate)
- [ ] #789: Update M2 milestone completion (Owner: Maintainer, Due: 2026-01-XX)

### Summary
- Security: X findings reviewed, Y resolved
- PRs: X reviewed, Y merged, Z closed
- Milestones: M1 at X% completion
- Policies: No violations
- Stale Issues: X closed, Y re-assigned
```

---

## Escalation Criteria

Escalate to immediate action (outside weekly cycle) if:

1. **CRITICAL security vulnerability** discovered (CVSSv3 ≥9.0)
2. **Production incident** or system outage
3. **Delivery gate abuse** or policy violation requiring investigation
4. **Milestone blocker** preventing critical path progress

---

## Review History

Track review completion in this table:

| Date | Reviewer | Security | PRs | Milestones | Issues | Notes |
|------|----------|----------|-----|------------|--------|-------|
| 2026-01-15 | Maintainer | ✅ 0 HIGH/CRIT | ✅ 4 PRs | M1: 85% | 3 closed | Initial audit |
| 2026-01-20 | - | - | - | - | - | *Next review* |

---

## Tool References

### GitHub CLI Commands

```bash
# List open PRs with age
gh pr list --state open --json number,title,createdAt,updatedAt

# List issues by milestone
gh issue list --milestone "M1" --state open

# List stale issues (>30 days)
gh issue list --state open --json number,title,updatedAt

# View security alerts
gh api /repos/:owner/:repo/vulnerability-alerts

# List workflow runs (last 7 days)
gh run list --limit 50
```

### Makefile Targets

```bash
# Run security scan
make security-scan

# Run test coverage
make test-coverage

# Run gitleaks
gitleaks detect --source . --report-path gitleaks.log
```

---

## Process Improvements

This process is a living document. Suggest improvements by:

1. Opening an issue with label `governance`
2. Proposing changes in PR to this file
3. Discussing in Issue #328 comments

**Last Updated**: 2026-01-15
**Next Review**: Q2 2026 (after Phase 3 planning)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
