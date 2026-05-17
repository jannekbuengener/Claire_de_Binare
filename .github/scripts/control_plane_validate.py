#!/usr/bin/env python3
"""
control_plane_validate.py
Validator for the .github control-plane manifest collection layer.

Usage:
  python3 .github/scripts/control_plane_validate.py
  python3 .github/scripts/control_plane_validate.py --unit-id cdb-daily-delta-triage
  python3 .github/scripts/control_plane_validate.py --generate
  python3 .github/scripts/control_plane_validate.py --generate --output path/to/out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

VALID_KINDS = {"control_workflow", "prompt", "script", "command"}
VALID_STATUSES = {"active", "manual_only", "parked", "historical_unclear"}
VALID_FAIL_POSTURES = {"fail_closed", "report_only"}

REQUIRED_TOP_LEVEL = {"id", "kind", "status", "owner_surface", "workflow", "purpose", "control", "discovery", "tests"}
REQUIRED_WORKFLOW_FIELDS = {"path", "triggers", "permissions"}
REQUIRED_CONTROL_FIELDS = {"fail_posture", "human_touchpoint", "auto_issue_creation"}
REQUIRED_DISCOVERY_FIELDS = {"register_group", "dedupe_key"}
REQUIRED_TESTS_FIELDS = {"smoke"}

PATH_CHECKED_DEP_KEYS = ("scripts", "prompts", "required_files")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _normalize_trigger(trigger: str) -> str:
    """Strip sub-type suffix: 'pull_request:closed' -> 'pull_request'."""
    return trigger.split(":")[0].strip()


def _extract_real_triggers(workflow_yaml: dict) -> set[str]:
    """Extract top-level trigger names from a real workflow's 'on:' section."""
    on_section = workflow_yaml.get("on") or workflow_yaml.get(True)
    if on_section is None:
        return set()
    if isinstance(on_section, str):
        return {on_section}
    if isinstance(on_section, list):
        return {str(t) for t in on_section}
    if isinstance(on_section, dict):
        return set(on_section.keys())
    return set()


def _extract_real_permissions(workflow_yaml: dict) -> dict[str, str]:
    """Extract top-level permissions block from a real workflow."""
    perms = workflow_yaml.get("permissions")
    if not isinstance(perms, dict):
        return {}
    return {str(k): str(v) for k, v in perms.items()}


# ---------------------------------------------------------------------------
# Per-unit validation
# ---------------------------------------------------------------------------

def validate_unit(unit_dir: Path, repo_root: Path) -> list[str]:
    """Validate a single unit directory. Returns list of error strings (empty = PASS)."""
    errors: list[str] = []
    unit_id = unit_dir.name

    manifest_path = unit_dir / "manifest.yaml"
    if not manifest_path.exists():
        return [f"[{unit_id}] manifest.yaml not found at {manifest_path}"]

    try:
        m = _load_yaml(manifest_path)
    except yaml.YAMLError as exc:
        return [f"[{unit_id}] YAML parse error in manifest.yaml: {exc}"]

    if not isinstance(m, dict):
        return [f"[{unit_id}] manifest.yaml must be a YAML mapping"]

    # --- Required top-level fields ---
    for field in REQUIRED_TOP_LEVEL:
        if field not in m:
            errors.append(f"[{unit_id}] Missing required field: {field}")

    if errors:
        return errors  # Can't continue without required fields

    # --- id must match directory name ---
    if m["id"] != unit_id:
        errors.append(f"[{unit_id}] 'id' field ({m['id']!r}) does not match directory name ({unit_id!r})")

    # --- kind ---
    if m["kind"] not in VALID_KINDS:
        errors.append(f"[{unit_id}] Invalid 'kind': {m['kind']!r}. Valid values: {sorted(VALID_KINDS)}")

    # --- status ---
    if m["status"] not in VALID_STATUSES:
        errors.append(f"[{unit_id}] Invalid 'status': {m['status']!r}. Valid values: {sorted(VALID_STATUSES)}")

    # --- workflow block ---
    wf = m.get("workflow", {})
    if not isinstance(wf, dict):
        errors.append(f"[{unit_id}] 'workflow' must be a mapping")
    else:
        for field in REQUIRED_WORKFLOW_FIELDS:
            if field not in wf:
                errors.append(f"[{unit_id}] Missing required workflow field: workflow.{field}")

        wf_path_str = wf.get("path")
        if wf_path_str:
            wf_path = repo_root / wf_path_str
            if not wf_path.exists():
                errors.append(f"[{unit_id}] workflow.path does not exist: {wf_path_str}")
            else:
                # --- Cross-check triggers and permissions against real workflow YAML ---
                try:
                    real_wf = _load_yaml(wf_path)
                except yaml.YAMLError as exc:
                    errors.append(f"[{unit_id}] Could not parse workflow YAML at {wf_path_str}: {exc}")
                    real_wf = None

                if real_wf is not None:
                    # Trigger cross-check
                    manifest_triggers = wf.get("triggers") or []
                    if not isinstance(manifest_triggers, list):
                        errors.append(f"[{unit_id}] workflow.triggers must be a list")
                    else:
                        manifest_trigger_set = {_normalize_trigger(t) for t in manifest_triggers}
                        real_trigger_set = _extract_real_triggers(real_wf)
                        missing_in_manifest = real_trigger_set - manifest_trigger_set
                        extra_in_manifest = manifest_trigger_set - real_trigger_set
                        if missing_in_manifest:
                            errors.append(
                                f"[{unit_id}] workflow.triggers missing triggers that exist in real workflow: "
                                f"{sorted(missing_in_manifest)}"
                            )
                        if extra_in_manifest:
                            errors.append(
                                f"[{unit_id}] workflow.triggers declares triggers not found in real workflow: "
                                f"{sorted(extra_in_manifest)}"
                            )

                    # Permissions cross-check
                    manifest_perms = wf.get("permissions") or {}
                    if not isinstance(manifest_perms, dict):
                        errors.append(f"[{unit_id}] workflow.permissions must be a mapping")
                    else:
                        real_perms = _extract_real_permissions(real_wf)
                        # Normalize both to str:str for comparison
                        manifest_perms_norm = {str(k): str(v) for k, v in manifest_perms.items()}
                        # Check for missing keys in manifest
                        for key, val in real_perms.items():
                            if key not in manifest_perms_norm:
                                errors.append(
                                    f"[{unit_id}] workflow.permissions missing key '{key}' "
                                    f"(real value: '{val}')"
                                )
                            elif manifest_perms_norm[key] != val:
                                errors.append(
                                    f"[{unit_id}] workflow.permissions['{key}'] mismatch: "
                                    f"manifest='{manifest_perms_norm[key]}' real='{val}'"
                                )
                        # Check for extra keys in manifest
                        for key in manifest_perms_norm:
                            if key not in real_perms:
                                errors.append(
                                    f"[{unit_id}] workflow.permissions declares key '{key}' "
                                    f"not found in real workflow permissions"
                                )

    # --- control block ---
    ctrl = m.get("control", {})
    if not isinstance(ctrl, dict):
        errors.append(f"[{unit_id}] 'control' must be a mapping")
    else:
        for field in REQUIRED_CONTROL_FIELDS:
            if field not in ctrl:
                errors.append(f"[{unit_id}] Missing required control field: control.{field}")
        if "fail_posture" in ctrl and ctrl["fail_posture"] not in VALID_FAIL_POSTURES:
            errors.append(
                f"[{unit_id}] Invalid control.fail_posture: {ctrl['fail_posture']!r}. "
                f"Valid values: {sorted(VALID_FAIL_POSTURES)}"
            )

    # --- discovery block ---
    disc = m.get("discovery", {})
    if not isinstance(disc, dict):
        errors.append(f"[{unit_id}] 'discovery' must be a mapping")
    else:
        for field in REQUIRED_DISCOVERY_FIELDS:
            if field not in disc:
                errors.append(f"[{unit_id}] Missing required discovery field: discovery.{field}")

    # --- tests block ---
    tests = m.get("tests", {})
    if not isinstance(tests, dict):
        errors.append(f"[{unit_id}] 'tests' must be a mapping")
    else:
        for field in REQUIRED_TESTS_FIELDS:
            if field not in tests:
                errors.append(f"[{unit_id}] Missing required tests field: tests.{field}")
        smoke_list = tests.get("smoke") or []
        if not isinstance(smoke_list, list):
            errors.append(f"[{unit_id}] tests.smoke must be a list")
        else:
            for smoke_path_str in smoke_list:
                smoke_path = repo_root / smoke_path_str
                if not smoke_path.exists():
                    errors.append(f"[{unit_id}] tests.smoke path does not exist: {smoke_path_str}")

    # --- dependencies: path-checked fields ---
    deps = m.get("dependencies") or {}
    if isinstance(deps, dict):
        for dep_key in PATH_CHECKED_DEP_KEYS:
            dep_list = deps.get(dep_key) or []
            if dep_list is None:
                continue
            if not isinstance(dep_list, list):
                errors.append(f"[{unit_id}] dependencies.{dep_key} must be a list")
                continue
            for dep_path_str in dep_list:
                dep_path = repo_root / dep_path_str
                if not dep_path.exists():
                    errors.append(
                        f"[{unit_id}] dependencies.{dep_key} path does not exist: {dep_path_str}"
                    )

    return errors


# ---------------------------------------------------------------------------
# Cross-unit uniqueness checks
# ---------------------------------------------------------------------------

def check_uniqueness(units: list[tuple[str, dict]]) -> list[str]:
    """Check for duplicate id, workflow.path, and discovery.dedupe_key across all units."""
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_paths: dict[str, str] = {}
    seen_dedupe: dict[str, str] = {}

    for unit_id, manifest in units:
        # id uniqueness (already guaranteed by directory structure, but belt-and-suspenders)
        if unit_id in seen_ids:
            errors.append(f"Duplicate unit id: {unit_id!r} (also in {seen_ids[unit_id]})")
        seen_ids[unit_id] = unit_id

        wf = manifest.get("workflow") or {}
        wf_path = wf.get("path")
        if wf_path:
            if wf_path in seen_paths:
                errors.append(
                    f"[{unit_id}] Duplicate workflow.path {wf_path!r} "
                    f"(also declared in {seen_paths[wf_path]})"
                )
            seen_paths[wf_path] = unit_id

        disc = manifest.get("discovery") or {}
        dedupe_key = disc.get("dedupe_key")
        if dedupe_key:
            if dedupe_key in seen_dedupe:
                errors.append(
                    f"[{unit_id}] Duplicate discovery.dedupe_key {dedupe_key!r} "
                    f"(also declared in {seen_dedupe[dedupe_key]})"
                )
            seen_dedupe[dedupe_key] = unit_id

    return errors


# ---------------------------------------------------------------------------
# Register generation
# ---------------------------------------------------------------------------

def generate_register(units: list[tuple[str, dict]], output_path: Path) -> None:
    """Write a deterministic workflow-register.json from validated manifests."""
    sorted_units = sorted(units, key=lambda x: x[0])

    entries = []
    for unit_id, m in sorted_units:
        wf = m.get("workflow") or {}
        disc = m.get("discovery") or {}
        ctrl = m.get("control") or {}
        deps = m.get("dependencies") or {}

        entry = {
            "id": unit_id,
            "kind": m.get("kind"),
            "status": m.get("status"),
            "owner_surface": m.get("owner_surface"),
            "workflow_path": wf.get("path"),
            "triggers": sorted(wf.get("triggers") or []),
            "permissions": dict(sorted((wf.get("permissions") or {}).items())),
            "purpose": (m.get("purpose") or "").strip(),
            "control": {
                "fail_posture": ctrl.get("fail_posture"),
                "human_touchpoint": ctrl.get("human_touchpoint"),
                "auto_issue_creation": ctrl.get("auto_issue_creation"),
            },
            "dependencies": {
                "scripts": sorted(deps.get("scripts") or []),
                "prompts": sorted(deps.get("prompts") or []),
                "required_files": sorted(deps.get("required_files") or []),
            },
            "discovery": {
                "register_group": disc.get("register_group"),
                "dedupe_key": disc.get("dedupe_key"),
                "related_control_issue": disc.get("related_control_issue"),
            },
        }
        entries.append(entry)

    register = {
        "schema_version": "1",
        "coverage": "partial",
        "catalog_scope": "control-plane-sprint1",
        "generated_from": "manifests",
        "unit_count": len(entries),
        "units": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(register, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"Generated: {output_path} ({len(entries)} units)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate .github control-plane manifests")
    parser.add_argument("--repo-root", default=".", help="Repo root path (default: current directory)")
    parser.add_argument(
        "--collection-dir",
        default=".github/control-plane/src",
        help="Collection source directory relative to repo-root",
    )
    parser.add_argument("--unit-id", default=None, help="Validate only a specific unit ID")
    parser.add_argument("--generate", action="store_true", help="Generate workflow-register.json if all pass")
    parser.add_argument(
        "--output",
        default=".github/control-plane/generated/workflow-register.json",
        help="Output path for generated register (relative to repo-root)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    collection_dir = repo_root / args.collection_dir

    if not collection_dir.exists():
        print(f"ERROR: Collection directory not found: {collection_dir}", file=sys.stderr)
        return 1

    # Discover unit directories
    if args.unit_id:
        unit_dirs = [collection_dir / args.unit_id]
        if not unit_dirs[0].is_dir():
            print(f"ERROR: Unit directory not found: {unit_dirs[0]}", file=sys.stderr)
            return 1
    else:
        unit_dirs = sorted(
            [d for d in collection_dir.iterdir() if d.is_dir()],
            key=lambda d: d.name,
        )

    if not unit_dirs:
        print("No unit directories found — nothing to validate.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    validated_units: list[tuple[str, dict]] = []

    for unit_dir in unit_dirs:
        print(f"Validating unit: {unit_dir.name} ...", end=" ")
        unit_errors = validate_unit(unit_dir, repo_root)
        if unit_errors:
            print("FAIL")
            all_errors.extend(unit_errors)
        else:
            print("PASS")
            manifest = _load_yaml(unit_dir / "manifest.yaml")
            validated_units.append((unit_dir.name, manifest))

    # Cross-unit uniqueness (only when validating all units)
    if not args.unit_id and validated_units:
        uniqueness_errors = check_uniqueness(validated_units)
        if uniqueness_errors:
            all_errors.extend(uniqueness_errors)

    if all_errors:
        print("\n--- VALIDATION ERRORS ---", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        print(f"\nFAIL: {len(all_errors)} error(s)", file=sys.stderr)
        return 1

    print(f"\nPASS: all {len(validated_units)} unit(s) valid")

    if args.generate:
        if args.unit_id:
            print("WARNING: --generate with --unit-id only regenerates with partial data; "
                  "run without --unit-id for full register.")
        output_path = repo_root / args.output
        generate_register(validated_units, output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
