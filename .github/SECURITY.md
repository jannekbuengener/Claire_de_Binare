# Security Policy

Claire de Binare (CDB) operates in shadow/paper mode. This policy documents
security reporting and repository measures. It does **not** authorize live
capital, production trading, or Echtgeld operations. Live-Readiness remains
**NO-GO** — SSOT: [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).

---

## Supported Versions

Only the `main` branch receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| other   | :x:                |

---

## Reporting a Vulnerability

**DO NOT** create public GitHub issues for security vulnerabilities.

Report suspected vulnerabilities privately:

1. **Email:** modusmono.dev@gmail.com
2. **Subject:** `[SECURITY] CDB Vulnerability Report`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

Reports are reviewed. Further handling and coordinated disclosure are managed
case by case. **No fixed response, triage, patch, or disclosure timelines are
promised.**

Maintainers may also use [GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories) for private coordination when appropriate. Private Vulnerability Reporting is not claimed as enabled in this repository unless separately verified on GitHub.

---

## Security Scope

In scope for this policy:

- Secrets or credentials exposure in the repository or documented operator paths
- Dependency and supply-chain vulnerabilities affecting supported code on `main`
- CI/workflow misconfigurations with demonstrable security impact
- Container image vulnerabilities surfaced by repository scanning workflows
- Unsafe defaults on order, risk, or execution paths in code reviewed on `main`

Out of scope:

- Live trading authorization or capital deployment decisions
- LR re-evaluation or board-stage changes
- Production runtime changes without an explicit scoped issue
- General feature requests or non-security bugs (use public issues)
- Historical archive trees under `docs/archive/` and `knowledge/archive/`

---

## Implemented Measures (live-verified)

Repository and platform controls currently in use:

| Measure | Location / evidence |
| ------- | ------------------- |
| Gitleaks secret scanning | [`.github/workflows/gitleaks.yml`](workflows/gitleaks.yml) |
| CodeQL Python analysis | [`.github/workflows/codeql-python.yml`](workflows/codeql-python.yml) |
| Trivy container scanning | [`.github/workflows/trivy.yml`](workflows/trivy.yml), [`.github/workflows/security-scan.yml`](workflows/security-scan.yml) |
| Dependabot version updates | [`.github/dependabot.yml`](dependabot.yml) |
| GitHub Secret Scanning | enabled (repository security settings) |
| GitHub Push Protection | enabled (repository security settings) |
| Dependabot security updates | enabled (repository security settings) |
| Local security scan helper | `make security-scan` (Gitleaks when installed, Bandit, Ruff) |

Security triage and readouts: [`docs/security/README.md`](../docs/security/README.md).

Secrets governance: [`knowledge/governance/SECRETS_POLICY.md`](../knowledge/governance/SECRETS_POLICY.md).

---

## Operator Boundaries

- No secrets in the repository; use the documented secrets path and Docker secrets.
- Productive database writes, MCP mutations, and BLUE/RED runtime changes require
  explicit human scope — not implied by this policy.
- Board stage `trade-capable` is orthogonal to live-readiness and does not grant
  live-capital authorization.

---

**Last Updated:** 2026-07-13
