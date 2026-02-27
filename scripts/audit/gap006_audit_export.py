"""
GAP-006 Tamper-Evident Audit Export (offline).

Reads a JSONL file containing LR-021 envelopes with event_hash and
chain_hash (e.g. output of lr021_replay.py or lr021_export_redis.py
with --include-hashes --compute-chain-hash), verifies the hash chain
strictly, and produces an evidence pack:

  out-dir/
    manifest.json       — counts, first/last hashes, file sha256
    sha256sum.txt       — sha256sum-compatible checksum of input file
    verification.md     — human-readable PASS/FAIL report

Read-only on input. Pure offline. No service / trading impact.

Usage:
    python scripts/audit/gap006_audit_export.py \\
        --input artifacts/replayed.jsonl \\
        --out-dir artifacts/audit_export

relations:
  role: audit_exporter
  domain: audit
  upstream:
    - scripts/replay/lr021_replay.py  # (which uses core/replay/canonical_json.py)
  downstream:
    - tests/unit/audit/test_gap006_audit_export.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Optional

# Allow running as standalone script.
if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Re-use hashing from the replay runner — single source of truth.
from scripts.replay.lr021_replay import compute_chain_hash, compute_event_hash

GENESIS_HASH = "0" * 64


def file_sha256(path: str) -> str:
    """Compute SHA-256 hex digest of an entire file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_chain(input_path: str) -> dict:
    """Verify event_hash + chain_hash integrity of a JSONL file.

    Returns a result dict:
        ok: bool — True if all hashes verify
        total: int — number of envelopes processed
        first_event_hash: str | None
        last_event_hash: str | None
        first_chain_hash: str | None
        last_chain_hash: str | None
        errors: list[str] — description of each failure
    """
    prev_chain_hash = GENESIS_HASH
    total = 0
    errors: list[str] = []
    first_event_hash: Optional[str] = None
    last_event_hash: Optional[str] = None
    first_chain_hash: Optional[str] = None
    last_chain_hash: Optional[str] = None

    with open(input_path, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"line {line_number}: invalid JSON: {e}")
                continue

            if not isinstance(obj, dict):
                errors.append(f"line {line_number}: expected JSON object, got {type(obj).__name__}")
                continue

            stored_event_hash = obj.get("event_hash")
            stored_chain_hash = obj.get("chain_hash")

            if stored_event_hash is None:
                errors.append(f"line {line_number}: missing event_hash")
                continue
            if stored_chain_hash is None:
                errors.append(f"line {line_number}: missing chain_hash")
                continue

            # Recompute event_hash on the envelope WITHOUT event_hash/chain_hash
            envelope = {k: v for k, v in obj.items() if k not in ("event_hash", "chain_hash")}
            computed_event_hash = compute_event_hash(envelope)

            if computed_event_hash != stored_event_hash:
                errors.append(
                    f"line {line_number}: event_hash mismatch: "
                    f"stored={stored_event_hash}, computed={computed_event_hash}"
                )

            # Recompute chain_hash
            computed_chain_hash = compute_chain_hash(prev_chain_hash, computed_event_hash)

            if computed_chain_hash != stored_chain_hash:
                errors.append(
                    f"line {line_number}: chain_hash mismatch: "
                    f"stored={stored_chain_hash}, computed={computed_chain_hash}"
                )

            prev_chain_hash = computed_chain_hash
            total += 1

            if first_event_hash is None:
                first_event_hash = stored_event_hash
                first_chain_hash = stored_chain_hash
            last_event_hash = stored_event_hash
            last_chain_hash = stored_chain_hash

    return {
        "ok": len(errors) == 0,
        "total": total,
        "first_event_hash": first_event_hash,
        "last_event_hash": last_event_hash,
        "first_chain_hash": first_chain_hash,
        "last_chain_hash": last_chain_hash,
        "errors": errors,
    }


def build_manifest(input_path: str, verification: dict) -> dict:
    """Build a deterministic manifest dict."""
    input_sha256 = file_sha256(input_path)
    input_basename = os.path.basename(input_path)

    manifest: dict[str, Any] = {
        "schema": "gap006.audit_manifest.v1",
        "input_file": input_basename,
        "input_sha256": input_sha256,
        "envelope_count": verification["total"],
        "chain_verified": verification["ok"],
        "first_event_hash": verification["first_event_hash"],
        "last_event_hash": verification["last_event_hash"],
        "first_chain_hash": verification["first_chain_hash"],
        "last_chain_hash": verification["last_chain_hash"],
        "error_count": len(verification["errors"]),
    }
    return manifest


def build_sha256sum(input_path: str) -> str:
    """Build sha256sum-compatible line for the input file."""
    digest = file_sha256(input_path)
    basename = os.path.basename(input_path)
    return f"{digest}  {basename}\n"


def build_verification_md(manifest: dict, errors: list[str]) -> str:
    """Build human-readable verification report."""
    status = "PASS" if manifest["chain_verified"] else "FAIL"
    lines = [
        f"# GAP-006 Audit Verification Report",
        "",
        f"**Status:** {status}",
        f"**Input file:** `{manifest['input_file']}`",
        f"**Input SHA-256:** `{manifest['input_sha256']}`",
        f"**Envelope count:** {manifest['envelope_count']}",
        "",
        "## Hash Chain",
        "",
        f"| Property | Value |",
        f"|----------|-------|",
        f"| First event_hash | `{manifest['first_event_hash']}` |",
        f"| Last event_hash | `{manifest['last_event_hash']}` |",
        f"| First chain_hash | `{manifest['first_chain_hash']}` |",
        f"| Last chain_hash | `{manifest['last_chain_hash']}` |",
        f"| Chain verified | {manifest['chain_verified']} |",
        "",
    ]

    if errors:
        lines.append("## Errors")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated by `gap006_audit_export.py`*")
    lines.append("")
    return "\n".join(lines)


def audit_export(input_path: str, out_dir: str) -> dict:
    """Run full audit export pipeline.

    Args:
        input_path: Path to JSONL file with event_hash + chain_hash.
        out_dir: Directory for output files (created if needed).

    Returns:
        manifest dict (also written to out_dir/manifest.json).
    """
    os.makedirs(out_dir, exist_ok=True)

    verification = verify_chain(input_path)
    manifest = build_manifest(input_path, verification)

    # Write manifest.json (deterministic via canonical_json_dumps is NOT
    # appropriate here — manifest is a report, not an envelope. We use
    # sorted json.dumps for human-readability + determinism.)
    manifest_json = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        f.write(manifest_json)

    # Write sha256sum.txt
    sha256sum_line = build_sha256sum(input_path)
    with open(os.path.join(out_dir, "sha256sum.txt"), "w", encoding="utf-8") as f:
        f.write(sha256sum_line)

    # Write verification.md
    report = build_verification_md(manifest, verification["errors"])
    with open(os.path.join(out_dir, "verification.md"), "w", encoding="utf-8") as f:
        f.write(report)

    return manifest


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="GAP-006 Tamper-Evident Audit Export. "
        "Verifies LR-021 envelope hash chain and produces evidence pack."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input JSONL file (with event_hash + chain_hash)",
    )
    parser.add_argument(
        "--out-dir", "-o",
        required=True,
        help="Output directory for evidence pack",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    """CLI entry point. Returns exit code (0=PASS, 1=FAIL)."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    manifest = audit_export(args.input, args.out_dir)

    if manifest["chain_verified"]:
        print(f"PASS: {manifest['envelope_count']} envelopes verified.", file=sys.stderr)
        return 0
    else:
        print(
            f"FAIL: {manifest['error_count']} error(s) in {manifest['envelope_count']} envelopes.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
