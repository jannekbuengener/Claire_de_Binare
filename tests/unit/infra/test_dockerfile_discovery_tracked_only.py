"""Regression: Dockerfile discovery is git-tracked only (#4237).

Protects the pip-pin classification inventory from local worktrees, backups,
vendor copies, and untracked Dockerfiles that previously leaked in via
filesystem-wide Path.rglob.

test_id: tc_dockerfile_discovery_tracked_only_4237
test_type: contract / bauteil
cdb_area: infra/ci
rule_ref: discover_dockerfiles tracked-only semantics
issue_ref: #4237
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.unit.infra import _dockerfile_pip_pin_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "cdb-test@example.com")
    _git(repo, "config", "user.name", "CDB Test")


def _write(repo: Path, relative: str, content: str = "FROM scratch\n") -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _commit_tracked(repo: Path, *relative_paths: str) -> None:
    _git(repo, "add", "--", *relative_paths)
    _git(repo, "commit", "-m", "track dockerfiles")


@pytest.fixture
def discovery_repo(tmp_path: Path) -> Path:
    """Temporary git repo with tracked, untracked, and nested-worktree Dockerfiles."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    tracked = (
        "services/alpha/Dockerfile",
        "ci/Dockerfile",
        "infrastructure/compose/Dockerfile.test",
    )
    for relative in tracked:
        _write(repo, relative)

    # Untracked local pollution — must not appear in discovery.
    _write(repo, "services/local-scratch/Dockerfile")
    _write(repo, ".worktrees/decoy-branch/services/ws/Dockerfile")
    _write(repo, "prefix/.worktrees/nested/Dockerfile")
    _write(repo, ".worktrees_backup/old/Dockerfile")
    _write(repo, "third_party/vendor/Dockerfile")
    _write(repo, ".venv/lib/Dockerfile")

    _commit_tracked(repo, *tracked)
    return repo


def test_tracked_dockerfile_is_discovered(discovery_repo: Path) -> None:
    found = helpers.discover_dockerfiles(discovery_repo)
    assert "services/alpha/Dockerfile" in found
    assert "ci/Dockerfile" in found
    assert "infrastructure/compose/Dockerfile.test" in found


def test_untracked_dockerfile_is_ignored(discovery_repo: Path) -> None:
    found = helpers.discover_dockerfiles(discovery_repo)
    assert "services/local-scratch/Dockerfile" not in found


def test_nested_worktrees_dockerfile_is_ignored(discovery_repo: Path) -> None:
    found = helpers.discover_dockerfiles(discovery_repo)
    assert not any(".worktrees/" in path for path in found)
    assert ".worktrees/decoy-branch/services/ws/Dockerfile" not in found
    assert "prefix/.worktrees/nested/Dockerfile" not in found


def test_worktrees_backup_dockerfile_is_ignored(discovery_repo: Path) -> None:
    found = helpers.discover_dockerfiles(discovery_repo)
    assert ".worktrees_backup/old/Dockerfile" not in found
    assert not any(".worktrees_backup/" in path for path in found)


def test_discovery_order_is_deterministic(discovery_repo: Path) -> None:
    first = helpers.discover_dockerfiles(discovery_repo)
    second = helpers.discover_dockerfiles(discovery_repo)
    assert first == second
    assert first == sorted(first)


def test_new_tracked_dockerfile_surface_remains_classification_duty(
    discovery_repo: Path,
) -> None:
    """A newly tracked Dockerfile* must still surface for productive/non-productive SSOT."""
    relative = "services/brand-new/Dockerfile"
    _write(discovery_repo, relative)
    _commit_tracked(discovery_repo, relative)

    found = helpers.discover_dockerfiles(discovery_repo)
    assert relative in found

    known = set(helpers.PRODUCTIVE_IMAGE_DOCKERFILES) | set(
        helpers.NON_PRODUCTIVE_DOCKERFILES
    )
    # Against the real repo SSOT the fixture path is unclassified — that is the
    # contract signal the inventory test guards on the live tree.
    assert relative not in known


def test_tracked_excluded_segments_still_filtered(tmp_path: Path) -> None:
    """Even if a non-canon tree is force-added to the index, discovery drops it."""
    repo = tmp_path / "forced"
    repo.mkdir()
    _init_git_repo(repo)
    _write(repo, "services/ok/Dockerfile")
    _write(repo, ".worktrees/forced/Dockerfile")
    _write(repo, ".worktrees_backup/forced/Dockerfile")
    _write(repo, "third_party/forced/Dockerfile")
    # Bypass ignore rules and force-add pollution into the index.
    _git(
        repo,
        "add",
        "-f",
        "--",
        "services/ok/Dockerfile",
        ".worktrees/forced/Dockerfile",
        ".worktrees_backup/forced/Dockerfile",
        "third_party/forced/Dockerfile",
    )
    _git(repo, "commit", "-m", "force-add excluded dockerfiles")

    found = helpers.discover_dockerfiles(repo)
    assert found == ["services/ok/Dockerfile"]


def test_discover_dockerfiles_fail_closed_outside_git_repo(tmp_path: Path) -> None:
    bare = tmp_path / "not-a-git-repo"
    bare.mkdir()
    _write(bare, "Dockerfile")
    with pytest.raises(RuntimeError, match="cannot enumerate tracked Dockerfiles"):
        helpers.discover_dockerfiles(bare)


def test_live_repo_discovery_matches_git_ls_files_dockerfile_basenames() -> None:
    """Sanity: live checkout discovery stays within the git index."""
    found = helpers.discover_dockerfiles()
    result = subprocess.run(
        [
            "git",
            "-C",
            str(helpers.REPO_ROOT),
            "ls-files",
            "-z",
            "--",
            "*Dockerfile*",
            "*/Dockerfile*",
        ],
        check=True,
        capture_output=True,
    )
    indexed = sorted(
        path.decode("utf-8").replace("\\", "/")
        for path in result.stdout.split(b"\0")
        if path and Path(path.decode("utf-8")).name.startswith("Dockerfile")
    )
    assert found == indexed
