"""CLI entry: python -m tools.hermes_ops <command>"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.hermes_ops.policy import (
    assert_action_allowed,
    omnipotent_combination_forbidden,
)
from tools.hermes_ops.profiles import validate_all_profiles
from tools.hermes_ops.secret_scan import scan_paths
from tools.hermes_ops.systemd_contract import validate_unit
from tools.hermes_ops.token_broker import (
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
    # Omnipotent combination request should fail closed when present.
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


def _cmd_mint_token(args: argparse.Namespace) -> int:
    if args.dry_run:
        print(json.dumps(metadata_only(args.profile), indent=2, sort_keys=True))
        return 0
    token, meta = mint_profile_token(args.profile, dry_run=False)
    # Token to stdout only when --print-token; metadata always JSON on stderr-safe path.
    meta_payload = {
        "profile": meta.profile,
        "repositories": list(meta.repositories),
        "permissions": meta.permissions,
        "expires_hint": meta.expires_hint,
        "token": "[REDACTED]",
    }
    print(json.dumps(meta_payload, indent=2, sort_keys=True))
    if args.print_token:
        # Explicit opt-in; callers should redirect to a secured FD.
        sys.stdout.write(token or "")
        sys.stdout.write("\n")
    return 0


def _cmd_pin_check(_: argparse.Namespace) -> int:
    pin = Path("infrastructure/hermes/VERSION_PIN.yaml")
    text = pin.read_text(encoding="utf-8") if pin.is_file() else ""
    git_ref_empty = 'git_ref: ""' in text or "git_ref:" in text and 'git_ref: "' in text
    # Treat literally empty quoted value as unset (bootstrap refuses this).
    unset = 'git_ref: ""' in text or 'install_script_sha256: ""' in text
    payload = {
        "ok": pin.is_file(),
        "pin_file": str(pin),
        "operator_must_set_before_live_install": unset or git_ref_empty,
        "note": "Empty pin is expected in-repo; live bootstrap requires operator fill-in.",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


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
        "--print-token",
        action="store_true",
        help="Print raw token to stdout (opt-in; never log)",
    )
    p_mint.set_defaults(func=_cmd_mint_token)

    p_pin = sub.add_parser("pin-check", help="Check VERSION_PIN.yaml presence")
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
