# CDB local CI image — Python 3.12 to match merge-gate ci.yml (not Dockerfile.test 3.14).
# No secrets. No GHCR push. Not a Required Check publisher.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=utf-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    make \
    && rm -rf /var/lib/apt/lists/*

# COPY sources must remain allowed by the repo-root .dockerignore — this image is
# also the Cursor Cloud environment build target (`.cursor/environment.json`, #4360).
COPY requirements.txt requirements-dev.txt requirements-mcp.txt pyproject.toml ./
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt -r requirements-mcp.txt
# Toolchain SSOT (#4206): black/ruff pins come only from requirements-dev.txt.
# Do not reinstall unversioned ruff/black after the requirements install.

# Application tree is bind-mounted at runtime for commit-bound evidence.
CMD ["python", "ci/scripts/run.py", "--profile", "fast"]
