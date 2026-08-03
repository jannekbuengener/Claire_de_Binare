"""CLI front door for agent registry + governed dispatcher.

Examples:
  python -m tools.agent_control registry validate --config <PATH>
  python -m tools.agent_control dispatch --contract <PATH> --registry <PATH> \\
      --agent-id <ID> --state <PATH> --dry-run
  python -m tools.agent_control provider capabilities --provider cursor-sdk --offline
  python -m tools.agent_control watch --run-id <ID> --state <PATH>
  python -m tools.agent_control cancel --run-id <ID> --state <PATH> --reason <TEXT>
  python -m tools.agent_control retry --previous-run-id <ID> --contract <PATH> --reason <TEXT>
  python -m tools.agent_control evidence --run-id <ID> --state <PATH>
  python -m tools.agent_control evidence snapshot --run <ID> --state <PATH>
  python -m tools.agent_control evidence emit --run <ID> --state <PATH> [--store <JSONL>]
  python -m tools.agent_control evidence verify --bundle <PATH>
  python -m tools.agent_control evidence verify --store <JSONL>
  python -m tools.agent_control evidence show --run <ID> --store <JSONL>
  python -m tools.agent_control approval context --pr <N> --snapshot <PATH>
  python -m tools.agent_control approval drift --baseline <PATH>
  python -m tools.agent_control pilot run --manifest <PATH> [--out <REPORT>]
  python -m tools.agent_control pilot verify --report <PATH>
  python -m tools.agent_control pilot cursor-preflight --repository owner/name
  python -m tools.agent_control pilot cursor-support-bundle \\
      --state-run1 <PATH> --state-run2 <PATH> --output <DIR>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.agent_control.dispatch import (
    cancel_run,
    dispatch_run,
    evidence_snapshot,
    retry_run,
    watch_run,
)
from tools.agent_control.errors import (
    AgentControlError,
    DispatchError,
    EvidenceError,
    RegistryError,
)
from tools.agent_control.approval.codes import (
    EXIT_BLOCKED,
    EXIT_ERROR,
    EXIT_HOLD,
    EXIT_OK,
    EXIT_UNKNOWN,
    ApprovalError,
)
from tools.agent_control.load import (
    dump_json,
    load_observed_state,
    load_registry_document,
)
from tools.agent_control.normalize import normalize_registry, registry_fingerprint
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT
from tools.agent_control.providers.capability import offline_capability_snapshot
from tools.agent_control.providers.factory import CURSOR_PROVIDER_IDS
from tools.agent_control.reconcile import backend_from_state, build_plan, reconcile
from tools.agent_control.run_store import JsonFileRunStore
from tools.agent_control.validate import validate_registry


def _print_json(payload: Any) -> None:
    sys.stdout.write(dump_json(payload))


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cmd_registry_validate(args: argparse.Namespace) -> int:
    try:
        document = load_registry_document(Path(args.config))
        validate_registry(document)
        fingerprint = registry_fingerprint(document)
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    print(f"VALID schema_id=cdb.agent_registry.v1 fingerprint={fingerprint}")
    return 0


def cmd_registry_normalize(args: argparse.Namespace) -> int:
    try:
        document = load_registry_document(Path(args.config))
        normalized = normalize_registry(document)
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(normalized), encoding="utf-8")
    else:
        _print_json(normalized)
    return 0


def cmd_registry_plan(args: argparse.Namespace) -> int:
    try:
        document = load_registry_document(Path(args.config))
        state = load_observed_state(Path(args.state))
        plan = build_plan(document, state, mode="plan")
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(plan), encoding="utf-8")
    else:
        _print_json(plan)
    return 1 if plan.get("blocked") else 0


def cmd_registry_reconcile(args: argparse.Namespace) -> int:
    dry_run = not args.apply
    if args.apply and not args.allow_mock_apply:
        print(
            "INVALID REGISTRY_LIVE_MUTATION_FORBIDDEN: "
            "reconcile defaults to dry-run; pass --apply --allow-mock-apply "
            "only against a mock state file (no live provider)",
            file=sys.stderr,
        )
        return 1
    try:
        document = load_registry_document(Path(args.config))
        if args.state:
            state = load_observed_state(Path(args.state))
        else:
            state = {
                "schema_id": "cdb.agent_registry.observed.v1",
                "agents": {},
            }
        backend_name = "mock" if args.apply else "file"
        backend = backend_from_state(state, backend_name=backend_name)
        result = reconcile(document, backend, dry_run=dry_run)
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(result), encoding="utf-8")
    else:
        _print_json(result)
    plan = result["plan"]
    if plan.get("blocked"):
        return 1
    return 0


def cmd_dispatch(args: argparse.Namespace) -> int:
    dry_run = not args.execute
    try:
        contract = _load_json(Path(args.contract))
        registry = load_registry_document(Path(args.registry))
        if dry_run:
            result = dispatch_run(
                contract,
                registry,
                args.agent_id,
                store=None,
                dry_run=True,
                scenario=args.scenario,
            )
        else:
            if not args.state:
                raise DispatchError(
                    "DISPATCH_STATE_REQUIRED",
                    "execute requires --state <PATH>",
                )
            if not args.allow_mock_dispatch:
                raise DispatchError(
                    "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                    "execute requires --allow-mock-dispatch",
                )
            store = JsonFileRunStore(Path(args.state))
            result = dispatch_run(
                contract,
                registry,
                args.agent_id,
                store,
                dry_run=False,
                allow_mock_dispatch=True,
                scenario=args.scenario,
            )
    except (AgentControlError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "DISPATCH_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(result), encoding="utf-8")
    else:
        _print_json(result)
    if result.get("dry_run"):
        return 0 if result["plan"].get("preflight_ok") else 1
    run = result.get("run") or {}
    return 0 if run.get("state") not in {"HOLD", "BLOCKED", "FAILED"} else 1


def cmd_watch(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = watch_run(args.run_id, store)
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(record)
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = cancel_run(args.run_id, store, args.reason)
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(record)
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    dry_run = not args.execute
    try:
        contract = _load_json(Path(args.contract))
        registry = load_registry_document(Path(args.registry))
        if not args.state:
            raise DispatchError("DISPATCH_STATE_REQUIRED", "retry requires --state")
        store = JsonFileRunStore(Path(args.state))
        result = retry_run(
            args.previous_run_id,
            contract,
            registry,
            store,
            args.reason,
            agent_id=args.agent_id,
            dry_run=dry_run,
            allow_mock_dispatch=bool(args.execute and args.allow_mock_dispatch),
            scenario=args.scenario,
        )
    except (AgentControlError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "DISPATCH_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return 1
    _print_json(result)
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """Legacy snapshot alias: evidence --run-id/--state."""
    try:
        store = JsonFileRunStore(Path(args.state))
        run_id = getattr(args, "run_id", None) or getattr(args, "run", None)
        snapshot = evidence_snapshot(run_id, store)
    except (DispatchError, EvidenceError) as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(snapshot)
    return 0


def cmd_evidence_dispatch(args: argparse.Namespace) -> int:
    """Parent evidence command without subcommand.

    - --run-id + --state → legacy lifecycle snapshot
    - --run + --state → emit bundle (documented bundle entry)
    """
    if getattr(args, "evidence_command", None):
        # Subcommand handlers are set via set_defaults; should not reach here.
        return 1
    run_id = getattr(args, "run_id", None)
    run = getattr(args, "run", None)
    state = getattr(args, "state", None)
    if run_id and state and not run:
        args.run_id = run_id
        return cmd_evidence(args)
    if run and state:
        args.run = run
        args.store = getattr(args, "store", None)
        return cmd_evidence_emit(args)
    print(
        "INVALID EVIDENCE_USAGE: use "
        "'evidence snapshot|emit|verify|show', "
        "legacy 'evidence --run-id <ID> --state <PATH>', "
        "or bundle entry 'evidence --run <ID> --state <PATH>'",
        file=sys.stderr,
    )
    return 1


def cmd_evidence_snapshot(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        run_id = args.run or args.run_id
        snapshot = evidence_snapshot(run_id, store)
    except (DispatchError, EvidenceError) as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(snapshot)
    return 0


def cmd_evidence_emit(args: argparse.Namespace) -> int:
    from tools.agent_control.evidence.emit import emit_evidence

    try:
        if not args.state:
            print(
                "INVALID EVIDENCE_STATE_REQUIRED: emit requires --state <PATH>",
                file=sys.stderr,
            )
            return 1
        store = JsonFileRunStore(Path(args.state))
        run_id = args.run or args.run_id
        store_path = Path(args.store) if args.store else None
        result = emit_evidence(run_id, store, jsonl_path=store_path)
    except (DispatchError, EvidenceError, AgentControlError) as exc:
        code = getattr(exc, "code", "EVIDENCE_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return 1
    _print_json(result)
    return 0


def cmd_evidence_verify(args: argparse.Namespace) -> int:
    from tools.agent_control.evidence.verify import (
        load_bundle_file,
        verify_bundle,
        verify_store,
    )

    try:
        if args.bundle:
            result = verify_bundle(load_bundle_file(Path(args.bundle)))
        elif args.store:
            result = verify_store(Path(args.store))
        else:
            print(
                "INVALID EVIDENCE_VERIFY_TARGET: pass --bundle or --store",
                file=sys.stderr,
            )
            return 1
    except EvidenceError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(result)
    return 0


def cmd_evidence_show(args: argparse.Namespace) -> int:
    from tools.agent_control.evidence.store import EvidenceJsonlStore

    try:
        records = EvidenceJsonlStore(Path(args.store)).find_by_run_id(args.run)
        payload = {
            "evidence_class": "agent_run_evidence_bundle_v1",
            "run_id": args.run,
            "count": len(records),
            "bundles": records,
            "limitations": ["pilot_store_only", "not_final_ci", "not_merge_authority"],
        }
    except EvidenceError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(payload)
    return 0


def cmd_provider_capabilities(args: argparse.Namespace) -> int:
    if not args.offline:
        print(
            "INVALID PROVIDER_PROBE_LIVE_FORBIDDEN: only --offline capability "
            "snapshots are allowed in #4254",
            file=sys.stderr,
        )
        return 1
    try:
        snapshot = offline_capability_snapshot(args.provider)
    except KeyError:
        print(
            f"INVALID PROVIDER_UNKNOWN: unknown provider {args.provider!r}",
            file=sys.stderr,
        )
        return 1
    _print_json(snapshot)
    return 0


def cmd_provider_probe(args: argparse.Namespace) -> int:
    return cmd_provider_capabilities(args)


def _load_run(store: JsonFileRunStore, run_id: str) -> dict[str, Any]:
    record = store.get(run_id)
    if record is None:
        raise DispatchError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
    return record


def cmd_provider_stream(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = _load_run(store, args.run_id)
        provider_id = record.get("provider_id")
        if provider_id not in CURSOR_PROVIDER_IDS:
            raise DispatchError(
                "PROVIDER_STREAM_UNSUPPORTED",
                f"stream unsupported for provider_id={provider_id!r}",
            )
        # Offline CLI stream reconstructs from stored refs only (no network).
        payload = {
            "run_id": args.run_id,
            "provider_id": provider_id,
            "provider_run_id": record.get("provider_run_id"),
            "events": [],
            "note": "offline stream view; live SSE requires injected transport",
        }
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(payload)
    return 0


def cmd_provider_follow_up(args: argparse.Namespace) -> int:
    print(
        "INVALID PROVIDER_FOLLOW_UP_LIVE_FORBIDDEN: follow-up execute requires "
        "recorded/fake transport; live path remains fail-closed",
        file=sys.stderr,
    )
    return 1


def cmd_environment_validate(args: argparse.Namespace) -> int:
    from tools.agent_control.environment.doctor import (
        validate_all_profiles,
        validate_profile,
    )
    from tools.agent_control.errors import EnvironmentError

    try:
        if args.profile:
            payload = validate_profile(args.profile, config=Path(args.config))
        else:
            payload = validate_all_profiles(config=Path(args.config))
    except (AgentControlError, EnvironmentError) as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(payload)
    return 0


def cmd_environment_doctor(args: argparse.Namespace) -> int:
    from tools.agent_control.environment.codes import (
        VERDICT_READY_FOR_RECORDED_TEST,
        VERDICT_READY_OFFLINE_ONLY,
    )
    from tools.agent_control.environment.doctor import doctor_profile

    attestation = Path(args.attestation) if args.attestation else None
    # Offline is default; refuse any non-offline without attestation fixture.
    if not args.offline and attestation is None:
        print(
            "INVALID ENVIRONMENT_LIVE_PROBE_FORBIDDEN: doctor requires "
            "--offline or --attestation <FIXTURE>; never contacts providers",
            file=sys.stderr,
        )
        return 1
    try:
        result = doctor_profile(
            args.profile,
            config=Path(args.config),
            attestation_path=attestation,
            offline=True,
        )
    except AgentControlError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(result.as_dict())
    if result.verdict in {
        VERDICT_READY_OFFLINE_ONLY,
        VERDICT_READY_FOR_RECORDED_TEST,
    }:
        return 0
    return 1


def cmd_provider_artifacts(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = _load_run(store, args.run_id)
        refs = (record.get("delivery_receipt") or {}) if False else {}
        payload = {
            "run_id": args.run_id,
            "provider_id": record.get("provider_id"),
            "artifacts": list((record.get("result_refs") or {}).get("artifacts") or []),
            "refs": refs,
        }
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(payload)
    return 0


def cmd_provider_usage(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = _load_run(store, args.run_id)
        payload = {
            "run_id": args.run_id,
            "provider_id": record.get("provider_id"),
            "usage": record.get("usage") or {},
        }
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(payload)
    return 0


def cmd_provider_archive(args: argparse.Namespace) -> int:
    print(
        "INVALID PROVIDER_ARCHIVE_LIVE_FORBIDDEN: archive mutate requires "
        "recorded/fake transport; permanent delete is never offered",
        file=sys.stderr,
    )
    return 1


def cmd_pilot_run(args: argparse.Namespace) -> int:
    """Run ACP pilot (mock default; live Cursor only with Human-GO flags)."""
    from tools.agent_control.paths import REPO_ROOT
    from tools.agent_control.pilot import PilotError, run_pilot_from_path
    from tools.agent_control.pilot_report import PilotReportError

    provider_id = str(getattr(args, "provider", "mock") or "mock")
    human_go = bool(getattr(args, "human_go_live_cursor", False))
    auto_create_pr = bool(getattr(args, "auto_create_pr", False))
    if provider_id != "mock" and not human_go:
        print(
            "INVALID PILOT_HUMAN_GO_REQUIRED: "
            "provider!=mock requires --human-go-live-cursor",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if auto_create_pr and not human_go:
        print(
            "INVALID PILOT_HUMAN_GO_REQUIRED: "
            "--auto-create-pr requires --human-go-live-cursor",
            file=sys.stderr,
        )
        return EXIT_ERROR

    try:
        root = Path(args.repo_root) if args.repo_root else REPO_ROOT
        out = Path(args.out) if args.out else None
        state = Path(args.state) if getattr(args, "state", None) else None
        resume = getattr(args, "resume", None)
        report = run_pilot_from_path(
            Path(args.manifest),
            repo_root=root,
            out_path=out,
            provider_id=provider_id,
            human_go_live_cursor=human_go,
            resume_run_id=resume,
            state_path=state,
            auto_create_pr=auto_create_pr,
        )
    except (PilotError, PilotReportError, AgentControlError) as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return EXIT_ERROR
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID PILOT_IO: {exc}", file=sys.stderr)
        return EXIT_ERROR
    _print_json(report)
    status = str(report.get("final_status"))
    if status == "PASS":
        return EXIT_OK
    if status == "BLOCKED":
        return EXIT_BLOCKED
    if status == "HOLD":
        return EXIT_HOLD
    if status == "UNKNOWN":
        return EXIT_UNKNOWN
    return EXIT_ERROR


def cmd_pilot_verify(args: argparse.Namespace) -> int:
    from tools.agent_control.pilot_report import PilotReportError, verify_report

    try:
        report = _load_json(Path(args.report))
        if not isinstance(report, dict):
            raise PilotReportError(
                "PILOT_REPORT_TYPE_INVALID", "report must be a JSON object"
            )
        result = verify_report(report)
    except (PilotReportError, AgentControlError) as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return EXIT_ERROR
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID PILOT_IO: {exc}", file=sys.stderr)
        return EXIT_ERROR
    _print_json(result)
    return EXIT_OK


def cmd_pilot_cursor_preflight(args: argparse.Namespace) -> int:
    """Dashboardless Cursor live preflight — zero creates, zero GitHub writes."""
    from tools.agent_control.cursor_preflight import (
        CursorPreflightError,
        run_cursor_live_preflight,
    )
    from tools.agent_control.paths import REPO_ROOT

    root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    secrets = Path(args.secrets_dir) if args.secrets_dir else None
    state = Path(args.state) if args.state else None
    dash = None
    if args.dashboard_observations:
        try:
            dash = _load_json(Path(args.dashboard_observations))
        except (OSError, json.JSONDecodeError, AgentControlError) as exc:
            print(f"INVALID dashboard_observations: {exc}", file=sys.stderr)
            return EXIT_ERROR
    try:
        report = run_cursor_live_preflight(
            repository=str(args.repository),
            environment_name=str(args.environment) if args.environment else None,
            binding_mode=str(args.binding_mode),
            repo_root=root,
            secrets_dir=secrets,
            state_path=state,
            existing_agent_id=args.existing_agent_id or None,
            existing_run_id=args.existing_run_id or None,
            dashboard_observations=dash if isinstance(dash, dict) else None,
        )
    except CursorPreflightError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return EXIT_ERROR
    _print_json(report)
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return EXIT_OK if report.get("ready_for_live_run") is True else EXIT_HOLD


def cmd_pilot_cursor_support_bundle(args: argparse.Namespace) -> int:
    """Dual-run Cursor ERROR support bundle — recorded states; zero POSTs."""
    from tools.agent_control.cursor_support_bundle import (
        SupportBundleError,
        run_support_bundle_from_states,
    )
    from tools.agent_control.paths import REPO_ROOT

    root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    tracked = Path(args.tracked_summary) if args.tracked_summary else None
    shared = Path(args.shared) if args.shared else None
    try:
        result = run_support_bundle_from_states(
            state_run1_path=Path(args.state_run1),
            state_run2_path=Path(args.state_run2),
            shared_path=shared,
            output_dir=Path(args.output),
            repo_root=root,
            write_tracked_summary=tracked,
        )
    except SupportBundleError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return EXIT_ERROR
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID BUNDLE_IO: {exc}", file=sys.stderr)
        return EXIT_ERROR
    _print_json(result)
    return EXIT_OK


def _approval_exit_code(recommendation: str) -> int:
    if recommendation == "APPROVE_RECOMMENDED":
        return EXIT_OK
    if recommendation == "BLOCKED":
        return EXIT_BLOCKED
    if recommendation in {"HOLD", "REQUEST_CHANGES", "ABSTAIN"}:
        return EXIT_HOLD
    if recommendation == "UNKNOWN":
        return EXIT_UNKNOWN
    return EXIT_ERROR


def cmd_approval_context(args: argparse.Namespace) -> int:
    """Build schema-valid approval context from a local/injected snapshot."""
    from tools.agent_control.approval.context import (
        RepoPaths,
        build_approval_context,
        default_repo_paths,
    )
    from tools.agent_control.paths import REPO_ROOT

    try:
        snapshot = _load_json(Path(args.snapshot))
        if not isinstance(snapshot, dict):
            raise ApprovalError("APPROVAL_SCHEMA_INVALID", "snapshot must be a mapping")
        pr = snapshot.get("pr")
        if not isinstance(pr, dict):
            pr = {}
            snapshot["pr"] = pr
        pr["number"] = int(args.pr)

        config_root = Path(args.config)
        paths = default_repo_paths(REPO_ROOT)
        # Allow alternate config root for policy/prompt/baseline resolution.
        paths = RepoPaths(
            repo_root=REPO_ROOT,
            policy_path=config_root / "policies" / "approval" / "pr_approval.v1.yaml",
            prompt_path=config_root / "prompts" / "approval" / "pr_approval.v1.md",
            baseline_path=(
                config_root
                / "capability-baselines"
                / "approval-dashboard-export.redacted.v1.json"
            ),
            schema_path=paths.schema_path,
        )
        envelope = build_approval_context(snapshot, paths)
    except (ApprovalError, AgentControlError, OSError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "APPROVAL_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return EXIT_ERROR

    text = dump_json(envelope)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return _approval_exit_code(str(envelope.get("recommendation")))


def cmd_approval_drift(args: argparse.Namespace) -> int:
    """Emit machine-readable drift report against a redacted baseline."""
    from tools.agent_control.approval.drift import audit_drift, load_baseline
    from tools.agent_control.approval.policy import load_policy
    from tools.agent_control.approval.prompt import load_prompt
    from tools.agent_control.paths import REPO_ROOT

    try:
        baseline_path = Path(args.baseline)
        baseline = load_baseline(baseline_path)
        config_root = Path(args.config)
        policy = load_policy(
            config_root / "policies" / "approval" / "pr_approval.v1.yaml",
            repo_root=REPO_ROOT,
        )
        prompt = load_prompt(
            config_root / "prompts" / "approval" / "pr_approval.v1.md",
            repo_root=REPO_ROOT,
        )
        snapshot: dict[str, Any] = {}
        if args.snapshot:
            loaded = _load_json(Path(args.snapshot))
            if isinstance(loaded, dict):
                snapshot = loaded
        report = audit_drift(
            policy=policy, prompt=prompt, snapshot=snapshot, baseline=baseline
        )
        payload = {
            "schema_id": "cdb.pr_approval_drift_report.v1",
            "baseline_path": str(baseline_path).replace("\\", "/"),
            "baseline_present": baseline is not None,
            "policy": {
                "version": policy["version"],
                "content_sha256": policy["content_sha256"],
            },
            "prompt": {
                "version": prompt["version"],
                "content_sha256": prompt["content_sha256"],
            },
            "drift": report,
        }
    except (ApprovalError, AgentControlError, OSError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "APPROVAL_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return EXIT_ERROR

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    status = report.get("status")
    if status == "NONE":
        return EXIT_OK
    if status == "UNKNOWN":
        return EXIT_UNKNOWN
    return EXIT_HOLD


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.agent_control",
        description="CDB Agent Control Plane CLI (registry + governed dispatcher)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    registry = sub.add_parser("registry", help="Declarative agent registry commands")
    reg_sub = registry.add_subparsers(dest="registry_command", required=True)

    p_val = reg_sub.add_parser("validate", help="Validate registry desired state")
    p_val.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_ROOT),
        help="Registry file or config/agent-control root",
    )
    p_val.set_defaults(func=cmd_registry_validate)

    p_norm = reg_sub.add_parser("normalize", help="Emit normalized registry JSON")
    p_norm.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_norm.add_argument("--output")
    p_norm.set_defaults(func=cmd_registry_normalize)

    p_plan = reg_sub.add_parser(
        "plan",
        help="Build deterministic reconcile plan (desired vs observed)",
    )
    p_plan.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_plan.add_argument("--state", required=True, help="Observed state JSON/YAML")
    p_plan.add_argument("--output")
    p_plan.set_defaults(func=cmd_registry_plan)

    p_rec = reg_sub.add_parser(
        "reconcile",
        help="Reconcile desired vs observed (dry-run default; no live mutation)",
    )
    p_rec.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_rec.add_argument(
        "--state",
        help="Observed state JSON/YAML (default: empty observed set)",
    )
    p_rec.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Plan only (default)",
    )
    p_rec.add_argument(
        "--apply",
        action="store_true",
        help="Simulate apply via MockBackend only (requires --allow-mock-apply)",
    )
    p_rec.add_argument(
        "--allow-mock-apply",
        action="store_true",
        help="Acknowledge mock-only apply (still no live provider calls)",
    )
    p_rec.add_argument("--output")
    p_rec.set_defaults(func=cmd_registry_reconcile)

    p_dispatch = sub.add_parser(
        "dispatch",
        help="Governed dispatch (dry-run default; mock execute opt-in)",
    )
    p_dispatch.add_argument("--contract", required=True)
    p_dispatch.add_argument(
        "--registry",
        default=str(DEFAULT_CONFIG_ROOT),
        help="Registry file or config/agent-control root",
    )
    p_dispatch.add_argument("--agent-id", required=True)
    p_dispatch.add_argument(
        "--state",
        help="JSON run-store path (required for --execute)",
    )
    p_dispatch.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preflight + plan only (default)",
    )
    p_dispatch.add_argument(
        "--execute",
        action="store_true",
        help="Execute mock dispatch (requires --allow-mock-dispatch)",
    )
    p_dispatch.add_argument(
        "--allow-mock-dispatch",
        action="store_true",
        help="Acknowledge mock-only provider execution",
    )
    p_dispatch.add_argument(
        "--scenario",
        default="success",
        help="MockProvider scenario (tests/CLI)",
    )
    p_dispatch.add_argument("--output")
    p_dispatch.set_defaults(func=cmd_dispatch)

    p_watch = sub.add_parser("watch", help="Watch/advance a mock run")
    p_watch.add_argument("--run-id", required=True)
    p_watch.add_argument("--state", required=True)
    p_watch.set_defaults(func=cmd_watch)

    p_cancel = sub.add_parser("cancel", help="Cancel a non-terminal mock run")
    p_cancel.add_argument("--run-id", required=True)
    p_cancel.add_argument("--state", required=True)
    p_cancel.add_argument("--reason", required=True)
    p_cancel.set_defaults(func=cmd_cancel)

    p_retry = sub.add_parser("retry", help="Explicit retry as a new attempt")
    p_retry.add_argument("--previous-run-id", required=True)
    p_retry.add_argument("--contract", required=True)
    p_retry.add_argument("--reason", required=True)
    p_retry.add_argument("--registry", default=str(DEFAULT_CONFIG_ROOT))
    p_retry.add_argument("--agent-id")
    p_retry.add_argument("--state", required=True)
    p_retry.add_argument("--dry-run", action="store_true", default=True)
    p_retry.add_argument("--execute", action="store_true")
    p_retry.add_argument("--allow-mock-dispatch", action="store_true")
    p_retry.add_argument("--scenario", default="success")
    p_retry.set_defaults(func=cmd_retry)

    p_evidence = sub.add_parser(
        "evidence",
        help=(
            "Evidence surfaces: lifecycle snapshot (#4253) and run evidence "
            "bundle (#4256)"
        ),
    )
    ev_sub = p_evidence.add_subparsers(dest="evidence_command", required=False)

    p_ev_snap = ev_sub.add_parser(
        "snapshot",
        help="Dispatcher lifecycle snapshot (not agent_run_evidence bundle)",
    )
    p_ev_snap.add_argument("--run", dest="run", required=True)
    p_ev_snap.add_argument("--state", required=True)
    p_ev_snap.set_defaults(func=cmd_evidence_snapshot, run_id=None)

    p_ev_emit = ev_sub.add_parser(
        "emit",
        help="Emit deterministic cdb.agent_run_evidence.v1 bundle",
    )
    p_ev_emit.add_argument("--run", dest="run", required=True)
    p_ev_emit.add_argument("--state", required=True)
    p_ev_emit.add_argument(
        "--store",
        help="Optional JSONL pilot store path (stdout-only when omitted)",
    )
    p_ev_emit.set_defaults(func=cmd_evidence_emit, run_id=None)

    p_ev_verify = ev_sub.add_parser(
        "verify",
        help="Verify a bundle file or JSONL pilot store",
    )
    p_ev_verify.add_argument("--bundle", help="Path to a single bundle JSON file")
    p_ev_verify.add_argument("--store", help="Path to JSONL pilot store")
    p_ev_verify.set_defaults(func=cmd_evidence_verify)

    p_ev_show = ev_sub.add_parser(
        "show",
        help="Show stored bundles for a run_id from a JSONL store",
    )
    p_ev_show.add_argument("--run", required=True)
    p_ev_show.add_argument("--store", required=True)
    p_ev_show.set_defaults(func=cmd_evidence_show)

    # Legacy snapshot alias: evidence --run-id ... --state ...
    p_evidence.add_argument("--run-id", dest="run_id", default=None)
    p_evidence.add_argument(
        "--run",
        dest="run",
        default=None,
        help="Bundle entry alias; requires --state (emit path)",
    )
    p_evidence.add_argument("--state", default=None)
    p_evidence.add_argument("--store", default=None)
    p_evidence.set_defaults(func=cmd_evidence_dispatch)

    provider = sub.add_parser(
        "provider", help="Cursor provider offline/ops surface (#4254)"
    )
    prov_sub = provider.add_subparsers(dest="provider_command", required=True)

    p_caps = prov_sub.add_parser("capabilities", help="Offline capability snapshot")
    p_caps.add_argument("--provider", required=True)
    p_caps.add_argument("--offline", action="store_true", required=True)
    p_caps.set_defaults(func=cmd_provider_capabilities)

    p_probe = prov_sub.add_parser("probe", help="Offline capability probe (alias)")
    p_probe.add_argument("--provider", required=True)
    p_probe.add_argument("--offline", action="store_true", required=True)
    p_probe.set_defaults(func=cmd_provider_probe)

    p_stream = prov_sub.add_parser("stream", help="Offline stream view for a run")
    p_stream.add_argument("--run-id", required=True)
    p_stream.add_argument("--state", required=True)
    p_stream.set_defaults(func=cmd_provider_stream)

    p_fu = prov_sub.add_parser("follow-up", help="Follow-up (gated; no live execute)")
    p_fu.add_argument("--run-id", required=True)
    p_fu.add_argument("--contract", required=True)
    p_fu.set_defaults(func=cmd_provider_follow_up)

    p_art = prov_sub.add_parser("artifacts", help="Artifact helpers")
    art_sub = p_art.add_subparsers(dest="artifacts_command", required=True)
    p_art_list = art_sub.add_parser("list", help="List artifact refs for a run")
    p_art_list.add_argument("--run-id", required=True)
    p_art_list.add_argument("--state", required=True)
    p_art_list.set_defaults(func=cmd_provider_artifacts)

    p_usage = prov_sub.add_parser("usage", help="Usage snapshot from run store")
    p_usage.add_argument("--run-id", required=True)
    p_usage.add_argument("--state", required=True)
    p_usage.set_defaults(func=cmd_provider_usage)

    p_arch = prov_sub.add_parser("archive", help="Archive (gated; no live mutate)")
    p_arch.add_argument("--run-id", required=True)
    p_arch.add_argument("--state", required=True)
    p_arch.set_defaults(func=cmd_provider_archive)

    environment = sub.add_parser(
        "environment",
        help="Governed environment profiles + fail-closed doctor (#4255)",
    )
    env_sub = environment.add_subparsers(dest="environment_command", required=True)

    p_env_val = env_sub.add_parser(
        "validate",
        help="Validate environment profiles (all or one)",
    )
    p_env_val.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_env_val.add_argument(
        "--profile",
        help="Optional single profile_id (default: validate all + cursor config)",
    )
    p_env_val.set_defaults(func=cmd_environment_validate)

    p_env_doc = env_sub.add_parser(
        "doctor",
        help="Offline/fixture environment doctor (never contacts Cursor)",
    )
    p_env_doc.add_argument("--profile", required=True)
    p_env_doc.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_env_doc.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Offline doctor (default)",
    )
    p_env_doc.add_argument(
        "--attestation",
        help="Optional recorded/fake attestation fixture JSON",
    )
    p_env_doc.set_defaults(func=cmd_environment_doctor)

    approval = sub.add_parser(
        "approval",
        help="Repo-backed PR approval context + drift audit (#4257)",
    )
    appr_sub = approval.add_subparsers(dest="approval_command", required=True)

    p_appr_ctx = appr_sub.add_parser(
        "context",
        help="Build cdb.pr_approval_context.v1 from an injected snapshot",
    )
    p_appr_ctx.add_argument("--pr", type=int, required=True)
    p_appr_ctx.add_argument("--snapshot", required=True, help="Local snapshot JSON")
    p_appr_ctx.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_appr_ctx.add_argument("--output", help="Optional output path (else stdout)")
    p_appr_ctx.set_defaults(func=cmd_approval_context)

    p_appr_drift = appr_sub.add_parser(
        "drift",
        help="Audit policy/prompt/adapter/protection drift against baseline",
    )
    p_appr_drift.add_argument("--baseline", required=True)
    p_appr_drift.add_argument(
        "--snapshot",
        help="Optional injected snapshot for adapter/protection view",
    )
    p_appr_drift.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_appr_drift.add_argument("--output", help="Optional output path (else stdout)")
    p_appr_drift.set_defaults(func=cmd_approval_drift)

    pilot = sub.add_parser(
        "pilot",
        help="ACP E2E pilot (#4258; mock default; live Cursor needs Human-GO; Refs only)",
    )
    pilot_sub = pilot.add_subparsers(dest="pilot_command", required=True)

    p_pilot_run = pilot_sub.add_parser(
        "run",
        help="Run ACP pilot chain and emit pilot report (mock default)",
    )
    p_pilot_run.add_argument("--manifest", required=True)
    p_pilot_run.add_argument("--out", help="Optional report output path")
    p_pilot_run.add_argument(
        "--repo-root",
        default=None,
        help="Optional repo root (defaults to package REPO_ROOT)",
    )
    p_pilot_run.add_argument(
        "--provider",
        choices=("mock", "cursor-cloud-api"),
        default="mock",
        help="Provider adapter (default mock; cursor-cloud-api needs Human-GO)",
    )
    p_pilot_run.add_argument(
        "--human-go-live-cursor",
        action="store_true",
        help="Explicit Human-GO for live Cursor cloud pilot (required when provider!=mock)",
    )
    p_pilot_run.add_argument(
        "--resume",
        default=None,
        help="Resume an existing run_id from --state (skip dispatch)",
    )
    p_pilot_run.add_argument(
        "--state",
        default=None,
        help="JsonFileRunStore path for live/resume persistence",
    )
    p_pilot_run.add_argument(
        "--auto-create-pr",
        action="store_true",
        help="Optional Cursor autoCreatePR (requires --human-go-live-cursor)",
    )
    p_pilot_run.set_defaults(func=cmd_pilot_run)

    p_pilot_verify = pilot_sub.add_parser(
        "verify",
        help="Verify a pilot report digest + authority limits",
    )
    p_pilot_verify.add_argument("--report", required=True)
    p_pilot_verify.set_defaults(func=cmd_pilot_verify)

    p_pilot_pf = pilot_sub.add_parser(
        "cursor-preflight",
        help=(
            "Dashboardless Cursor live preflight (official API+gh+environment.json; "
            "zero creates; Refs #4258)"
        ),
    )
    p_pilot_pf.add_argument(
        "--repository",
        default="jannekbuengener/Claire_de_Binare",
        help="owner/name repository",
    )
    p_pilot_pf.add_argument(
        "--environment",
        default="jannekbuengener/Claire_de_Binare",
        help="Requested cloud environment name (supporting; see --binding-mode)",
    )
    p_pilot_pf.add_argument(
        "--binding-mode",
        choices=("repos_plus_repo_config", "named_cloud_env"),
        default="repos_plus_repo_config",
        help="Official create binding: repos+environment.json (default) or named env",
    )
    p_pilot_pf.add_argument(
        "--state", default=None, help="Optional local runstore path"
    )
    p_pilot_pf.add_argument("--out", default=None, help="Optional JSON report path")
    p_pilot_pf.add_argument("--repo-root", default=None)
    p_pilot_pf.add_argument("--secrets-dir", default=None)
    p_pilot_pf.add_argument(
        "--dashboard-observations",
        default=None,
        help="Optional JSON file with supporting (non-authoritative) dashboard notes",
    )
    p_pilot_pf.add_argument(
        "--existing-agent-id",
        default="bc-d1ba82b5-db1a-5040-b50a-2007040a65c7",
    )
    p_pilot_pf.add_argument(
        "--existing-run-id",
        default="run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b",
    )
    p_pilot_pf.set_defaults(func=cmd_pilot_cursor_preflight)

    p_pilot_sb = pilot_sub.add_parser(
        "cursor-support-bundle",
        help=(
            "Dual-run Cursor ERROR support bundle (recorded states; zero POSTs; "
            "Refs #4258)"
        ),
    )
    p_pilot_sb.add_argument("--state-run1", required=True)
    p_pilot_sb.add_argument("--state-run2", required=True)
    p_pilot_sb.add_argument(
        "--shared",
        default=None,
        help="Optional shared metadata JSON (/v1/me, repos listing flags)",
    )
    p_pilot_sb.add_argument(
        "--output",
        required=True,
        help="Gitignored output directory for redacted bundle + support draft",
    )
    p_pilot_sb.add_argument(
        "--tracked-summary",
        default=None,
        help="Optional tracked markdown summary path under docs/evidence/",
    )
    p_pilot_sb.add_argument("--repo-root", default=None)
    p_pilot_sb.set_defaults(func=cmd_pilot_cursor_support_bundle)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
