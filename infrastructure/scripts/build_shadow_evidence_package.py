#!/usr/bin/env python3
"""Build and validate a canonical shadow-soak evidence package."""

from __future__ import annotations

import json
import shutil
import sys
from hashlib import sha256
from pathlib import Path

REQUIRED_PACKAGE_FILES = (
    "run_summary.json",
    "shadow_block_probe.json",
    "soak_gate_eval.json",
    "evidence_index.json",
    "shadow_metrics_comparison.json",
    "endpoints/execution_metrics.txt",
    "endpoints/risk_metrics.txt",
    "endpoints/execution_status.json",
    "endpoints/risk_status.json",
)

OPTIONAL_PACKAGE_FILES = (
    "run_summary.md",
    "shadow_metrics_comparison.md",
    "compose_ps.txt",
    "container_inspect.json",
    "logs_tail.txt",
    "logs_grep.txt",
)


def _load_json_required(path: Path, source_name: str) -> dict:
    if not path.is_file():
        raise ValueError(f"required source missing: {source_name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {source_name}: {exc}") from exc


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize_fragment(value: object) -> str:
    text = str(value or "unknown").strip()
    sanitized = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    sanitized = sanitized.strip("-")
    return sanitized or "unknown"


def _package_file_record(root: Path, relative_path: str) -> dict:
    path = root / relative_path
    if not path.is_file():
        raise ValueError(f"required package file missing: {relative_path}")
    return {
        "path": relative_path,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def build_shadow_evidence_package(evidence_dir: Path) -> dict:
    missing = [
        path for path in REQUIRED_PACKAGE_FILES if not (evidence_dir / path).is_file()
    ]
    if missing:
        raise ValueError(
            "required package files missing: " + ", ".join(sorted(missing))
        )

    run_summary = _load_json_required(
        evidence_dir / "run_summary.json", "run_summary.json"
    )
    evidence_index = _load_json_required(
        evidence_dir / "evidence_index.json", "evidence_index.json"
    )
    soak_gate_eval = _load_json_required(
        evidence_dir / "soak_gate_eval.json", "soak_gate_eval.json"
    )
    shadow_probe = _load_json_required(
        evidence_dir / "shadow_block_probe.json", "shadow_block_probe.json"
    )

    if run_summary.get("gate_status") != "PASS":
        raise ValueError("run_summary gate_status must be PASS for canonical package")
    if soak_gate_eval.get("verdict") != "PASS":
        raise ValueError("soak_gate_eval verdict must be PASS for canonical package")
    shadow_comparison = _load_json_required(
        evidence_dir / "shadow_metrics_comparison.json", "shadow_metrics_comparison.json"
    )
    if shadow_comparison.get("verdict") != "PASS":
        raise ValueError(
            f"shadow_metrics_comparison verdict must be PASS for canonical package "
            f"(got: {shadow_comparison.get('verdict')!r}). "
            "Calibrate docs/evidence/lr031_baseline_thresholds.json first."
        )

    run_id = _sanitize_fragment(run_summary.get("run_id"))
    commit = _sanitize_fragment(str(run_summary.get("commit") or "")[:12])
    mode = _sanitize_fragment(run_summary.get("mode"))
    package_id = f"shadow-soak-{run_id}-{commit}-{mode}"
    package_root = evidence_dir / "packages" / package_id
    package_root.mkdir(parents=True, exist_ok=True)

    copied_paths: list[str] = []
    for relative_path in REQUIRED_PACKAGE_FILES + OPTIONAL_PACKAGE_FILES:
        source = evidence_dir / relative_path
        if not source.is_file():
            continue
        destination = package_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_paths.append(relative_path)

    manifest = {
        "schema_version": "1.1",
        "package_id": package_id,
        "package_type": "shadow-soak-evidence",
        "package_status": "PASS",
        "canonical_manifest_path": f"packages/{package_id}/manifest.json",
        "canonical_package_root": f"packages/{package_id}",
        "run": {
            "run_id": run_summary.get("run_id"),
            "run_url": run_summary.get("run_url"),
            "ref": run_summary.get("ref"),
            "commit": run_summary.get("commit"),
            "mode": run_summary.get("mode"),
            "soak_minutes": run_summary.get("soak_minutes"),
            "ended_at": run_summary.get("ended_at"),
        },
        "verdicts": {
            "service_gate_status": run_summary.get("gate_status"),
            "shadow_gate_verdict": soak_gate_eval.get("verdict"),
            "lr031_comparison_verdict": shadow_comparison.get("verdict"),
        },
        "required_files": [
            _package_file_record(package_root, relative_path)
            for relative_path in REQUIRED_PACKAGE_FILES
        ],
        "optional_files": [
            _package_file_record(package_root, relative_path)
            for relative_path in OPTIONAL_PACKAGE_FILES
            if (package_root / relative_path).is_file()
        ],
        "evidence_summary": {
            "shadow_blocked_total": evidence_index.get("shadow_blocked_total"),
            "orders_filled": evidence_index.get("orders_filled"),
            "orders_approved": evidence_index.get("orders_approved"),
            "has_live_data": evidence_index.get("has_live_data"),
            "risk_blocked_all": evidence_index.get("risk_blocked_all"),
            "trading_mode": evidence_index.get("trading_mode"),
            "order_result_found": shadow_probe.get("order_result_found"),
            "order_result_source": shadow_probe.get("order_result_source"),
        },
        "copied_files": copied_paths,
    }

    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (package_root / "manifest.json").write_text(manifest_text, encoding="utf-8")
    (evidence_dir / "package_manifest.json").write_text(manifest_text, encoding="utf-8")
    return manifest


def validate_shadow_evidence_package(package_root: Path) -> dict:
    manifest = _load_json_required(package_root / "manifest.json", "manifest.json")

    if manifest.get("package_status") != "PASS":
        raise ValueError("package_status must be PASS")

    required_files = manifest.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        raise ValueError("manifest missing required_files records")

    missing_files: list[str] = []
    checksum_mismatches: list[str] = []

    for record in required_files:
        relative_path = record.get("path")
        expected_sha = record.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
            raise ValueError("invalid required_files manifest entry")
        target = package_root / relative_path
        if not target.is_file():
            missing_files.append(relative_path)
            continue
        if _sha256_file(target) != expected_sha:
            checksum_mismatches.append(relative_path)

    return {
        "package_id": manifest.get("package_id"),
        "package_status": manifest.get("package_status"),
        "missing_files": missing_files,
        "checksum_mismatches": checksum_mismatches,
        "valid": not missing_files and not checksum_mismatches,
    }


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <evidence-directory>", file=sys.stderr)
        sys.exit(2)

    evidence_dir = Path(sys.argv[1])
    if not evidence_dir.is_dir():
        print(f"ERROR: not a directory: {evidence_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = build_shadow_evidence_package(evidence_dir)
        validation = validate_shadow_evidence_package(
            evidence_dir / manifest["canonical_package_root"]
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    validation_path = evidence_dir / "package_validation.json"
    validation_path.write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "package_manifest_path": "package_manifest.json",
                "package_validation_path": "package_validation.json",
                "package_id": manifest["package_id"],
                "valid": validation["valid"],
            },
            ensure_ascii=False,
        )
    )
    sys.exit(0 if validation["valid"] else 1)


if __name__ == "__main__":
    main()
