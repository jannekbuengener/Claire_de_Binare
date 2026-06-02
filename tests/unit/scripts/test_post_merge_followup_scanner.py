from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
SCANNER_PATH = REPO_ROOT / ".github" / "scripts" / "post_merge_followup_scanner.py"

_SPEC = importlib.util.spec_from_file_location("post_merge_followup_scanner", SCANNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


# ---------------------------------------------------------------------------
# Rate-Limit Detection
# ---------------------------------------------------------------------------


RATE_LIMIT_HTML_STDERR = """Error: rate limited: <html>
  <head>
    <title>Rate limit &middot; GitHub</title>
  </head>
  <body>
    <div class="c">
      <h1>Whoa there!</h1>
      <p>You have triggered an abuse detection mechanism.<br><br>
        Please wait a few minutes before you try again;<br>
        in some cases this may take up to an hour.
      </p>
    </div>
  </body>
</html> (retry after 1m0s)"""

RATE_LIMIT_SHORT_STDERR = "Error: rate limited (retry after 30s)"


def test_is_gh_models_rate_limit_error_detects_html_rate_limit() -> None:
    assert scanner.is_gh_models_rate_limit_error(RATE_LIMIT_HTML_STDERR)


def test_is_gh_models_rate_limit_error_detects_short() -> None:
    assert scanner.is_gh_models_rate_limit_error(RATE_LIMIT_SHORT_STDERR)


def test_is_gh_models_rate_limit_error_detects_abuse_detection() -> None:
    stderr = "You have triggered an abuse detection mechanism."
    assert scanner.is_gh_models_rate_limit_error(stderr)


def test_is_gh_models_rate_limit_error_detects_retry_after() -> None:
    stderr = "something went wrong (retry after 2m0s)"
    assert scanner.is_gh_models_rate_limit_error(stderr)


def test_is_gh_models_rate_limit_error_returns_false_for_other_errors() -> None:
    stderr = "Error: model 'gpt-42' not found"
    assert not scanner.is_gh_models_rate_limit_error(stderr)


def test_is_gh_models_rate_limit_error_returns_false_for_empty() -> None:
    assert not scanner.is_gh_models_rate_limit_error("")
    assert not scanner.is_gh_models_rate_limit_error(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Retry-After Parsing
# ---------------------------------------------------------------------------


def test_parse_retry_after_seconds_1m0s() -> None:
    assert scanner._parse_retry_after_seconds("(retry after 1m0s)") == 60


def test_parse_retry_after_seconds_30s() -> None:
    assert scanner._parse_retry_after_seconds("(retry after 30s)") == 30


def test_parse_retry_after_seconds_5m30s_capped() -> None:
    assert scanner._parse_retry_after_seconds("(retry after 5m30s)") == 120


def test_parse_retry_after_seconds_fallback() -> None:
    assert scanner._parse_retry_after_seconds("unknown format") == 60


# ---------------------------------------------------------------------------
# run_models_with_retry — bounded retry behavior
# ---------------------------------------------------------------------------


def test_run_models_with_retry_succeeds_on_first_attempt(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"classification":"report_only","confidence":0.8,"affected_artifacts":["a"],"suggested_next_step":"none"}'
        )

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    prompt_file = Path("/fake/prompt.yml")
    result = scanner.run_models_with_retry(prompt_file, "test input")
    assert "report_only" in result


def test_run_models_with_retry_succeeds_on_retry(monkeypatch) -> None:
    attempts: list[int] = []

    def fake_run(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            return subprocess.CompletedProcess(
                args=[], returncode=1, stderr="Error: rate limited (retry after 1s)"
            )
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"classification":"follow_up_issue","confidence":0.9,"affected_artifacts":["b"],"suggested_next_step":"create issue"}'
        )

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    prompt_file = Path("/fake/prompt.yml")
    result = scanner.run_models_with_retry(prompt_file, "test input", max_retries=2)
    assert "follow_up_issue" in result
    assert len(attempts) == 2


def test_run_models_with_retry_raises_models_rate_limited_after_exhaustion(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=1, stderr="Error: rate limited (retry after 1s)"
        )

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    prompt_file = Path("/fake/prompt.yml")
    with pytest.raises(scanner.ModelsRateLimitedError, match="rate-limited after"):
        scanner.run_models_with_retry(prompt_file, "test input", max_retries=2)


def test_run_models_with_retry_non_rate_limit_error_raises_runtime_error(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=1, stderr="Error: invalid model name"
        )

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    prompt_file = Path("/fake/prompt.yml")
    with pytest.raises(RuntimeError, match="command failed"):
        scanner.run_models_with_retry(prompt_file, "test input", max_retries=3)


# ---------------------------------------------------------------------------
# build_summary — degraded status
# ---------------------------------------------------------------------------


def test_build_summary_degraded_rate_limited() -> None:
    pr = {"number": 2782, "title": "test", "url": "https://github.com/test/test/pull/2782"}
    result = {
        "repo": "test/test",
        "publish_mode": "dry_run",
        "pr": pr,
        "status": "degraded_rate_limited",
        "candidate_count": 1,
        "findings": [
            {
                "rule_id": "discovery_surface_drift",
                "title": "test finding",
                "fingerprint": "abc123",
                "classification": {
                    "classification": "unclear",
                    "confidence": 0.0,
                    "affected_artifacts": ["a.yaml"],
                    "suggested_next_step": "No model classification available",
                },
                "degraded_reason": "rate_limited",
                "trigger_files": ["a.yaml"],
                "affected_candidates": ["a.yaml"],
                "evidence_lines": [],
                "issue_title": "test",
                "labels": ["scope:docs"],
                "force_follow_up_issue": False,
            }
        ],
        "control_comment": None,
    }
    summary = scanner.build_summary(result)
    assert "degraded_rate_limited" in summary
    assert "Rate Limited" in summary
    assert "No model classification" in summary
    assert "No blind follow-up" in summary
    assert "degraded" in summary.lower()


def test_build_summary_completed_no_degraded_section() -> None:
    pr = {"number": 2782, "title": "test", "url": "https://github.com/test/test/pull/2782"}
    result = {
        "repo": "test/test",
        "publish_mode": "dry_run",
        "pr": pr,
        "status": "completed",
        "candidate_count": 0,
        "findings": [],
        "control_comment": None,
    }
    summary = scanner.build_summary(result)
    assert "degraded" not in summary.lower()
    assert "No repo-backed follow-up" in summary


def _make_pr(number: int, title: str, *paths: str) -> dict[str, object]:
    return {
        "number": number,
        "url": f"https://github.com/jannekbuengener/Claire_de_Binare/pull/{number}",
        "title": title,
        "files": [{"path": path} for path in paths],
    }


def _rule_ids(findings: list[object]) -> set[str]:
    return {finding.rule_id for finding in findings}


def test_digest_only_compose_pin_does_not_trigger_architecture_followup() -> None:
    pr = _make_pr(
        1719,
        "fix(security): pin postgres:15.17-alpine to rebuild digest",
        "infrastructure/compose/compose.blue.yml",
        "infrastructure/compose/base.yml",
        ".github/workflows/security-scan.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -17,7 +17,7 @@ services:
-    image: postgres:15.17-alpine
+    image: postgres:15.17-alpine@sha256:1c52f5ad23db5d7648a63634444af76de48e63b860fccbe3e3a5458b2812eaed
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" not in _rule_ids(findings)


def test_digest_only_dockerfile_pin_does_not_trigger_architecture_followup() -> None:
    pr = _make_pr(
        1722,
        "fix(security): pin python:3.11-slim-trixie to rebuild digest",
        "services/allocation/Dockerfile",
        "services/execution/Dockerfile",
    )
    diff_text = """\
diff --git a/services/allocation/Dockerfile b/services/allocation/Dockerfile
+++ b/services/allocation/Dockerfile
@@ -1,4 +1,4 @@
-FROM python:3.11-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39
+FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf
diff --git a/services/execution/Dockerfile b/services/execution/Dockerfile
+++ b/services/execution/Dockerfile
@@ -1,6 +1,6 @@
-FROM python:3.11-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39 AS build
+FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf AS build
@@ -21,7 +21,7 @@
-FROM python:3.11-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39
+FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" not in _rule_ids(findings)


def test_image_swaps_do_not_count_as_digest_only_change() -> None:
    pr = _make_pr(
        2003,
        "refactor(runtime): swap images between services",
        "infrastructure/compose/compose.blue.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -10,8 +10,8 @@ services:
-    image: service-a:1.0.0@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
-    image: service-b:2.0.0@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
+    image: service-b:2.0.0@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
+    image: service-a:1.0.0@sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" in _rule_ids(findings)


def test_tag_change_still_triggers_architecture_followup() -> None:
    pr = _make_pr(
        2001,
        "fix(security): move postgres to new tag",
        "infrastructure/compose/compose.blue.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -17,7 +17,7 @@ services:
-    image: postgres:15.17-alpine@sha256:1c52f5ad23db5d7648a63634444af76de48e63b860fccbe3e3a5458b2812eaed
+    image: postgres:15.18-alpine@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" in _rule_ids(findings)


def test_new_service_surface_still_triggers_architecture_followup() -> None:
    pr = _make_pr(
        2002,
        "feat(runtime): add operator sidecar",
        "infrastructure/compose/compose.blue.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -30,0 +31,4 @@ services:
+  cdb_sidecar:
+    image: busybox:1.36.1@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
+    container_name: cdb_sidecar
+    restart: unless-stopped
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" in _rule_ids(findings)
