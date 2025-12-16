# Integration Plan — PR-01..PR-06 → main

**Date:** 2025-12-16  
**Integrator:** Copilot  
**Canonical Remote:** gitlab  
**Strategy:** Small merges, test after each, push after each success

---

## Order & Rationale

1. **feature/pr-01-ci-guard** (a890a22)  
   → Adds GitLab CI pipeline + Write-Zone validation  
   → Foundation for CI checks

2. **feature/pr-02-safe-deletes** (006ccf5)  
   → Rollback & cleanup scripts  
   → Safety tooling

3. **feature/pr-03-makefile-compose** (8133272)  
   → Makefile + Compose fragment support  
   → Build orchestration

4. **feature/pr-04-unit-tests** (d9b407b)  
   → Unit test skeletons + fixtures  
   → Test infrastructure

5. **feature/pr-05-compose-split** (a2714ac)  
   → Docker Compose split (base/dev/prod)  
   → Infrastructure refinement

6. **feature/pr-06-replay-enabler** (ec9a59f)  
   → Deterministic replay (Clock/Seed/UUID)  
   → Testing determinism

---

## Procedure (per PR)

```bash
git checkout main
git merge --no-ff feature/pr-XX-<name>
python -m pytest -q
git push gitlab main
```

If tests fail → **STOP**, fix, repeat test.

---

## Constraints

- No remote pulls (local = truth)
- No bytecode commits (gitignore enforced)
- Submodule `docs/` stays deinitialized (no `D docs` commits)
- All merges auditable (--no-ff)

---

## Expected Outcome

- **main** at HEAD with all 6 PRs integrated
- All tests green
- Clean history with merge commits
- Pushed to gitlab after each merge
