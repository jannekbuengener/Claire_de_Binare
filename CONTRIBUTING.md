# Contributing to Claire de Binare

Thank you for your interest in contributing to Claire de Binare! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop with Docker Compose
- Git with pre-commit hooks

### Local Setup

```bash
# Clone the repository
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Setup secrets (copy template)
cp .env.example .cdb_local/.secrets/.env.compose
# Edit with your credentials
```

### Running the Stack

```powershell
# Development mode
.\infrastructure\scripts\stack_up.ps1

# Production mode with all hardening
.\infrastructure\scripts\stack_up.ps1 -Profile prod -TLS -StrictHealth -NetworkIsolation
```

## Development Workflow

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

**Example:** `feat/310-add-license-file`

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/). Pre-commit hooks enforce this format:

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
docs(readme): update installation instructions
```

### Pull Requests

1. Create a feature branch from `main`
2. Make your changes with meaningful commits
3. Ensure all tests pass: `pytest tests/`
4. Ensure code quality: `pre-commit run --all-files`
5. Open a PR against `main`

**PR Title Format:** Same as commit message format
**PR Template:** Use the provided template (`.github/pull_request_template.md`)

### Testing Requirements

- All new code must have tests
- Minimum coverage: 80%
- Run tests before committing:

```bash
# Unit tests only
pytest tests/unit/ -v

# Full test suite
pytest tests/ -v --cov=core --cov=services

# E2E tests (requires running stack)
pytest tests/e2e/ -v -m e2e
```

## Local Sanity Checks

Use these commands to mirror the CI jobs locally before GitHub Actions is available:

- `ruff check .`
- `black --check --diff .`
- `mypy services/ --ignore-missing-imports --no-strict-optional`
- `python -m pytest -v -m "not e2e and not local_only"`

## Code Style

### Python

- Formatter: **black** (line length 88)
- Linter: **flake8**
- Type checker: **mypy**
- All configured in `.pre-commit-config.yaml`

### General Guidelines

- Use type hints for all function signatures
- Document complex logic with docstrings
- Prefer explicit over implicit
- Keep functions focused and small

## Architecture

### Directory Structure

```
Claire_de_Binare/
├── core/               # Shared modules (clients, config, domain, utils)
├── services/           # Microservices (execution, risk, market, etc.)
├── infrastructure/     # IaC (compose, tls, database, monitoring)
├── tests/              # Unit, integration, E2E tests
└── .github/            # CI/CD workflows, templates
```

### Key Principles

1. **Microservices:** Each service is self-contained
2. **Event-driven:** Services communicate via Redis Streams
3. **Domain-driven:** Clear separation of concerns
4. **Infrastructure as Code:** All infra in `infrastructure/`

## Getting Help

- **Issues:** Search existing issues or create a new one
- **Discussions:** Use GitHub Discussions for questions
- **Documentation:** Check `knowledge/` directory

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
