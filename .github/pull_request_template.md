# Pull Request

## Summary
<!-- 1-3 Sätze: Was wird geändert und warum? -->

## Type
<!-- Wähle EINE Option (delete others): -->
- [ ] **Feature** - Neue Funktionalität
- [ ] **Bug** - Fehlerbehebung
- [ ] **Refactor** - Code-Umbau ohne Funktionsänderung
- [ ] **Docs** - Nur Dokumentation
- [ ] **Chore** - Wartung, Tooling, CI/CD

---

## Changes
<!-- Bulletpoints: Was wurde konkret geändert? -->
-
-
-

---

## Testing
### Test Coverage
- [ ] Unit Tests added/updated (≥90% coverage)
- [ ] Integration Tests added/updated (≥80% coverage)
- [ ] E2E/Feature Tests added (if applicable)
- [ ] Manual testing completed

### Test Evidence
<!-- REQUIRED: Link to CI run oder paste test output -->
```
Coverage: __%
Tests passed: __/__
```

**CI Run:** [Link to Actions run](#)

**Screenshots/Logs** (if UI/output changes):
<!-- Paste screenshots or logs here -->

---

## Risk Assessment
### Breaking Changes
- [ ] **No breaking changes**
- [ ] **Breaking changes** (describe below):

<!-- If breaking changes, describe:
- What breaks?
- Who is affected?
- Migration path?
-->

### Impact
- [ ] **Low** - Isolated change, minimal risk
- [ ] **Medium** - Multiple components, moderate risk
- [ ] **High** - Critical path, high risk

### Rollback Plan
<!-- How to revert this PR if issues arise? -->
- [ ] Revert commit (simple rollback)
- [ ] Feature flag kill-switch available
- [ ] Requires data migration rollback (describe steps below)
- [ ] Other (describe):

---

## Documentation
- [ ] Code comments added where needed
- [ ] API documentation updated
- [ ] README/Runbook updated
- [ ] ADR created/updated (if architectural decision)
- [ ] No documentation needed

**Docs Updated:**
<!-- List files or link to docs PR -->

---

## Deployment
### Deployment Strategy
- [ ] **Direct merge** (low risk, standard deployment)
- [ ] **Feature flag** (gradual rollout)
- [ ] **Requires DB migration** (describe below)
- [ ] **Requires infrastructure changes** (describe below)

### Environment Sequence
- [ ] Local tested
- [ ] Dev environment ready
- [ ] Staging tested
- [ ] Production deployment planned

---

## Governance Compliance
<!-- AUTO-CHECKED by pr-auto-label.yml (Issue #145) -->
- [ ] No `.github/` changes (or governance-approved)
- [ ] No root-level files modified (or docs-approved)
- [ ] CODEOWNERS consulted if needed

**Governance Override** (if needed):
<!-- Use `/governance-override @maintainer-name` in comment -->

---

## Review Checklist (Author Self-Check)
- [ ] Code follows project conventions
- [ ] Security considerations addressed
- [ ] Error handling implemented
- [ ] Logging added where appropriate
- [ ] Performance impact assessed
- [ ] All CI checks passing
- [ ] Linked to related issue(s)

---

## Related Issues
Closes #
Related to #

---

## Additional Context
<!-- Optional: Add any context not covered above -->
