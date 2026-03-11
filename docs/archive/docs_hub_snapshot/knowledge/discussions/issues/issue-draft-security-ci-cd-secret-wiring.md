# CI/CD Integration: GitHub/GitLab Secret Wiring

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, ci, devops, docs]
Milestone: Security / M8

Goal:
Wire CI/CD so secrets come only from the platform secret store, with clear required names and safe behavior for untrusted or non-protected runs. The wiring must be deterministic and documented for both GitHub and GitLab.

Non-Goals:
- Introducing a new CI system or replacing existing pipelines.
- Storing secrets in the repo or in CI job artifacts.
- Adding non-security features unrelated to secret handling.
- Forcing secrets in unprotected contexts such as forks or dry-run pipelines.
- Changing application runtime secret handling beyond CI wiring.

Files/Paths to touch:
- .gitlab-ci.yml
- .github/workflows/*
- SECURITY_ISSUES.md
- Claire_de_Binare_Docs/docs/content/security/ci-secrets-wiring.md
- Claire_de_Binare_Docs/data/ci-secret-registry.yaml

Ordered Steps:
1. Enumerate required CI secrets and map each to its usage (job, environment, service) in a single registry list.
2. Update .gitlab-ci.yml to consume secrets only via CI variables, with clear error output when missing.
3. Update GitHub Actions workflows to read from repository or environment secrets, not files in the repo.
4. Define a protected-job rule: protected jobs require secrets; unprotected jobs skip safely with a clear message.
5. Document the expected secret names, scopes, and owners in the Docs Hub.
6. Add a minimal validation step in CI to confirm required secrets exist before running protected jobs.
7. Ensure CI logs do not echo secret values, even in error output.
8. Provide a dry-run mode or documentation that explains how to run CI without secrets locally.

Acceptance Criteria:
- CI secrets are referenced only through platform secret stores in GitHub/GitLab.
- A single registry file lists all required secret names with scope and owner.
- Protected jobs fail fast with clear errors if secrets are missing.
- Unprotected jobs complete without secrets and without leaking sensitive information.
- No secret values are printed in logs or stored in artifacts.
- Docs Hub contains a CI secret wiring guide with step-by-step setup.
- SECURITY_ISSUES.md references the CI secret wiring location.
- A minimal validation step runs before protected jobs and exits with a single, clear error summary.

Risks:
- Misconfigured secret names could break protected CI jobs.
- Excessive gating could block harmless contributor workflows.
- Incomplete registry entries may cause drift and inconsistent behavior.
- CI logs could accidentally expose context if not sanitized.
- Multiple CI systems could diverge if updates are not kept in sync.

Rollback:
- Revert CI configuration changes to prior behavior.
- Remove the registry file if it becomes outdated or unused.
- Restore previous documentation links in SECURITY_ISSUES.md.
