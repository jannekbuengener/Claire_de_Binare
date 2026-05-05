"""Tests for scripts.audit.github_security_quality_readout."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.github_security_quality_readout import (  # noqa: E402
    JSON_FILENAME,
    MARKDOWN_FILENAME,
    REDACTED_SECRET_COMPONENT,
    REDACTED_SECRET_PATH,
    REDACTED_SECRET_RULE,
    REDACTED_SECRET_SUBJECT,
    SurfaceFetchResult,
    build_markdown_report,
    build_readout,
    fetch_surface,
    generate_readout,
    normalize_code_scanning_alert,
    normalize_dependabot_alert,
    normalize_secret_scanning_alert,
)


def _completed_process(
    *,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gh", "api"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class TestNormalizeAlerts:
    def test_normalize_code_scanning_alert(self):
        alert = normalize_code_scanning_alert(
            {
                "number": 12,
                "state": "open",
                "created_at": "2026-03-01T10:00:00Z",
                "updated_at": "2026-03-20T10:00:00Z",
                "html_url": "https://example.invalid/code/12",
                "rule": {
                    "id": "py/path-traversal",
                    "security_severity_level": "high",
                    "name": "Path traversal",
                },
                "most_recent_instance": {
                    "ref": "refs/heads/main",
                    "location": {"path": "core/security/check.py"},
                },
                "tool": {"name": "CodeQL"},
            },
            reference_now=generate_readout.__globals__["_parse_iso8601"](
                "2026-04-23T00:00:00Z"
            ),
        )

        assert alert["source"] == "code_scanning"
        assert alert["severity"] == "high"
        assert alert["rule_or_advisory"] == "py/path-traversal"
        assert alert["affected_path"] == "core/security/check.py"
        assert alert["branch"] == "main"
        assert alert["age_bucket"] == "31-90d"
        assert alert["tool"] == "CodeQL"

    def test_normalize_dependabot_alert(self):
        alert = normalize_dependabot_alert(
            {
                "number": 7,
                "state": "fixed",
                "created_at": "2026-04-20T12:00:00Z",
                "updated_at": "2026-04-21T12:00:00Z",
                "html_url": "https://example.invalid/dependabot/7",
                "dependency": {
                    "manifest_path": "requirements.txt",
                    "package": {"name": "requests"},
                },
                "security_advisory": {
                    "ghsa_id": "GHSA-test-1234",
                    "severity": "medium",
                },
            },
            reference_now=generate_readout.__globals__["_parse_iso8601"](
                "2026-04-23T00:00:00Z"
            ),
        )

        assert alert["source"] == "dependabot"
        assert alert["subject"] == "requests"
        assert alert["rule_or_advisory"] == "GHSA-test-1234"
        assert alert["affected_path"] == "requirements.txt"
        assert alert["branch"] == "not_provided"
        assert alert["severity"] == "medium"
        assert alert["age_bucket"] == "0-7d"

    def test_normalize_secret_scanning_alert(self):
        alert = normalize_secret_scanning_alert(
            {
                "number": 3,
                "state": "resolved",
                "created_at": "2025-12-01T00:00:00Z",
                "updated_at": "2026-01-15T00:00:00Z",
                "html_url": "https://example.invalid/secret/3",
                "secret_type": "generic_api_key",
                "secret_type_display_name": "Generic API Key",
                "first_location_detected": {"path": ".env"},
            },
            reference_now=generate_readout.__globals__["_parse_iso8601"](
                "2026-04-23T00:00:00Z"
            ),
        )

        assert alert["source"] == "secret_scanning"
        assert alert["subject"] == REDACTED_SECRET_SUBJECT
        assert alert["rule_or_advisory"] == REDACTED_SECRET_RULE
        assert alert["affected_path"] == REDACTED_SECRET_PATH
        assert alert["affected_component"] == REDACTED_SECRET_COMPONENT
        assert alert["severity"] == "not_provided"
        assert alert["branch"] == "not_provided"
        assert alert["url"] is None
        assert alert["age_bucket"] == "91d+"


class TestFetchSurface:
    def test_fetch_surface_marks_permission_failure_unavailable(self):
        result = fetch_surface(
            source="dependabot",
            repo="octo/example",
            runner=lambda command: _completed_process(
                returncode=1,
                stderr="gh: HTTP 403: Resource not accessible by integration",
            ),
        )

        assert result.status == "unavailable"
        assert result.alerts == ()
        assert "HTTP 403" in (result.note or "")

    def test_fetch_surface_marks_invalid_page_shape_unavailable(self):
        result = fetch_surface(
            source="code_scanning",
            repo="octo/example",
            runner=lambda command: _completed_process(
                stdout=json.dumps([{"bad": "shape"}])
            ),
        )

        assert result.status == "unavailable"
        assert "page 0 is not a JSON array" in (result.note or "")

    def test_fetch_surface_marks_missing_stdout_unavailable(self):
        result = fetch_surface(
            source="code_scanning",
            repo="octo/example",
            runner=lambda command: subprocess.CompletedProcess(
                args=["gh", "api"],
                returncode=0,
                stdout=None,
                stderr="",
            ),
        )

        assert result.status == "unavailable"
        assert result.note == "gh api returned no stdout payload"

    def test_fetch_surface_redacts_secret_scanning_payload_before_persistence(self):
        def _runner_must_not_be_called(*_args, **_kwargs):
            raise AssertionError("runner must not be called for secret_scanning")

        result = fetch_surface(
            source="secret_scanning",
            repo="octo/example",
            runner=_runner_must_not_be_called,
        )

        assert result.status == "redacted"
        assert result.alert_count is None
        assert result.alerts == ()
        assert "not-fetched" in (result.note or "")


class TestReadoutGeneration:
    def test_build_readout_is_partial_when_a_surface_is_unavailable(self):
        readout = build_readout(
            repo="octo/example",
            reference_now_utc="2026-04-23T00:00:00Z",
            fetched_surfaces=[
                SurfaceFetchResult(
                    source="code_scanning",
                    endpoint="repos/octo/example/code-scanning/alerts?per_page=100",
                    status="readable",
                    alerts=(
                        {
                            "number": 1,
                            "state": "open",
                            "created_at": "2026-04-22T00:00:00Z",
                            "updated_at": "2026-04-22T00:00:00Z",
                            "rule": {
                                "id": "py/sql-injection",
                                "security_severity_level": "critical",
                            },
                            "most_recent_instance": {
                                "ref": "refs/heads/main",
                                "location": {"path": "app/db.py"},
                            },
                            "tool": {"name": "CodeQL"},
                        },
                    ),
                ),
                SurfaceFetchResult(
                    source="dependabot",
                    endpoint="repos/octo/example/dependabot/alerts?per_page=100",
                    status="unavailable",
                    alerts=(),
                    note="HTTP 403",
                ),
                SurfaceFetchResult(
                    source="secret_scanning",
                    endpoint="repos/octo/example/secret-scanning/alerts?per_page=100",
                    status="readable",
                    alerts=(),
                ),
            ],
        )

        assert readout["status"] == "PARTIAL"
        assert readout["readable_surface_count"] == 2
        assert readout["summary"]["total_alerts"] == 1
        assert readout["summary"]["counts_by_source"] == [
            {"value": "code_scanning", "count": 1}
        ]

        markdown = build_markdown_report(readout)
        assert "Dieses Bild ist partiell." in markdown
        assert "`dependabot`: HTTP 403" in markdown

    def test_markdown_report_mentions_secret_scanning_redaction(self):
        readout = build_readout(
            repo="octo/example",
            reference_now_utc="2026-04-23T00:00:00Z",
            fetched_surfaces=[
                SurfaceFetchResult(
                    source="code_scanning",
                    endpoint="repos/octo/example/code-scanning/alerts?per_page=100",
                    status="readable",
                    alerts=(),
                ),
                SurfaceFetchResult(
                    source="dependabot",
                    endpoint="repos/octo/example/dependabot/alerts?per_page=100",
                    status="readable",
                    alerts=(),
                ),
                SurfaceFetchResult(
                    source="secret_scanning",
                    endpoint="repos/octo/example/secret-scanning/alerts?per_page=100",
                    status="redacted",
                    alerts=(),
                ),
            ],
        )

        assert readout["summary"]["total_alerts"] == 0
        assert readout["summary"]["counts_by_source"] == []
        assert readout["summary"]["counts_by_state"] == []
        assert readout["summary"]["counts_by_severity"] == []
        assert readout["alerts"] == []

        markdown = build_markdown_report(readout)
        assert "Secret-Scanning bleibt in der Surface-Coverage sichtbar" in markdown
        assert (
            "Secret-Scanning-Detailfelder werden im Artefakt absichtlich redigiert"
            in markdown
        )
        assert "| `secret_scanning` | redacted | redacted |" in markdown

    def test_generate_readout_writes_deterministic_artifacts(self, tmp_path):
        pages_by_source = {
            "code_scanning": [
                {
                    "number": 10,
                    "state": "open",
                    "created_at": "2026-04-10T00:00:00Z",
                    "updated_at": "2026-04-12T00:00:00Z",
                    "html_url": "https://example.invalid/code/10",
                    "rule": {
                        "id": "py/insecure-temp-file",
                        "security_severity_level": "medium",
                    },
                    "most_recent_instance": {
                        "ref": "refs/heads/main",
                        "location": {"path": "core/tmp.py"},
                    },
                    "tool": {"name": "CodeQL"},
                }
            ],
            "dependabot": [
                {
                    "number": 11,
                    "state": "open",
                    "created_at": "2026-04-11T00:00:00Z",
                    "updated_at": "2026-04-12T00:00:00Z",
                    "html_url": "https://example.invalid/dependabot/11",
                    "dependency": {
                        "manifest_path": "requirements.txt",
                        "package": {"name": "urllib3"},
                    },
                    "security_advisory": {
                        "ghsa_id": "GHSA-test-5678",
                        "severity": "high",
                    },
                }
            ],
        }

        _secret_scanning_calls = []

        def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
            endpoint = command[-1]
            if "secret-scanning" in endpoint:
                _secret_scanning_calls.append(command)
                raise AssertionError("secret_scanning must not call runner")
            for source, page in pages_by_source.items():
                if (
                    f"/{source.replace('_', '-')}/" in endpoint
                    or source == "code_scanning"
                    and "/code-scanning/" in endpoint
                ):
                    return _completed_process(stdout=json.dumps([page]))
            raise AssertionError(f"Unexpected command endpoint: {endpoint}")

        out_dir_a = tmp_path / "out_a"
        out_dir_b = tmp_path / "out_b"
        reference_now = "2026-04-23T00:00:00Z"

        first = generate_readout(
            repo="octo/example",
            out_dir=out_dir_a,
            reference_now_utc=reference_now,
            runner=runner,
        )
        second = generate_readout(
            repo="octo/example",
            out_dir=out_dir_b,
            reference_now_utc=reference_now,
            runner=runner,
        )

        assert first == second
        assert first["status"] == "PASS"
        assert first["summary"]["total_alerts"] == 2
        assert not _secret_scanning_calls
        assert len(first["alerts"]) == 2
        assert first["summary"]["counts_by_source"] == [
            {"value": "code_scanning", "count": 1},
            {"value": "dependabot", "count": 1},
        ]
        assert first["summary"]["counts_by_state"] == [{"value": "open", "count": 2}]
        assert first["summary"]["counts_by_severity"] == [
            {"value": "high", "count": 1},
            {"value": "medium", "count": 1},
        ]
        exported = json.loads((out_dir_a / JSON_FILENAME).read_text(encoding="utf-8"))
        secret_surface = next(
            surface
            for surface in exported["surfaces"]
            if surface["source"] == "secret_scanning"
        )
        assert secret_surface["alert_count"] is None
        assert (out_dir_a / JSON_FILENAME).read_text(encoding="utf-8") == (
            out_dir_b / JSON_FILENAME
        ).read_text(encoding="utf-8")
        assert (out_dir_a / MARKDOWN_FILENAME).read_text(encoding="utf-8") == (
            out_dir_b / MARKDOWN_FILENAME
        ).read_text(encoding="utf-8")
