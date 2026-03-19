"""Tests for render_branch_protection_reapply_prompt.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from render_branch_protection_reapply_prompt import main, render_document


def test_render_document_uses_saved_branch_protection_inputs(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    payload_path = tmp_path / "payload.json"

    baseline = {
        "required_signatures": {"enabled": False},
    }
    payload = {
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews": False,
            "require_code_owner_reviews": False,
            "require_last_push_approval": False,
        },
        "required_status_checks": {
            "strict": True,
            "checks": [
                {"context": "ci (Unit/Integration + Lint gesammelt)", "app_id": 15368}
            ],
        },
        "required_conversation_resolution": True,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "lock_branch": False,
        "allow_fork_syncing": False,
        "restrictions": None,
    }

    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    document = render_document(
        repo="example/repo",
        branch="main",
        baseline_path=baseline_path,
        apply_payload_path=payload_path,
        baseline=baseline,
        apply_payload=payload,
    )

    assert "Branch Protection Re-Apply Prompt (main)" in document
    assert "Rulesets are explicitly out of scope for this re-apply path" in document
    assert "Include administrators: `ON`" in document
    assert "Required approving reviews: `0`" in document
    assert "- ci (Unit/Integration + Lint gesammelt) (app_id=15368)" in document
    assert "Require signed commits: `OFF`" in document
    assert "gh api --method PUT repos/example/repo/branches/main/protection" in document


def test_main_writes_prompt_for_current_repo_saved_files(
    tmp_path: Path, monkeypatch
) -> None:
    output_path = tmp_path / "prompt.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "render_branch_protection_reapply_prompt.py",
            "--out",
            str(output_path),
        ],
    )

    assert main() == 0
    text = output_path.read_text(encoding="utf-8")

    assert "Repo: `jannekbuengener/Claire_de_Binare`" in text
    assert "Branch: `main`" in text
    assert "ci (Unit/Integration + Lint gesammelt)" in text
    assert "Do not touch merge methods, repository rulesets" in text
