"""CLI entry: python -m tools.hermes_ops <command>"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

import yaml

from tools.hermes_ops.policy import (
    assert_action_allowed,
    omnipotent_combination_forbidden,
)
from tools.hermes_ops.profiles import validate_all_profiles
from tools.hermes_ops.secret_scan import scan_paths
from tools.hermes_ops.systemd_contract import validate_unit
from tools.hermes_ops.token_broker import (
    assert_app_compatible_for_hermes_write,
    credential_paths_outside_workspace,
    metadata_only,
    mint_profile_token,
)


def _cmd_validate_profiles(_: argparse.Namespace) -> int:
    reports = validate_all_profiles()
    payload = {
        "ok": all(r.ok for r in reports),
        "profiles": [
            {
                "profile": r.profile,
                "ok": r.ok,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in reports
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


def _cmd_secret_scan(_: argparse.Namespace) -> int:
    findings = scan_paths()
    payload = {
        "ok": not findings,
        "findings": [
            {"path": f.path, "kind": f.kind, "detail": f.detail} for f in findings
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


def _cmd_policy_check(args: argparse.Namespace) -> int:
    unit_errors = validate_unit()
    path_errors = credential_paths_outside_workspace()
    action = assert_action_allowed(args.profile, args.action)
    combo = omnipotent_combination_forbidden(set(args.capabilities or []))
    expect = args.expect
    if expect == "allow":
        action_matches = action.ok is True
    else:
        action_matches = action.ok is False
    combo_ok = not combo
    payload = {
        "ok": action_matches and not unit_errors and not path_errors and combo_ok,
        "expect": expect,
        "action": {
            "profile": action.profile,
            "ok": action.ok,
            "reason": action.reason,
            "details": action.details,
        },
        "systemd_errors": unit_errors,
        "credential_path_errors": path_errors,
        "omnipotent_combination": combo,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


def _write_token_file(path: Path, token: str) -> None:
    """Write token with mode 0600. Never print raw token to stdout/stderr."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, 0o600)
    try:
        os.write(fd, token.encode("utf-8"))
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        path.unlink(missing_ok=True)
        raise PermissionError(f"token file mode must be 0600, got {oct(mode)}")


def _cmd_mint_token(args: argparse.Namespace) -> int:
    if args.dry_run:
        print(json.dumps(metadata_only(args.profile), indent=2, sort_keys=True))
        return 0
    if not args.token_file:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "token_file_required",
                    "detail": (
                        "Live mint requires --token-file PATH (mode 0600). "
                        "--print-token is removed; raw tokens must not hit stdout."
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    # Fail-closed App compatibility gate (cdb-local-ci App is not Hermes write).
    try:
        assert_app_compatible_for_hermes_write()
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "hold": "HOLD_SCOPE_BLOCKER",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    token, meta = mint_profile_token(args.profile, dry_run=False)
    if not token:
        print(json.dumps({"ok": False, "error": "empty_token"}, indent=2))
        return 2
    _write_token_file(Path(args.token_file), token)
    meta_payload = {
        "ok": True,
        "profile": meta.profile,
        "repositories": list(meta.repositories),
        "permissions": meta.permissions,
        "expires_hint": meta.expires_hint,
        "token": "[REDACTED]",
        "token_file": str(args.token_file),
        "token_file_mode": "0600",
    }
    print(json.dumps(meta_payload, indent=2, sort_keys=True))
    return 0


def _pin_fields_missing(pin: dict) -> list[str]:
    hermes = pin.get("hermes") or {}
    missing: list[str] = []
    for key in ("git_ref", "git_commit", "install_script_sha256", "install_url"):
        val = hermes.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(f"hermes.{key}")
    return missing


def _cmd_pin_check(args: argparse.Namespace) -> int:
    pin_path = Path("infrastructure/hermes/VERSION_PIN.yaml")
    if not pin_path.is_file():
        print(
            json.dumps(
                {"ok": False, "pin_file": str(pin_path), "error": "missing_pin_file"},
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    pin = yaml.safe_load(pin_path.read_text(encoding="utf-8")) or {}
    missing = _pin_fields_missing(pin)
    require_pinned = bool(args.require_pinned)
    # Default: report presence; with --require-pinned (live install): fail empty.
    ok = not missing if require_pinned else True
    payload = {
        "ok": ok,
        "pin_file": str(pin_path),
        "require_pinned": require_pinned,
        "missing_fields": missing,
        "git_ref": (pin.get("hermes") or {}).get("git_ref") or "",
        "git_commit": (pin.get("hermes") or {}).get("git_commit") or "",
        "note": (
            "Live install / bootstrap must pass pin-check --require-pinned."
            if missing
            else "Pin fields present."
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.hermes_ops")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate-profiles", help="Validate profile distributions")
    p_val.set_defaults(func=_cmd_validate_profiles)

    p_scan = sub.add_parser("secret-scan", help="Scan Hermes repo surfaces for leaks")
    p_scan.set_defaults(func=_cmd_secret_scan)

    p_pol = sub.add_parser("policy-check", help="Check action/unit/credential policy")
    p_pol.add_argument("--profile", default="cdb-engineer")
    p_pol.add_argument("--action", default="github_write_branch_pr")
    p_pol.add_argument(
        "--expect",
        choices=("allow", "deny"),
        default="allow",
        help="Whether the action should be allowed or denied",
    )
    p_pol.add_argument(
        "--capabilities",
        nargs="*",
        default=[],
        help="Capability tags to test omnipotent-combination guard",
    )
    p_pol.set_defaults(func=_cmd_policy_check)

    p_mint = sub.add_parser("mint-token", help="Mint scoped GitHub App token")
    p_mint.add_argument("--profile", required=True)
    p_mint.add_argument("--dry-run", action="store_true")
    p_mint.add_argument(
        "--token-file",
        default="",
        help="Write raw token to this path with mode 0600 (required for live mint)",
    )
    p_mint.set_defaults(func=_cmd_mint_token)

    p_pin = sub.add_parser("pin-check", help="Check VERSION_PIN.yaml completeness")
    p_pin.add_argument(
        "--require-pinned",
        action="store_true",
        help="Fail (exit 2) when git_ref/commit/sha256 are empty (live install gate)",
    )
    p_pin.set_defaults(func=_cmd_pin_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 — CLI fail-closed with type only
        print(
            json.dumps({"ok": False, "error": type(exc).__name__, "detail": str(exc)})
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
