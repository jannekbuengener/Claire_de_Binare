"""Tests for scripts/audit/gap006_audit_export.py — tamper-evident audit export.

Positive: valid fixture -> PASS, exit 0
Negative: mutated line -> FAIL, exit != 0

Governance: GAP-006 (Audit Export)
"""

import json
import os
import sys
from pathlib import Path

import pytest

# scripts/ is not a Python package (no __init__.py), so add repo root.
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.gap006_audit_export import (  # noqa: E402
    audit_export,
    build_manifest,
    build_sha256sum,
    build_verification_md,
    file_sha256,
    verify_chain,
)

FIXTURES = repo_root / "tests" / "fixtures" / "replay"
GOLDEN_FILE = FIXTURES / "lr021_expected_hashes.jsonl"


# ---------------------------------------------------------------------------
# verify_chain — positive
# ---------------------------------------------------------------------------


class TestVerifyChainPositive:
    def test_golden_file_passes(self):
        """The existing golden fixture with valid chain_hash passes."""
        result = verify_chain(str(GOLDEN_FILE))
        assert result["ok"] is True
        assert result["total"] == 5
        assert result["errors"] == []
        assert result["first_event_hash"] is not None
        assert result["last_chain_hash"] is not None

    def test_single_envelope(self, tmp_path):
        """Single-envelope file with correct hashes passes."""
        from scripts.replay.lr021_replay import compute_chain_hash, compute_event_hash

        env = {
            "schema_version": "envelope.v1",
            "event_type": "DECISION",
            "event_id": "ev-1",
            "ts_ms": 1000,
            "payload": {"decision": "ALLOW"},
        }
        eh = compute_event_hash(env)
        ch = compute_chain_hash("0" * 64, eh)
        line_obj = {**env, "event_hash": eh, "chain_hash": ch}

        f = tmp_path / "single.jsonl"
        f.write_text(json.dumps(line_obj, sort_keys=True) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is True
        assert result["total"] == 1
        assert result["first_event_hash"] == eh
        assert result["last_chain_hash"] == ch


# ---------------------------------------------------------------------------
# verify_chain — negative (tamper detection)
# ---------------------------------------------------------------------------


class TestVerifyChainNegative:
    def test_mutated_event_hash_fails(self, tmp_path):
        """Flipping a bit in event_hash is detected."""
        lines = GOLDEN_FILE.read_text(encoding="utf-8").strip().splitlines()
        # Mutate event_hash in second line
        obj = json.loads(lines[1])
        obj["event_hash"] = "0" * 64  # wrong
        lines[1] = json.dumps(obj, sort_keys=True)

        f = tmp_path / "mutated_eh.jsonl"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is False
        assert any("event_hash mismatch" in e for e in result["errors"])

    def test_mutated_chain_hash_fails(self, tmp_path):
        """Flipping a bit in chain_hash is detected."""
        lines = GOLDEN_FILE.read_text(encoding="utf-8").strip().splitlines()
        obj = json.loads(lines[2])
        obj["chain_hash"] = "f" * 64  # wrong
        lines[2] = json.dumps(obj, sort_keys=True)

        f = tmp_path / "mutated_ch.jsonl"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is False
        # Only the tampered line should fail — no error cascade
        chain_errors = [e for e in result["errors"] if "chain_hash mismatch" in e]
        assert len(chain_errors) == 1
        assert "line 3" in chain_errors[0]

    def test_mutated_payload_fails(self, tmp_path):
        """Changing a payload field invalidates event_hash."""
        lines = GOLDEN_FILE.read_text(encoding="utf-8").strip().splitlines()
        obj = json.loads(lines[0])
        obj["payload"]["decision"] = "BLOCK"  # was ALLOW
        lines[0] = json.dumps(obj, sort_keys=True)

        f = tmp_path / "mutated_payload.jsonl"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is False
        assert any("event_hash mismatch" in e for e in result["errors"])

    def test_deleted_line_breaks_chain(self, tmp_path):
        """Removing a line breaks the chain from that point on."""
        lines = GOLDEN_FILE.read_text(encoding="utf-8").strip().splitlines()
        # Remove line 2 (index 1) — chain_hash of line 3 depends on line 2
        del lines[1]

        f = tmp_path / "deleted.jsonl"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is False
        assert result["total"] == 4

    def test_missing_event_hash_field(self, tmp_path):
        """Missing event_hash field is reported as error."""
        env = {
            "schema_version": "envelope.v1",
            "event_type": "DECISION",
            "event_id": "ev-1",
            "ts_ms": 1000,
            "payload": {},
            "chain_hash": "0" * 64,
        }
        f = tmp_path / "no_eh.jsonl"
        f.write_text(json.dumps(env) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is False
        assert any("missing event_hash" in e for e in result["errors"])

    def test_missing_chain_hash_field(self, tmp_path):
        """Missing chain_hash field is reported as error."""
        env = {
            "schema_version": "envelope.v1",
            "event_type": "DECISION",
            "event_id": "ev-1",
            "ts_ms": 1000,
            "payload": {},
            "event_hash": "0" * 64,
        }
        f = tmp_path / "no_ch.jsonl"
        f.write_text(json.dumps(env) + "\n", encoding="utf-8")

        result = verify_chain(str(f))
        assert result["ok"] is False
        assert any("missing chain_hash" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# audit_export — full pipeline
# ---------------------------------------------------------------------------


class TestAuditExport:
    def test_pass_produces_evidence_pack(self, tmp_path):
        out_dir = str(tmp_path / "out")
        manifest = audit_export(str(GOLDEN_FILE), out_dir)

        assert manifest["chain_verified"] is True
        assert manifest["envelope_count"] == 5
        assert manifest["error_count"] == 0
        assert manifest["schema"] == "gap006.audit_manifest.v1"

        # All output files exist
        assert os.path.isfile(os.path.join(out_dir, "manifest.json"))
        assert os.path.isfile(os.path.join(out_dir, "sha256sum.txt"))
        assert os.path.isfile(os.path.join(out_dir, "verification.md"))

    def test_manifest_json_valid(self, tmp_path):
        out_dir = str(tmp_path / "out")
        audit_export(str(GOLDEN_FILE), out_dir)

        with open(os.path.join(out_dir, "manifest.json"), "r") as f:
            manifest = json.load(f)

        assert manifest["chain_verified"] is True
        assert manifest["envelope_count"] == 5
        assert manifest["input_file"] == "lr021_expected_hashes.jsonl"
        assert len(manifest["input_sha256"]) == 64
        assert len(manifest["first_event_hash"]) == 64
        assert len(manifest["last_chain_hash"]) == 64

    def test_sha256sum_format(self, tmp_path):
        out_dir = str(tmp_path / "out")
        audit_export(str(GOLDEN_FILE), out_dir)

        content = (tmp_path / "out" / "sha256sum.txt").read_text(encoding="utf-8")
        # sha256sum format: "<hash>  <filename>\n"
        parts = content.strip().split("  ")
        assert len(parts) == 2
        assert len(parts[0]) == 64
        assert parts[1] == "lr021_expected_hashes.jsonl"

    def test_verification_md_pass(self, tmp_path):
        out_dir = str(tmp_path / "out")
        audit_export(str(GOLDEN_FILE), out_dir)

        content = (tmp_path / "out" / "verification.md").read_text(encoding="utf-8")
        assert "**Status:** PASS" in content
        assert "Errors" not in content

    def test_fail_produces_evidence_pack(self, tmp_path):
        """Mutated input still produces evidence pack, but with FAIL."""
        lines = GOLDEN_FILE.read_text(encoding="utf-8").strip().splitlines()
        obj = json.loads(lines[0])
        obj["event_hash"] = "bad" + obj["event_hash"][3:]
        lines[0] = json.dumps(obj, sort_keys=True)

        bad_file = tmp_path / "bad.jsonl"
        bad_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        out_dir = str(tmp_path / "out")
        manifest = audit_export(str(bad_file), out_dir)

        assert manifest["chain_verified"] is False
        assert manifest["error_count"] > 0

        content = (tmp_path / "out" / "verification.md").read_text(encoding="utf-8")
        assert "**Status:** FAIL" in content
        assert "## Errors" in content

    def test_deterministic_output(self, tmp_path):
        """Same input -> byte-identical manifest on repeated runs."""
        manifests = []
        for i in range(3):
            out_dir = str(tmp_path / f"out{i}")
            audit_export(str(GOLDEN_FILE), out_dir)
            content = (tmp_path / f"out{i}" / "manifest.json").read_text(encoding="utf-8")
            manifests.append(content)

        assert manifests[0] == manifests[1] == manifests[2]


# ---------------------------------------------------------------------------
# CLI exit code
# ---------------------------------------------------------------------------


class TestCLIExitCode:
    def test_exit_0_on_pass(self, tmp_path):
        from audit.gap006_audit_export import main

        out_dir = str(tmp_path / "out")
        code = main(["--input", str(GOLDEN_FILE), "--out-dir", out_dir])
        assert code == 0

    def test_exit_1_on_fail(self, tmp_path):
        from audit.gap006_audit_export import main

        lines = GOLDEN_FILE.read_text(encoding="utf-8").strip().splitlines()
        obj = json.loads(lines[0])
        obj["event_hash"] = "0" * 64
        lines[0] = json.dumps(obj, sort_keys=True)

        bad_file = tmp_path / "bad.jsonl"
        bad_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        out_dir = str(tmp_path / "out")
        code = main(["--input", str(bad_file), "--out-dir", out_dir])
        assert code == 1


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_file_sha256(self, tmp_path):
        f = tmp_path / "test.txt"
        # Write binary to avoid platform line-ending differences.
        f.write_bytes(b"hello\n")
        digest = file_sha256(str(f))
        assert len(digest) == 64
        import hashlib
        expected = hashlib.sha256(b"hello\n").hexdigest()
        assert digest == expected

    def test_build_sha256sum_format(self, tmp_path):
        f = tmp_path / "data.jsonl"
        f.write_text("{}\n", encoding="utf-8")
        line = build_sha256sum(str(f))
        assert line.endswith("  data.jsonl\n")
        assert len(line.split("  ")[0]) == 64

    def test_build_verification_md_pass(self):
        manifest = {
            "input_file": "test.jsonl",
            "input_sha256": "a" * 64,
            "envelope_count": 3,
            "chain_verified": True,
            "first_event_hash": "b" * 64,
            "last_event_hash": "c" * 64,
            "first_chain_hash": "d" * 64,
            "last_chain_hash": "e" * 64,
        }
        md = build_verification_md(manifest, [])
        assert "PASS" in md
        assert "Errors" not in md

    def test_build_verification_md_fail(self):
        manifest = {
            "input_file": "test.jsonl",
            "input_sha256": "a" * 64,
            "envelope_count": 3,
            "chain_verified": False,
            "first_event_hash": "b" * 64,
            "last_event_hash": "c" * 64,
            "first_chain_hash": "d" * 64,
            "last_chain_hash": "e" * 64,
        }
        md = build_verification_md(manifest, ["line 1: event_hash mismatch"])
        assert "FAIL" in md
        assert "## Errors" in md
        assert "event_hash mismatch" in md
