from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from tools.arvp_github_reporter import (
    GitHubReporter,
    _format_probe_table,
    _git_branch_name,
    _should_comment_3087,
    pr_body,
    render_body,
    render_chain_found,
    render_timeout_no_chain,
    render_interrupted,
    render_blocked,
    render_merged,
    STATE_CHAIN_FOUND,
    STATE_TIMEOUT_NO_CHAIN,
    STATE_INTERRUPTED,
    STATE_BLOCKED_RUNTIME,
    STATE_BLOCKED_DB_READONLY,
    STATE_BLOCKED_GOVERNANCE,
    STATE_EVIDENCE_MERGED,
    ISSUE_CAMPAIGN,
    ISSUE_REFERENCE_WINDOW,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _manifest(**overrides: object) -> dict:
    base = {
        "schema_version": "1.0",
        "campaign_id": "arvp_3095_vol_window_3_20260611_0800",
        "parent_issue": 3095,
        "symbol": "BTCUSDT",
        "strategy_id": "primary_breakout_v1",
        "evidence_class": "natural_paper_evidence",
        "evidence_doc": "docs/evidence/arvp_test.md",
        "evidence_log_jsonl": "artifacts/campaigns/test/evidence_log.jsonl",
        "github_reporting": {
            "post_on_issue_3095": True,
            "post_on_issue_3087": False,
            "post_on_issue_3102": False,
            "pr_create_on_chain_found": True,
            "issue_close_after_acceptance": False,
        },
        "start_utc": "2026-06-11T08:00:00Z",
        "timeout_utc": "2026-06-11T16:00:00Z",
        "max_duration_hours": 8.0,
        "start_criteria": {"pre_documented": True},
        "safety_flags": {
            "mock_trading": True,
            "use_real_balance": False,
            "dry_run": True,
            "mexc_testnet": True,
        },
        "runtime_targets": ["cdb_execution"],
        "db_readonly_targets": ["public.correlation_ledger"],
        "allowed_statuses": ["running", "chain_found"],
        "terminal_statuses": ["chain_found"],
    }
    base.update(overrides)
    return base


def _entry(state: str, **overrides: object) -> dict:
    base = {
        "observed_at_utc": "2026-06-11T12:00:00Z",
        "cycle": 12,
        "campaign_id": "arvp_3095_vol_window_3_20260611_0800",
        "state": state,
        "probe_statuses": {
            "host": "ok",
            "docker": "ok",
            "safety": "ok",
            "db_readonly": "ok",
            "candles": "ok",
            "correlation_ledger": "ok",
            "regime": "ok",
        },
        "event_count_since_start": 4,
        "chain_detected": state == STATE_CHAIN_FOUND,
        "no_mutation": True,
        "limitations": [],
    }
    if state == STATE_CHAIN_FOUND:
        base["chain_details"] = {
            "chain_status": "complete_chain",
            "complete": True,
            "event_count": 4,
            "event_ids": [101, 102, 103, 104],
            "first_event_ts": "2026-06-11T11:45:00Z",
            "last_event_ts": "2026-06-11T11:46:30Z",
            "missing_steps": [],
            "observed_types": ["SIGNAL", "DECISION", "ORDER", "FILL"],
            "export_trigger": {"export_candidate": True},
        }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Template rendering
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderChainFound:
    def test_contains_key_fields(self):
        entry = _entry(STATE_CHAIN_FOUND)
        body = render_chain_found(entry, _manifest())
        assert "CHAIN_FOUND" in body
        assert "101, 102, 103, 104" in body
        assert "2026-06-11T11:45:00Z" in body
        assert "LR remains NO-GO" in body

    def test_contains_evidence_paths(self):
        entry = _entry(STATE_CHAIN_FOUND)
        manifest = _manifest(
            evidence_doc="docs/evidence/arvp_test.md",
            evidence_log_jsonl="artifacts/campaigns/test/log.jsonl",
        )
        body = render_chain_found(entry, manifest)
        assert "docs/evidence/arvp_test.md" in body
        assert "artifacts/campaigns/test/log.jsonl" in body

    def test_no_issue_closure_in_body(self):
        entry = _entry(STATE_CHAIN_FOUND)
        body = render_chain_found(entry, _manifest())
        assert "Closes #" not in body
        assert "closes #" not in body

    def test_no_event_ids_graceful(self):
        entry = _entry(STATE_CHAIN_FOUND, chain_details={"event_ids": []})
        body = render_chain_found(entry, _manifest())
        assert "none" in body or "event_ids" not in body


@pytest.mark.unit
class TestRenderTimeoutNoChain:
    def test_contains_classification(self):
        entry = _entry(STATE_TIMEOUT_NO_CHAIN)
        body = render_timeout_no_chain(entry, _manifest())
        assert "TIMEOUT_NO_CHAIN" in body
        assert "campaign_timeout_record" in body
        assert "counts as failure" in body
        assert "LR remains NO-GO" in body

    def test_probe_table_rendered(self):
        entry = _entry(STATE_TIMEOUT_NO_CHAIN)
        body = render_timeout_no_chain(entry, _manifest())
        assert "| Probe | Status |" in body
        assert "| host | ok |" in body

    def test_no_issue_closure(self):
        body = render_timeout_no_chain(_entry(STATE_TIMEOUT_NO_CHAIN), _manifest())
        assert "Closes #" not in body


@pytest.mark.unit
class TestRenderInterrupted:
    def test_contains_classification(self):
        entry = _entry(STATE_INTERRUPTED)
        body = render_interrupted(entry, _manifest())
        assert "INTERRUPTED" in body
        assert "interruption_record" in body
        assert "does NOT count as failure" in body
        assert "LR remains NO-GO" in body

    def test_no_issue_closure(self):
        body = render_interrupted(_entry(STATE_INTERRUPTED), _manifest())
        assert "Closes #" not in body


@pytest.mark.unit
class TestRenderBlocked:
    @pytest.mark.parametrize(
        "state",
        [
            STATE_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE,
        ],
    )
    def test_contains_blocked_info(self, state: str):
        entry = _entry(state)
        body = render_blocked(entry, _manifest())
        assert state in body
        assert "LR remains NO-GO" in body

    def test_blocking_probe_listed(self):
        entry = _entry(
            STATE_BLOCKED_RUNTIME,
            probe_statuses={"docker": "blocked", "host": "ok"},
        )
        body = render_blocked(entry, _manifest())
        assert "docker" in body

    def test_no_issue_closure(self):
        body = render_blocked(_entry(STATE_BLOCKED_RUNTIME), _manifest())
        assert "Closes #" not in body


@pytest.mark.unit
class TestRenderMerged:
    def test_contains_merge_info(self):
        entry = _entry(
            STATE_EVIDENCE_MERGED,
            pr_url="https://github.com/example/repo/pull/42",
            merge_sha="abc123def456",
        )
        body = render_merged(entry, _manifest())
        assert "EVIDENCE_MERGED" not in body
        assert "Merged" in body
        assert "abc123def456" in body
        assert "LR remains NO-GO" in body
        assert "No Echtgeld claim" in body

    def test_no_issue_closure(self):
        entry = _entry(STATE_EVIDENCE_MERGED, pr_url="?", merge_sha="?")
        body = render_merged(entry, _manifest())
        assert "Closes #" not in body


@pytest.mark.unit
class TestRenderBody:
    def test_unknown_state_raises(self):
        with pytest.raises(ValueError, match="unknown state"):
            render_body("BOGUS_STATE", _entry("BOGUS_STATE"), _manifest())

    def test_dispatches_correctly(self):
        for state in [
            STATE_CHAIN_FOUND,
            STATE_TIMEOUT_NO_CHAIN,
            STATE_INTERRUPTED,
            STATE_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE,
            STATE_EVIDENCE_MERGED,
        ]:
            body = render_body(state, _entry(state), _manifest())
            assert isinstance(body, str)
            assert len(body) > 20

    def test_all_templates_have_lr_no_go(self):
        for state in [
            STATE_CHAIN_FOUND,
            STATE_TIMEOUT_NO_CHAIN,
            STATE_INTERRUPTED,
            STATE_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE,
            STATE_EVIDENCE_MERGED,
        ]:
            body = render_body(state, _entry(state), _manifest())
            assert "LR remains NO-GO" in body, f"missing LR NO-GO in {state}"


# ---------------------------------------------------------------------------
# 2. Safety: forbidden patterns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSafetyNoForbiddenPatterns:
    FORBIDDEN = [
        "gh issue close",
        "gh pr merge",
        "Closes #3095",
        "Closes #3087",
        "INSERT",
        "UPDATE",
        "DELETE",
        "USE_REAL_BALANCE=true",
        "MOCK_TRADING=false",
        "DRY_RUN=false",
        "MEXC_TESTNET=false",
    ]

    @pytest.mark.parametrize(
        "state",
        [
            STATE_CHAIN_FOUND,
            STATE_TIMEOUT_NO_CHAIN,
            STATE_INTERRUPTED,
            STATE_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE,
            STATE_EVIDENCE_MERGED,
        ],
    )
    def test_no_forbidden_in_template(self, state: str):
        body = render_body(state, _entry(state), _manifest())
        for pat in self.FORBIDDEN:
            assert pat not in body, f"found '{pat}' in {state} template"

    def test_no_forbidden_in_pr_body(self):
        entry = _entry(STATE_CHAIN_FOUND)
        body = pr_body("test_campaign", "CHAIN_FOUND", entry, "doc.md", "log.jsonl")
        for pat in self.FORBIDDEN:
            assert pat not in body, f"found '{pat}' in PR body"


# ---------------------------------------------------------------------------
# 3. Utilities
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatProbeTable:
    def test_empty_dict(self):
        assert _format_probe_table({}) == "*No probe data*"

    def test_renders_table(self):
        result = _format_probe_table({"host": "ok", "docker": "ok"})
        assert "| Probe | Status |" in result
        assert "| host | ok |" in result
        assert "| docker | ok |" in result


@pytest.mark.unit
class TestShouldComment3087:
    def test_chain_found_returns_true(self):
        assert _should_comment_3087(STATE_CHAIN_FOUND, 0) is True

    def test_timeout_with_3_failures_returns_true(self):
        assert _should_comment_3087(STATE_TIMEOUT_NO_CHAIN, 3) is True

    def test_timeout_with_2_failures_returns_false(self):
        assert _should_comment_3087(STATE_TIMEOUT_NO_CHAIN, 2) is False

    def test_timeout_with_0_failures_returns_false(self):
        assert _should_comment_3087(STATE_TIMEOUT_NO_CHAIN, 0) is False

    def test_interrupted_returns_false(self):
        assert _should_comment_3087(STATE_INTERRUPTED, 0) is False

    def test_blocked_returns_false(self):
        assert _should_comment_3087(STATE_BLOCKED_RUNTIME, 0) is False


@pytest.mark.unit
class TestGitBranchName:
    def test_chain_found(self):
        name = _git_branch_name(
            "arvp_3095_vol_window_3_20260611_0800", STATE_CHAIN_FOUND
        )
        assert name == "evidence/arvp-arvp_3095_vol_window_3_20260611_0800-chain_found"

    def test_sanitizes_slashes(self):
        name = _git_branch_name("campaign/id/1", STATE_CHAIN_FOUND)
        assert "/" not in name.replace("evidence/", "", 1)

    def test_lowercases_state(self):
        name = _git_branch_name("test", STATE_BLOCKED_RUNTIME)
        assert "BLOCKED" not in name
        assert "blocked_runtime" in name


# ---------------------------------------------------------------------------
# 4. PR body
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrBody:
    def test_contains_campaign_info(self):
        entry = _entry(STATE_CHAIN_FOUND)
        body = pr_body("test_campaign", "CHAIN_FOUND", entry, "doc.md", "log.jsonl")
        assert "test_campaign" in body
        assert "CHAIN_FOUND" in body
        assert "doc.md" in body
        assert "log.jsonl" in body
        assert "#3102" in body

    def test_no_issue_closure_in_pr_body(self):
        entry = _entry(STATE_CHAIN_FOUND)
        body = pr_body("test_campaign", "CHAIN_FOUND", entry, "doc.md", "log.jsonl")
        assert "Closes #" not in body

    def test_lr_no_go_present(self):
        entry = _entry(STATE_CHAIN_FOUND)
        body = pr_body("test_campaign", "CHAIN_FOUND", entry, "doc.md", "log.jsonl")
        assert "LR remains NO-GO" in body
        assert "No Echtgeld claim" in body


# ---------------------------------------------------------------------------
# 5. GitHubReporter: construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitHubReporterInit:
    def test_create_pr_requires_github_write(self):
        with pytest.raises(ValueError, match="--create-pr requires --github-write"):
            GitHubReporter(_manifest(), github_write=False, create_pr=True)

    def test_create_pr_with_github_write_ok(self):
        reporter = GitHubReporter(_manifest(), github_write=True, create_pr=True)
        assert reporter._create_pr is True
        assert reporter._github_write is True

    def test_default_dry_run(self):
        reporter = GitHubReporter(_manifest())
        assert reporter._github_write is False
        assert reporter._create_pr is False

    def test_reads_github_reporting_from_manifest(self):
        manifest = _manifest(
            github_reporting={
                "post_on_issue_3095": False,
                "post_on_issue_3087": True,
                "post_on_issue_3102": True,
                "pr_create_on_chain_found": False,
            }
        )
        reporter = GitHubReporter(manifest)
        assert reporter._post_3095 is False
        assert reporter._post_3087 is True
        assert reporter._post_3102 is True
        assert reporter._pr_on_chain is False


# ---------------------------------------------------------------------------
# 6. GitHubReporter: issue target resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveTargets:
    def test_chain_found_includes_3087(self):
        reporter = GitHubReporter(
            _manifest(
                github_reporting={
                    "post_on_issue_3095": True,
                    "post_on_issue_3087": True,
                }
            )
        )
        targets = reporter._resolve_targets(STATE_CHAIN_FOUND, 0)
        assert ISSUE_CAMPAIGN in targets
        assert ISSUE_REFERENCE_WINDOW in targets

    def test_timeout_no_chain_excludes_3087_below_3(self):
        reporter = GitHubReporter(
            _manifest(
                github_reporting={
                    "post_on_issue_3095": True,
                    "post_on_issue_3087": True,
                }
            )
        )
        targets = reporter._resolve_targets(STATE_TIMEOUT_NO_CHAIN, 2)
        assert ISSUE_CAMPAIGN in targets
        assert ISSUE_REFERENCE_WINDOW not in targets

    def test_timeout_no_chain_includes_3087_at_3(self):
        reporter = GitHubReporter(
            _manifest(
                github_reporting={
                    "post_on_issue_3095": True,
                    "post_on_issue_3087": True,
                }
            )
        )
        targets = reporter._resolve_targets(STATE_TIMEOUT_NO_CHAIN, 3)
        assert ISSUE_REFERENCE_WINDOW in targets

    def test_3095_disabled_via_manifest(self):
        reporter = GitHubReporter(
            _manifest(
                github_reporting={
                    "post_on_issue_3095": False,
                }
            )
        )
        targets = reporter._resolve_targets(STATE_CHAIN_FOUND, 0)
        assert ISSUE_CAMPAIGN not in targets

    def test_3087_disabled_via_manifest(self):
        reporter = GitHubReporter(
            _manifest(
                github_reporting={
                    "post_on_issue_3087": False,
                }
            )
        )
        targets = reporter._resolve_targets(STATE_CHAIN_FOUND, 0)
        assert ISSUE_REFERENCE_WINDOW not in targets


# ---------------------------------------------------------------------------
# 7. GitHubReporter: report_terminal behavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReportTerminal:
    def test_non_terminal_state_raises(self):
        reporter = GitHubReporter(_manifest())
        with pytest.raises(ValueError, match="non-terminal state"):
            reporter.report_terminal({"state": "RUNNING"})

    def test_dry_run_returns_dry_run_actions(self):
        reporter = GitHubReporter(_manifest())
        results = reporter.report_terminal(_entry(STATE_TIMEOUT_NO_CHAIN))
        assert len(results) >= 1
        for r in results:
            assert r["action"].startswith("dry_run_")

    def test_dry_run_does_not_call_subprocess(self):
        reporter = GitHubReporter(_manifest())
        with patch("subprocess.run") as mock_run:
            reporter.report_terminal(_entry(STATE_TIMEOUT_NO_CHAIN))
            mock_run.assert_not_called()

    def test_github_write_calls_subprocess(self):
        reporter = GitHubReporter(_manifest(), github_write=True)
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "https://github.com/comment/1"
            mock_run.return_value = mock_result

            results = reporter.report_terminal(_entry(STATE_TIMEOUT_NO_CHAIN))

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "gh"
            assert args[1] == "issue"
            assert args[2] == "comment"
            assert args[3] == str(ISSUE_CAMPAIGN)

    def test_chain_found_includes_pr_dry_run(self):
        reporter = GitHubReporter(_manifest())
        results = reporter.report_terminal(_entry(STATE_CHAIN_FOUND))
        pr_results = [r for r in results if "pr" in r.get("action", "")]
        assert len(pr_results) >= 1
        assert pr_results[0]["action"] == "dry_run_pr"

    def test_chain_found_with_create_pr_calls_subprocess(self):
        reporter = GitHubReporter(_manifest(), github_write=True, create_pr=True)
        with (
            patch("subprocess.run") as mock_run,
            patch("os.path.isfile", return_value=False),
        ):
            mock_comment = MagicMock()
            mock_comment.returncode = 0
            mock_comment.stdout = "https://github.com/comment/1"

            mock_ok = MagicMock()
            mock_ok.returncode = 0
            mock_ok.stdout = ""

            mock_fail = MagicMock()
            mock_fail.returncode = 1
            mock_fail.stdout = ""

            # subprocess calls: gh comment, git rev-parse, checkout -b,
            # commit, push, gh pr create, checkout main
            mock_run.side_effect = [
                mock_comment,  # gh issue comment (to #3095)
                mock_fail,  # git rev-parse --verify (branch doesn't exist)
                mock_ok,  # git checkout -b
                mock_ok,  # git commit
                mock_ok,  # git push
                mock_ok,  # gh pr create
                mock_ok,  # git checkout main
            ]

            results = reporter.report_terminal(_entry(STATE_CHAIN_FOUND))

            pr_results = [r for r in results if r.get("action") == "pr_created"]
            assert len(pr_results) == 1

    def test_chain_found_pr_skipped_if_branch_exists(self):
        reporter = GitHubReporter(_manifest(), github_write=True, create_pr=True)
        with patch("subprocess.run") as mock_run:
            mock_ok = MagicMock()
            mock_ok.returncode = 0
            mock_ok.stdout = "abc123"

            mock_run.return_value = mock_ok

            results = reporter.report_terminal(_entry(STATE_CHAIN_FOUND))

            pr_results = [r for r in results if "pr" in r.get("action", "")]
            assert len(pr_results) == 1
            assert pr_results[0]["action"] == "pr_skipped"

    def test_chain_found_pr_create_failure_returns_error(self):
        reporter = GitHubReporter(_manifest(), github_write=True, create_pr=True)
        with (
            patch("subprocess.run") as mock_run,
            patch("os.path.isfile", return_value=False),
        ):
            mock_comment = MagicMock()
            mock_comment.returncode = 0
            mock_comment.stdout = "https://github.com/comment/1"

            mock_fail = MagicMock()
            mock_fail.returncode = 1
            mock_fail.stdout = ""
            mock_fail.stderr = "push rejected"

            mock_ok = MagicMock()
            mock_ok.returncode = 0
            mock_ok.stdout = ""

            # mock subprocess does not enforce check=True,
            # so git push failure does not raise CalledProcessError
            # Sequence: gh comment, rev-parse, checkout, commit,
            #           push(rc=1), gh pr create(rc=1), checkout main
            mock_run.side_effect = [
                mock_comment,  # gh issue comment (to #3095)
                mock_fail,  # git rev-parse (branch doesn't exist)
                mock_ok,  # git checkout -b
                mock_ok,  # git commit
                mock_fail,  # git push (rc=1, but check=True not enforced by mock)
                mock_fail,  # gh pr create (rc=1)
                mock_ok,  # git checkout main (cleanup after pr_create fails)
            ]

            results = reporter.report_terminal(_entry(STATE_CHAIN_FOUND))

            pr_results = [r for r in results if "pr" in r.get("action", "")]
            assert len(pr_results) == 1
            assert pr_results[0]["action"] == "pr_create_failed"

    def test_github_write_comment_failure_returns_error(self):
        reporter = GitHubReporter(_manifest(), github_write=True)
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "auth error"
            mock_run.return_value = mock_result

            results = reporter.report_terminal(_entry(STATE_TIMEOUT_NO_CHAIN))

            comments = [r for r in results if r.get("action") == "comment_failed"]
            assert len(comments) >= 1
            assert "auth error" in comments[0]["error"]

    def test_result_includes_comment_body(self):
        reporter = GitHubReporter(_manifest())
        results = reporter.report_terminal(_entry(STATE_TIMEOUT_NO_CHAIN))
        for r in results:
            if r.get("action") == "dry_run_comment":
                assert "body" in r
                assert "TIMEOUT_NO_CHAIN" in r["body"]

    def test_reports_to_multiple_issues(self):
        reporter = GitHubReporter(
            _manifest(
                github_reporting={
                    "post_on_issue_3095": True,
                    "post_on_issue_3087": True,
                    "post_on_issue_3102": True,
                }
            )
        )
        results = reporter.report_terminal(_entry(STATE_CHAIN_FOUND), 0)
        comment_actions = [r for r in results if "comment" in r.get("action", "")]
        issues_reported = {r["issue"] for r in comment_actions}
        assert ISSUE_CAMPAIGN in issues_reported
        assert ISSUE_REFERENCE_WINDOW in issues_reported


# ---------------------------------------------------------------------------
# 8. GitHubReporter: _post_comment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostComment:
    def test_without_github_write_returns_dry_run(self):
        reporter = GitHubReporter(_manifest())
        result = reporter._post_comment(3095, "test body")
        assert result["action"] == "dry_run_comment"
        assert result["issue"] == 3095
        assert result["body"] == "test body"

    def test_with_github_write_calls_gh(self):
        reporter = GitHubReporter(_manifest(), github_write=True)
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "https://github.com/comment/1"
            mock_run.return_value = mock_result

            result = reporter._post_comment(3095, "test body")

            assert result["action"] == "comment_posted"
            mock_run.assert_called_once_with(
                ["gh", "issue", "comment", "3095", "--body", "test body"],
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_gh_not_found_returns_error(self):
        reporter = GitHubReporter(_manifest(), github_write=True)
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh not found")
            result = reporter._post_comment(3095, "body")
            assert result["action"] == "comment_failed"
            assert "gh not found" in result["error"]


# ---------------------------------------------------------------------------
# 9. CLI
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCLI:
    def test_help_smoke(self):
        from tools.arvp_github_reporter import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--help"])

    def test_manifest_required(self):
        from tools.arvp_github_reporter import parse_args

        with pytest.raises(SystemExit):
            parse_args([])

    def test_requires_state_or_entry(self):
        from tools.arvp_github_reporter import parse_args

        args = parse_args(["--manifest", "test.yaml"])
        assert args.manifest == "test.yaml"

    def test_github_write_flag(self):
        from tools.arvp_github_reporter import parse_args

        args = parse_args(["--manifest", "test.yaml", "--github-write"])
        assert args.github_write is True

    def test_create_pr_flag(self):
        from tools.arvp_github_reporter import parse_args

        args = parse_args(["--manifest", "test.yaml", "--create-pr"])
        assert args.create_pr is True

    def test_verbose_flag(self):
        from tools.arvp_github_reporter import parse_args

        args = parse_args(["--manifest", "test.yaml", "--verbose"])
        assert args.verbose is True


@pytest.mark.unit
class TestLoadEntry:
    def test_from_json_string(self):
        from tools.arvp_github_reporter import load_entry

        class FakeArgs:
            cycle_entry = '{"state": "CHAIN_FOUND"}'
            cycle_entry_file = None
            state = None

        entry = load_entry(FakeArgs())
        assert entry["state"] == "CHAIN_FOUND"

    def test_from_file(self):
        from tools.arvp_github_reporter import load_entry

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"state": "TIMEOUT_NO_CHAIN"}, f)
            fname = f.name

        try:

            class FakeArgs:
                cycle_entry = None
                cycle_entry_file = fname
                state = None

            entry = load_entry(FakeArgs())
            assert entry["state"] == "TIMEOUT_NO_CHAIN"
        finally:
            os.unlink(fname)

    def test_from_state_override(self):
        from tools.arvp_github_reporter import load_entry

        class FakeArgs:
            cycle_entry = None
            cycle_entry_file = None
            state = "CHAIN_FOUND"

        entry = load_entry(FakeArgs())
        assert entry["state"] == "CHAIN_FOUND"

    def test_no_input_raises(self):
        from tools.arvp_github_reporter import load_entry

        class FakeArgs:
            cycle_entry = None
            cycle_entry_file = None
            state = None

        with pytest.raises(ValueError):
            load_entry(FakeArgs())
