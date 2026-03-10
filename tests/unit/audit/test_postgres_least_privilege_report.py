"""Tests for the offline Postgres least-privilege report."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.postgres_least_privilege_report import (  # noqa: E402
    build_report,
    generate_report,
    load_baseline,
    load_datasets,
    main,
)

FIXTURE_DIR = repo_root / "tests" / "fixtures" / "postgres_privileges"
BASELINE_PATH = repo_root / "scripts" / "audit" / "desired_privileges.json"


def _copy_fixture_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "fixtures"
    destination.mkdir()
    for source in FIXTURE_DIR.iterdir():
        destination.joinpath(source.name).write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return destination


class TestPostgresLeastPrivilegeReport:
    def test_build_report_is_deterministic_for_unsorted_input(self, tmp_path):
        fixture_dir = _copy_fixture_tree(tmp_path)
        table_privileges_path = fixture_dir / "table_privileges.csv"
        rows = table_privileges_path.read_text(encoding="utf-8").splitlines()
        header, body = rows[0], rows[1:]
        table_privileges_path.write_text(
            "\n".join([header, *reversed(body)]) + "\n",
            encoding="utf-8",
        )

        datasets = load_datasets(str(fixture_dir))
        baseline = load_baseline(str(BASELINE_PATH))
        report_one = build_report(datasets, baseline)
        report_two = build_report(load_datasets(str(fixture_dir)), baseline)

        assert report_one["status"] == "PASS"
        assert report_one == report_two

    def test_generate_report_detects_unexpected_direct_runtime_privilege(
        self, tmp_path
    ):
        fixture_dir = _copy_fixture_tree(tmp_path)
        table_privileges_path = fixture_dir / "table_privileges.csv"
        with table_privileges_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["claire_user", "public", "signals", "SELECT"])

        out_dir = tmp_path / "out"
        report = generate_report(
            str(out_dir),
            input_dir=str(fixture_dir),
            baseline_path=str(BASELINE_PATH),
        )

        assert report["status"] == "FAIL"
        assert any(
            finding["resource"] == "claire_user:public.signals:SELECT"
            and finding["status"] == "VIOLATION"
            for finding in report["violations"]
        )

    def test_cli_returns_nonzero_when_required_dump_is_missing(self, tmp_path):
        fixture_dir = _copy_fixture_tree(tmp_path)
        (fixture_dir / "rls_tables.csv").unlink()

        out_dir = tmp_path / "out"
        exit_code = main(
            [
                "--input-dir",
                str(fixture_dir),
                "--out-dir",
                str(out_dir),
                "--baseline",
                str(BASELINE_PATH),
            ]
        )
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

        assert exit_code == 2
        assert report["status"] == "FAIL"
        assert any(
            finding["category"] == "INPUT" and finding["resource"] == "rls_tables"
            for finding in report["gaps"]
        )

    def test_cli_writes_stable_report_schema_for_passing_fixture(self, tmp_path):
        fixture_dir = _copy_fixture_tree(tmp_path)
        out_dir = tmp_path / "out"

        exit_code = main(
            [
                "--input-dir",
                str(fixture_dir),
                "--out-dir",
                str(out_dir),
                "--baseline",
                str(BASELINE_PATH),
            ]
        )
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        summary_md = (out_dir / "summary.md").read_text(encoding="utf-8")

        assert exit_code == 0
        assert report["schema"] == "governance.postgres_least_privilege_report.v1"
        assert report["summary"]["violation_count"] == 0
        assert report["summary"]["gap_count"] == 0
        assert "| `table_privileges` | 33 |" in summary_md
