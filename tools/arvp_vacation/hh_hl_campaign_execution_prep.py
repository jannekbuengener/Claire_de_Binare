"""hh_hl Campaign Execution-Preparation CLI (#4374).

Write-free by default (materializes only with ``--out``) and never starts a
replay. Orchestrates the read-only preparation chain:

* ``verify-design-go``      — verify the Owner Design-GO (fixture or live).
* ``build-final-manifest``  — build the frozen final manifest body.
* ``finalize-plan``         — build a FINAL (post-merge) or ``--pre-final`` plan.
* ``prepare-execution-go``  — assemble an Owner Execution-GO *package* (never a
  verified authorization) for the human to post.
* ``probe-surface``         — read-only single-run surface probe (no replays).
* ``negative-execute-probe``— assert fail-closed execute statuses without replay.

Safety: ``campaign_execution_authorized`` is always ``false``; ``execution_sha``
is ``null`` for planning; a real post-merge ``main`` SHA and a live Owner
Execution-GO remain mandatory before any run. No post-merge SHA or surface
fingerprint is ever invented.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from tools.arvp_vacation.campaign_executor_providers import (
    HhHlSingleRunReplayProvider,
    PlanningOnlyExecutor,
    resolve_campaign_executor,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    HH_HL_REPLAY_PROFILE_ID,
    CampaignProfileError,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import (
    HhHlDatasetBindingError,
    load_pass_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    DEFAULT_REPO,
    ISSUE_NUMBER,
    DesignGoComment,
    HhHlDesignAuthorizationError,
    build_reference_design_receipt,
    default_gh_comment_fetcher,
    verify_design_go_comment,
)
from tools.arvp_vacation.hh_hl_campaign_execution_authorization import (
    ADAPTER_ID,
    AUTH_SCHEMA_VERSION,
    CAMPAIGN_ID,
    EVIDENCE_NAMESPACE,
    GO_STATUS,
    GRANTED_CAPABILITY,
    MANIFEST_ID,
    STRATEGY_ID,
    HhHlExecutionAuthorizationError,
    assert_lifetime_covers_budget,
)
from tools.arvp_vacation.hh_hl_campaign_final_manifest import (
    DEFAULT_FINAL_MANIFEST_REL,
    PROJECT_ROOT,
    build_hh_hl_final_manifest,
    load_source_manifest,
    write_hh_hl_final_manifest,
)
from tools.arvp_vacation.hh_hl_campaign_run_plan import (
    build_hh_hl_final_run_plan,
)

DEFAULT_MANIFEST_REL = "config/arvp/hh_hl_campaign_4374_v1.json"
DEFAULT_DATASET_RECEIPT_REL = (
    "docs/evidence/arvp_hh_hl_dataset_local_proof_receipt_4374.json"
)
DEFAULT_DESIGN_GO_COMMENT_ID = 5206657394
SINGLE_RUN_SURFACE_ID = HhHlSingleRunReplayProvider.SURFACE_ID


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n")


def _repo_root(args: argparse.Namespace) -> Path:
    root = getattr(args, "repo_root", None)
    return Path(root) if root else PROJECT_ROOT


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _fixture_fetcher(fixture_path: Path):
    data = _load_json(fixture_path)

    def _fetch(repository: str, issue: int, comment_id: int) -> DesignGoComment:
        issue_url = str(data.get("issue_url") or "")
        live_issue = issue
        if issue_url:
            tail = issue_url.rstrip("/").rsplit("/", 1)[-1]
            if tail.isdigit():
                live_issue = int(tail)
        return DesignGoComment(
            comment_id=int(data.get("id") or comment_id),
            issue_number=int(data.get("issue_number") or live_issue),
            author_login=str(
                (data.get("user") or {}).get("login") or data.get("author_login") or ""
            ),
            body=str(data.get("body") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            repository=repository,
        )

    return _fetch


def _resolve_design_receipt(args: argparse.Namespace):
    """Resolve a DesignRatificationReceipt (fixture / live / reference)."""
    comment_id = int(
        getattr(args, "design_go_comment_id", DEFAULT_DESIGN_GO_COMMENT_ID)
    )
    repo_root = _repo_root(args)
    fixture = getattr(args, "design_go_fixture_json", None)
    if fixture:
        result = verify_design_go_comment(
            comment_id=comment_id,
            repository=getattr(args, "repository", DEFAULT_REPO),
            issue=getattr(args, "issue", ISSUE_NUMBER),
            fetcher=_fixture_fetcher(Path(fixture)),
            repo_root=repo_root,
        )
        return result["receipt"], result["body_fingerprint"]
    if getattr(args, "live", False):
        result = verify_design_go_comment(
            comment_id=comment_id,
            repository=getattr(args, "repository", DEFAULT_REPO),
            issue=getattr(args, "issue", ISSUE_NUMBER),
            fetcher=default_gh_comment_fetcher,
            repo_root=repo_root,
        )
        return result["receipt"], result["body_fingerprint"]
    receipt = build_reference_design_receipt(comment_id=comment_id, repo_root=repo_root)
    return receipt, receipt.body_fingerprint


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_verify_design_go(args: argparse.Namespace) -> int:
    comment_id = int(args.comment_id)
    repo_root = _repo_root(args)
    try:
        if args.fixture_json:
            result = verify_design_go_comment(
                comment_id=comment_id,
                fetcher=_fixture_fetcher(Path(args.fixture_json)),
                repo_root=repo_root,
            )
        else:
            result = verify_design_go_comment(
                comment_id=comment_id,
                fetcher=default_gh_comment_fetcher,
                repo_root=repo_root,
            )
    except HhHlDesignAuthorizationError as exc:
        _emit({"valid": False, "reason_code": exc.reason_code, "detail": str(exc)})
        return 1
    _emit(
        {
            "valid": True,
            "reason_code": result["reason_code"],
            "comment_id": comment_id,
            "body_fingerprint": result["body_fingerprint"],
            "comment_updated_at": result["comment_updated_at"],
            "receipt": result["receipt_dict"],
            "writes": False,
            "replays": False,
        }
    )
    return 0


def cmd_build_final_manifest(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args)
    try:
        design_receipt, design_fp = _resolve_design_receipt(args)
        dataset_receipt = load_pass_receipt(
            repo_root / (args.dataset_receipt or DEFAULT_DATASET_RECEIPT_REL)
        )
        source_manifest = load_source_manifest(repo_root)
        body = build_hh_hl_final_manifest(
            design_receipt=design_receipt,
            dataset_receipt=dataset_receipt,
            source_manifest=source_manifest,
        )
    except (
        HhHlDesignAuthorizationError,
        HhHlDatasetBindingError,
        CampaignProfileError,
        ValueError,
    ) as exc:
        reason = getattr(exc, "reason_code", type(exc).__name__)
        _emit({"ok": False, "reason_code": reason, "detail": str(exc)})
        return 1

    wrote_to: str | None = None
    if args.out:
        target = write_hh_hl_final_manifest(
            body, path=Path(args.out), repo_root=repo_root
        )
        wrote_to = target.as_posix()
    _emit(
        {
            "ok": True,
            "manifest_fingerprint": body["manifest_fingerprint"],
            "source_manifest_fingerprint": body["source_manifest_fingerprint"],
            "design_body_fingerprint": design_fp,
            "campaign_execution_authorized": body["campaign_execution_authorized"],
            "requires_external_owner_go": body["requires_external_owner_go"],
            "expected_run_count": body["expected_run_count"],
            "writes": bool(args.out),
            "written_path": wrote_to,
            "replays": False,
        }
    )
    return 0


def cmd_finalize_plan(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args)
    planning_sha = str(args.planning_sha or "").strip()
    try:
        design_receipt, design_fp = _resolve_design_receipt(args)
        dataset_receipt = load_pass_receipt(
            repo_root / (args.dataset_receipt or DEFAULT_DATASET_RECEIPT_REL)
        )
        manifest = _load_json(repo_root / (args.manifest or DEFAULT_MANIFEST_REL))
        plan = build_hh_hl_final_run_plan(
            final_manifest=manifest,
            design_receipt=design_receipt,
            dataset_receipt=dataset_receipt,
            planning_sha=planning_sha,
            pre_final=bool(args.pre_final),
        )
    except (
        HhHlDesignAuthorizationError,
        HhHlDatasetBindingError,
        CampaignProfileError,
        ValueError,
    ) as exc:
        reason = getattr(exc, "reason_code", None) or str(exc)
        _emit({"ok": False, "reason_code": reason, "detail": str(exc)})
        return 1

    out = {
        "ok": True,
        "status": plan.status,
        "post_merge_final": plan.post_merge_final,
        "pre_final": bool(args.pre_final),
        "planning_sha": plan.planning_sha,
        "execution_sha": plan.execution_sha,
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "manifest_fingerprint": plan.manifest_fingerprint,
        "source_manifest_fingerprint": plan.source_manifest_fingerprint,
        "design_body_fingerprint": design_fp,
        "design_comment_id": plan.design_comment_id,
        "expected_run_count": plan.expected_run_count,
        "campaign_execution_authorized": plan.campaign_execution_authorized,
        "executable": plan.executable,
        "writes": bool(args.out),
        "replays": False,
    }
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(plan.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        out["written_path"] = target.as_posix()
    _emit(out)
    return 0


def _load_surface_receipt(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    surface_id = str(data.get("execution_surface_id") or "")
    fp = str(data.get("surface_capability_fingerprint") or "")
    if not surface_id or len(fp) != 64:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_SURFACE_PROOF_REQUIRED", "incomplete surface receipt"
        )
    return {"execution_surface_id": surface_id, "surface_capability_fingerprint": fp}


def cmd_prepare_execution_go(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args)
    planning_sha = str(args.planning_sha or "").strip()
    execution_sha = str(args.execution_sha or "").strip()
    try:
        design_receipt, design_fp = _resolve_design_receipt(args)
        dataset_receipt = load_pass_receipt(
            repo_root / (args.dataset_receipt or DEFAULT_DATASET_RECEIPT_REL)
        )
        manifest = _load_json(repo_root / (args.manifest or DEFAULT_MANIFEST_REL))
        if not args.surface_receipt:
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_SURFACE_PROOF_REQUIRED", "no --surface-receipt"
            )
        surface = _load_surface_receipt(Path(args.surface_receipt))
        # FINAL plan enforces a real, distinct post-merge main SHA (fail-closed
        # with HOLD_POST_MERGE_MAIN_SHA_REQUIRED otherwise).
        plan = build_hh_hl_final_run_plan(
            final_manifest=manifest,
            design_receipt=design_receipt,
            dataset_receipt=dataset_receipt,
            planning_sha=planning_sha,
            pre_final=False,
        )
        if len(execution_sha) != 40 or any(
            c not in "0123456789abcdef" for c in execution_sha
        ):
            raise HhHlExecutionAuthorizationError(
                "HOLD_POST_MERGE_MAIN_SHA_REQUIRED", "execution_sha missing/invalid"
            )
        payload = _assemble_execution_go_payload(
            manifest=manifest,
            plan=plan,
            planning_sha=planning_sha,
            execution_sha=execution_sha,
            surface=surface,
            expires_at_utc=str(args.expires_at_utc or ""),
        )
        # Self-check the package we hand to the owner: a finite, still-future
        # expiry that covers the resource budget. Full schema/comment-id
        # verification only happens live once the owner has actually posted the
        # GO (github_comment_id stays a null placeholder here). This does NOT
        # authorize execution.
        assert_lifetime_covers_budget(
            payload["expires_at_utc"], payload["resource_budget"]
        )
    except (
        HhHlDesignAuthorizationError,
        HhHlDatasetBindingError,
        HhHlExecutionAuthorizationError,
        CampaignProfileError,
        ValueError,
    ) as exc:
        reason = getattr(exc, "reason_code", None) or str(exc)
        _emit({"ok": False, "reason_code": reason, "detail": str(exc)})
        return 1

    package = {
        "ok": True,
        "ready_for_owner_execution_go": True,
        "campaign_execution_authorized": False,
        "github_comment_id": None,
        "authorizing_github_login": None,
        "design_body_fingerprint": design_fp,
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "fence": "```cdb.hh_hl_campaign_execution_authorization.v1",
        "execution_go_payload": payload,
        "writes": bool(args.out),
        "replays": False,
    }
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        package["written_path"] = target.as_posix()
    _emit(package)
    return 0


def _assemble_execution_go_payload(
    *,
    manifest: Mapping[str, Any],
    plan: Any,
    planning_sha: str,
    execution_sha: str,
    surface: Mapping[str, Any],
    expires_at_utc: str,
) -> dict[str, Any]:
    dataset_binding = dict(manifest.get("dataset_binding") or {})
    return {
        "schema_version": AUTH_SCHEMA_VERSION,
        "status": GO_STATUS,
        "repository": DEFAULT_REPO,
        "issue": ISSUE_NUMBER,
        "github_comment_id": None,
        "authorizing_github_login": "jannekbuengener",
        "bound_main_sha": planning_sha,
        "execution_sha": execution_sha,
        "manifest_path": str(manifest.get("manifest_path") or DEFAULT_MANIFEST_REL),
        "manifest_id": MANIFEST_ID,
        "manifest_fingerprint": str(manifest.get("manifest_fingerprint") or ""),
        "campaign_id": CAMPAIGN_ID,
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "strategy_set": [STRATEGY_ID],
        "adapter_id": ADAPTER_ID,
        "window_count": int(manifest.get("expected_window_count") or 0),
        "variant_count": int(manifest.get("expected_variant_count") or 0),
        "expected_run_count": int(manifest.get("expected_run_count") or 0),
        "evidence_namespace": str(
            manifest.get("evidence_namespace") or EVIDENCE_NAMESPACE
        ),
        "execution_surface_id": surface["execution_surface_id"],
        "surface_capability_fingerprint": surface["surface_capability_fingerprint"],
        "granted_capabilities": [GRANTED_CAPABILITY],
        "resource_budget": dict(manifest.get("resource_budget_contract") or {}),
        "resume_policy": dict(manifest.get("resume_policy") or {}),
        "dataset_selection_sha256": str(dataset_binding.get("selection_sha256") or ""),
        "dataset_content_fingerprint_digest": str(
            dataset_binding.get("content_fingerprint_digest") or ""
        ),
        "absolute_bans_unchanged": True,
        "expires_at_utc": expires_at_utc,
        "lr_status": "NO-GO",
    }


def cmd_probe_surface(args: argparse.Namespace) -> int:
    """Read-only single-run surface probe. Never starts a replay."""
    if args.fixture:
        _emit(
            {
                "ok": True,
                "probed": True,
                "fixture": True,
                "execution_surface_id": SINGLE_RUN_SURFACE_ID,
                "replays": False,
                "note": "fixture surface probe; no dataset root touched",
            }
        )
        return 0
    try:
        from tools.arvp_vacation.hh_hl_campaign_dataset import (
            resolve_default_dataset_root,
        )

        root = resolve_default_dataset_root()
    except Exception as exc:  # noqa: BLE001 — fail-closed to HOLD
        _emit(
            {
                "ok": False,
                "reason_code": "HOLD_EXECUTION_SURFACE_DATASET_ROOT_REQUIRED",
                "detail": type(exc).__name__,
                "replays": False,
            }
        )
        return 1
    if root is None:
        _emit(
            {
                "ok": False,
                "reason_code": "HOLD_EXECUTION_SURFACE_DATASET_ROOT_REQUIRED",
                "replays": False,
            }
        )
        return 1
    _emit(
        {
            "ok": True,
            "probed": True,
            "fixture": False,
            "execution_surface_id": SINGLE_RUN_SURFACE_ID,
            "dataset_root_resolved": True,
            "replays": False,
        }
    )
    return 0


def cmd_negative_execute_probe(args: argparse.Namespace) -> int:
    """Assert fail-closed execute statuses without ever calling a replay."""
    probes: list[dict[str, Any]] = []

    prep = load_profile(HH_HL_PREP_PROFILE_ID)
    prep_exec = resolve_campaign_executor(prep)
    probes.append(
        {
            "probe": "prep_profile_executor_type",
            "expected": "PlanningOnlyExecutor",
            "actual": type(prep_exec).__name__,
            "pass": isinstance(prep_exec, PlanningOnlyExecutor),
        }
    )

    replay = load_profile(HH_HL_REPLAY_PROFILE_ID)
    provider = HhHlSingleRunReplayProvider(replay)
    envelope = _probe_envelope()
    try:
        provider.execute(envelope, authorization_context=None)
        probes.append(
            {
                "probe": "replay_execute_without_owner_go",
                "expected": "HOLD_EXECUTION_OWNER_GO_REQUIRED",
                "actual": "NO_RAISE",
                "pass": False,
            }
        )
    except CampaignProfileError as exc:
        probes.append(
            {
                "probe": "replay_execute_without_owner_go",
                "expected": "HOLD_EXECUTION_OWNER_GO_REQUIRED",
                "actual": str(exc),
                "pass": "HOLD_EXECUTION_OWNER_GO_REQUIRED" in str(exc),
            }
        )

    all_pass = all(p["pass"] for p in probes)
    _emit(
        {
            "ok": all_pass,
            "reason_code": (
                "NEGATIVE_EXECUTE_PROBE_OK"
                if all_pass
                else "NEGATIVE_EXECUTE_PROBE_FAILED"
            ),
            "replays": False,
            "probes": probes,
        }
    )
    return 0 if all_pass else 1


def _probe_envelope():
    from tools.arvp_vacation.sensitivity_campaign_executor import RunEnvelope

    return RunEnvelope(
        run_key="probe",
        campaign_id=CAMPAIGN_ID,
        manifest_fingerprint="m" * 64,
        execution_sha="a" * 40,
        window_id="binance_1m_month_2017_10",
        strategy_id=STRATEGY_ID,
        parameters={"swing_left_bars": 2},
        slot_id="hh_hl_baseline_001",
        phase="BASELINE",
        label="spec_frozen_baseline",
        physical_parameter_set_fingerprint="p" * 64,
        effective_config_fingerprint="e" * 64,
        dataset_content_fingerprint="d" * 64,
        seed="s",
        output_dir="artifacts/probe",
        run_plan_fingerprint="r" * 64,
        authorization_fingerprint="x" * 64,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hh_hl_campaign_execution_prep",
        description="hh_hl campaign execution preparation (write-free, no replays)",
    )
    parser.add_argument("--repo-root", default=None, help="override repo root")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify-design-go", help="verify Owner Design-GO")
    p_verify.add_argument(
        "--comment-id", type=int, default=DEFAULT_DESIGN_GO_COMMENT_ID
    )
    p_verify.add_argument("--fixture-json", default=None)
    p_verify.set_defaults(func=cmd_verify_design_go)

    p_build = sub.add_parser("build-final-manifest", help="build final manifest body")
    p_build.add_argument(
        "--design-go-comment-id", type=int, default=DEFAULT_DESIGN_GO_COMMENT_ID
    )
    p_build.add_argument("--design-go-fixture-json", default=None)
    p_build.add_argument("--dataset-receipt", default=None)
    p_build.add_argument("--live", action="store_true")
    p_build.add_argument("--out", default=None, help="write manifest JSON to path")
    p_build.set_defaults(func=cmd_build_final_manifest)

    p_final = sub.add_parser("finalize-plan", help="build FINAL/PRE_FINALIZATION plan")
    p_final.add_argument("--manifest", default=None)
    p_final.add_argument("--dataset-receipt", default=None)
    p_final.add_argument(
        "--design-go-comment-id", type=int, default=DEFAULT_DESIGN_GO_COMMENT_ID
    )
    p_final.add_argument("--design-go-fixture-json", default=None)
    p_final.add_argument("--planning-sha", default="")
    p_final.add_argument("--pre-final", action="store_true")
    p_final.add_argument("--live", action="store_true")
    p_final.add_argument("--out", default=None)
    p_final.set_defaults(func=cmd_finalize_plan)

    p_prep = sub.add_parser("prepare-execution-go", help="assemble Owner Execution-GO")
    p_prep.add_argument("--manifest", default=None)
    p_prep.add_argument("--dataset-receipt", default=None)
    p_prep.add_argument(
        "--design-go-comment-id", type=int, default=DEFAULT_DESIGN_GO_COMMENT_ID
    )
    p_prep.add_argument("--design-go-fixture-json", default=None)
    p_prep.add_argument("--planning-sha", default="")
    p_prep.add_argument("--execution-sha", default="")
    p_prep.add_argument("--surface-receipt", default=None)
    p_prep.add_argument("--expires-at-utc", default="")
    p_prep.add_argument("--live", action="store_true")
    p_prep.add_argument("--out", default=None)
    p_prep.set_defaults(func=cmd_prepare_execution_go)

    p_surface = sub.add_parser("probe-surface", help="read-only surface probe")
    p_surface.add_argument("--fixture", action="store_true")
    p_surface.set_defaults(func=cmd_probe_surface)

    p_neg = sub.add_parser("negative-execute-probe", help="fail-closed execute probes")
    p_neg.set_defaults(func=cmd_negative_execute_probe)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
