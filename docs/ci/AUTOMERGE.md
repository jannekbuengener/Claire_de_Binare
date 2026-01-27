# Auto-merge (Jules + checks + label)

Rules
- Auto-merge runs only when ALL are true:
  - PR has label `automerge`
  - Jules review is APPROVED
  - Required checks are green on PR head SHA

How to use
1) Ensure label `automerge` exists (sync labels from `.github/workflows/labels.json` or create manually).
2) Set repo variable `JULES_LOGIN` to the GitHub login of the Jules bot.
3) Add secret `AUTOMERGE_TOKEN` (PAT with `repo` scope) for merge permission.
4) (Optional) Set repo variable `AUTOMERGE_REQUIRED_CHECKS` as a comma-separated list of check names.
5) Apply label `automerge` to an eligible PR.

Branch protection settings (manual)
- Require pull request before merging
- Require approvals (>= 1)
- Require status checks to pass
- Restrict dismissing reviews
- Require CODEOWNERS review (only if Jules is enforced via CODEOWNERS)

Workflow
- `.github/workflows/automerge.yml`
