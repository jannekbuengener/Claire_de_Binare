from __future__ import annotations


from src import get_version, project_root


def test_package_version_and_root() -> None:
    version = get_version()
    root = project_root()

    assert version.count(".") == 2, "Version should follow semantic x.y.z"
    assert root.exists(), "Project root must exist"
    assert (root / "backoffice").is_dir(), "Backoffice directory missing"
