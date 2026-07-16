# Contributing to Claire de Binare

Thank you for your interest in contributing to Claire de Binare! This document
provides guidelines for contributing to the project.

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker Desktop with Docker Compose (optional for CI-only work)
- Git

### Onboarding Chain

Start here if you are new to the project:

1. [`README.md`](README.md) — GitHub landing page
2. [`docs/index.md`](docs/index.md) — Shortest docs navigation
3. [`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`](docs/onboarding/DEVELOPER_VISUAL_START_HERE.md) — Visual developer start
4. [`DEVELOPER_ONBOARDING.md`](DEVELOPER_ONBOARDING.md) — Full setup guide

### README Link Convention

For repository-internal documentation paths in **active** `README.md` files **and**
explicit canon entry points listed in
[`tests/fixtures/readme_link_policy.yaml`](tests/fixtures/readme_link_policy.yaml)
(`explicit_active_surfaces`, e.g. `CURRENT_STATUS.md`, `CONTROL_REGISTER.md`,
`docs/onboarding/cdb_glossary.md`):

- Use **relative Markdown links**, not bare inline-code paths, when the path is
  navigation-relevant (entry points, parent/root/index, runbooks, contracts).
- Keep **inline code** for shell commands, config examples, and illustrative
  paths inside code blocks.
- Prefer a small `## Navigation` block where a README is an area index (adapt
  links to directory depth; no blind copy-paste).
- Archive trees (`docs/archive/`, `knowledge/archive/`) and fixture paths are
  classified out of the README link guard — see
  [`tests/fixtures/readme_link_policy.yaml`](tests/fixtures/readme_link_policy.yaml).

Validation (offline, no network):

```bash
make readme-links-guard      # active README.md + explicit canon entry points (#3994/#3995/#4037)
make onboarding-docs-guard   # onboarding front-door surfaces (#3233)
```

See also [`docs/meta/REPOSITORY_CANON.md`](docs/meta/REPOSITORY_CANON.md)
(README vs. `docs/index.md` navigation rule).

### Local Setup

```bash
# Clone the repository
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare

# Create virtual environment (Python 3.12+)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .\.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup secrets directory
# Canonical path: ~/Documents/.secrets/.cdb/
# Windows: .\tools\cdb.ps1 secrets init
# Linux:   ./infrastructure/scripts/init-secrets.sh
# Docs: knowledge/governance/SECRETS_POLICY.md
```

### Quick Verification

```bash
# Lint (CI-required)
ruff check .

# Quick test (no containers needed)
pytest -q -k "not test_mcp_time_server_runtime"

# Context preflight
make context-doctor
```

---

## Development Workflow

### Dedupe Before You Start

Before opening an issue, branch, or PR:

1. Search open issues and PRs for duplicates or overlapping scope.
2. Extend existing work instead of creating parallel governance or doc hubs.
3. Link related issues in the PR body (`Refs #...`).

Worktree and branch cleanup of obsolete leftovers is tracked in
[Issue #4006](https://github.com/jannekbuengener/Claire_de_Binare/issues/4006) —
do not delete foreign worktrees or branches inside other scopes.

### Branch Naming

Follow this pattern: `<type>/<issue-number>-<short-description>`

| Type | Purpose |
|------|---------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `refactor/` | Code refactoring |
| `test/` | Test additions/fixes |
| `chore/` | Maintenance tasks |

Example: `docs/3229-developer-onboarding-reconcile`

### Branch and Worktree Hygiene

- Branch from current `origin/main`.
- Prefer a **dedicated git worktree** for issue-scoped delivery so parallel
  sessions do not overwrite each other.
- Keep the working tree clean before push; do not mix unrelated changes.
- Cleanup of obsolete worktrees, branches, stashes, and remotes belongs to
  [#4006](https://github.com/jannekbuengener/Claire_de_Binare/issues/4006).

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**Examples:**
```
feat(risk): add drawdown guard with configurable threshold
fix(execution): handle MEXC rate limit gracefully
docs(onboarding): reconcile zero-context developer setup
```

### Pull Requests

1. Create a feature branch from `main`
2. Make your changes with meaningful commits
3. Run lint + test: `ruff check . && pytest -q -k "not test_mcp_time_server_runtime"`
4. Push and create a PR against `main`
5. **After PR creation, set a `LOCK:` comment on the PR** before any further
   push, PR, or GitHub mutation. This is a single-writer lock.
   Format: `LOCK: agent=<agent> issue=<issue> ts=<UTC timestamp> mode=single-writer`
6. Wait for required checks (CI gate must pass)
7. Squash-merge when approved and green

**PR Title Format:** Same as commit message format.
**PR Template:** Use the provided template (`.github/pull_request_template.md`).

**Important**: An issue-status comment (e.g. "working on this") does **not**
replace the required PR `LOCK:`. The `LOCK:` must be on the PR itself before
any mutation.

### Testing Requirements

- All new code must have tests
- Minimum coverage: 80%
- Run tests before committing:

```bash
# CI slice (unit + integration, no containers)
make test

# Unit tests only
pytest tests/unit/ -v

# With coverage
make test-coverage

# E2E tests (requires running stack)
pytest tests/e2e/ -v -m e2e
```

### Required Checks

Merge contract on `main` (SSOT:
[`docs/runbooks/merge_policy_ci_gate.md`](docs/runbooks/merge_policy_ci_gate.md)):

| Check | Source |
|-------|--------|
| `ci (Unit/Integration + Lint gesammelt)` | `.github/workflows/ci.yml` |
| `policy-gate` | `.github/workflows/policy-gate.yml` |

Inside the CI gate: `ruff check .`, unit/integration tests, and Black on changed
Python under `services/` and `tests/`. Coverage >= 80% applies when running
`make test-coverage` locally; the default CI slice does not enforce coverage on
every PR.

Classify your PR scope with the policy-gate rules in the merge-policy runbook.
Do not assume labels without checking the live diff classification.

### Scope Boundaries

This project enforces strict scope boundaries:

| Scope | Allowed | Not Allowed |
|-------|---------|-------------|
| Code/Docs | Features, fixes, docs, tests | — |
| Runtime/Docker | Documented in runbooks | No changes without explicit issue scope |
| Live Trading | Never (LR remains **NO-GO**) | No Live-Go, no Echtgeld-Go |
| DB/Memory writes | Test/mock only | No productive writes without Human-GO |
| CI/CD | Workflow fixes | No infra changes without scope |

### Linting & Formatting

```bash
# Lint
ruff check .

# Format
black .

# Type check
mypy core/ services/
```

### Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit run --all-files
make root-layout-guard
```

Note: Ruff and Black gates in CI are the primary enforcement. Pre-commit is
optional for local convenience.

---

## Architecture

### Directory Structure

```
Claire_de_Binare/
├── core/               # Shared modules (clients, config, domain, utils)
├── services/           # Microservices (execution, risk, market, etc.)
├── infrastructure/     # IaC (compose, tls, database, monitoring)
├── config/             # Repository, ARVP, and readiness configuration
├── artifacts/          # Generated local/CI output
├── tests/              # Unit, integration, E2E tests
├── tools/              # PowerShell helpers, diagnostics
├── scripts/            # Repo-wide automation and operator scripts
├── agents/             # Canonical agent registry and role guidance
├── knowledge/          # Governance, policy, knowledge hub
├── docs/               # Runbooks, evidence, navigation
└── .github/            # CI/CD workflows, templates
```

The complete root allowlist and placement rules are documented in
[`docs/meta/ROOT_INFORMATION_ARCHITECTURE.md`](docs/meta/ROOT_INFORMATION_ARCHITECTURE.md).

### Key Principles

1. **Microservices:** Each service is self-contained
2. **Event-driven:** Services communicate via Redis Streams
3. **Domain-driven:** Clear separation of concerns
4. **Infrastructure as Code:** All infra in `infrastructure/`
5. **Deterministic:** All system state must be reproducible
6. **Governance-first:** Policy over convenience

---

## Agents, Brain Evidence, and MCP Boundaries

- Agent bootloader pointer: [`agents/AGENTS.md`](agents/AGENTS.md) (full Read Order
  and operating rules live there — not duplicated here).
- For strategy/runtime/module/service/contract/context scope, output the Brain
  Evidence block from `agents/AGENTS.md` **before any plan**. Repo/GitHub live
  evidence overrides brain or ledger claims.
- Skills live under `.cursor/skills/`, `.codex/cdb_skills/`, `.opencode/skills/`
  — load only what the task needs; skills do not grant write permission.
- Context/MCP tools are read-only by default on `main`
  (`PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`). Productive DB writes, MCP
  mutations, and runtime changes require explicit human scope.

---

## Security Reporting

- **Do not** report security vulnerabilities as public GitHub issues.
- Use the canonical policy: [`.github/SECURITY.md`](.github/SECURITY.md)
- Contact: `modusmono.dev@gmail.com`

---

## Safety / LR Boundaries

- **LR bleibt NO-GO** — SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Board-Stage `trade-capable` ist kein Live-Go
- Kein Echtgeld-Go ohne explizite Human-Freigabe
- `CURRENT_STATUS.md` ist ein Ledger, nicht Live-Wahrheit
- GitHub live und Repo live fuehren
- Stage-/Board-Aussagen und LR-Go/No-Go-Aussagen strikt trennen

---

## Getting Help

- **Issues:** Search existing issues or create a new one (not for security bugs)
- **Documentation:** Start with [`docs/index.md`](docs/index.md)
- **Repo Brain / Context:** `make context-doctor` or [`docs/surrealdb/README.md`](docs/surrealdb/README.md)
- **Code of Conduct:** [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- **Security:** [`.github/SECURITY.md`](.github/SECURITY.md)
