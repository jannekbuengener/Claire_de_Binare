# LR-000: Security Ruleset Exception (Timeboxed)

## What Changed
Temporarily lowered Ruleset `main-protection-single-maintainer` code_scanning threshold from `high_or_higher` to `critical_or_higher` (or `none` if CRITICAL alerts block).

## Why
Unblock merge of PR #790 (Live-Readiness Governance Framework delivery). Security backlog already identified and tracked separately. PR #790 contains no runtime code changes - only governance documentation.

## Timebox
- **Start:** 2026-02-04
- **Revert By:** 2026-02-11 (7 days)
- **Condition:** Revert threshold back to `high_or_higher` after LR-002 is merged OR by deadline, whichever comes first.

## Owner
Jannek Büngener

## Links
- **PR #790:** https://github.com/jannekbuengener/Claire_de_Binare/pull/790
- **Ruleset:** https://github.com/jannekbuengener/Claire_de_Binare/rules/11617228
- **Follow-up Issue:** (created in STOP E)

## Evidence (STOP A - Captured 2026-02-04 12:10 UTC)

### Current Ruleset Code Scanning Requirements:
```json
{
  "type": "code_scanning",
  "parameters": {
    "code_scanning_tools": [
      {
        "tool": "CodeQL",
        "security_alerts_threshold": "high_or_higher",
        "alerts_threshold": "none"
      },
      {
        "tool": "Gitleaks",
        "security_alerts_threshold": "high_or_higher",
        "alerts_threshold": "errors"
      },
      {
        "tool": "Trivy",
        "security_alerts_threshold": "high_or_higher",
        "alerts_threshold": "errors"
      }
    ]
  }
}
```

### Alert Counts:
- **Total Open Alerts:** 93
- **HIGH/CRITICAL Alerts:** 23
  - 2x CRITICAL severity (CVE-2025-15467)
  - 21x HIGH severity (various CVEs + py/clear-text-logging-sensitive-data)

### Blocker Analysis:
Ruleset requires 0 HIGH+ security alerts for merge. Current state: 23 HIGH+.

**Decision:** Governance-approved exception to deliver Live-Readiness framework (docs-only PR). Security remediation tracked in separate issue with clear acceptance criteria (0 HIGH/CRITICAL alerts).

## Acceptance Criteria for Revert:
1. All HIGH/CRITICAL code scanning alerts resolved OR dismissed with justification
2. LR-002 (Contract Tests) merged successfully
3. Threshold reverted to `high_or_higher` in Ruleset 11617228
4. Follow-up issue closed

---
**Status:** ACTIVE (awaiting user Ruleset change in GitHub UI)
