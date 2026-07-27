"""Publish-gate orchestration over shared local CI evidence validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ci.lib.evidence import (
    DEFAULT_FRESHNESS_HOURS,
    DEFAULT_REQUIRED_STAGES,
    EvidenceError,
    assert_evidence_fresh,
    assert_publishable,
    load_and_validate_manifest,
    manifest_digest,
    optional_skipped_stages,
    verify_artifact_hashes,
)
from ci.lib.gitinfo import (
    EXPECTED_REPOSITORY,
    assert_expected_repository,
    collect_git_info,
)
from ci.publisher.exceptions import PublisherError
from ci.publisher.models import StatusPayload, ValidationResult

SUCCESS_SUMMARY = "Local Docker CI evidence verified for exact commit SHA."
FAILURE_SUMMARY = "Local Docker CI evidence rejected or pipeline failed."


def resolve_repository(
    *,
    repository: str | None,
    repo_root: Path | None,
    manifest: dict[str, Any],
) -> str:
    """Bind publication to jannekbuengener/Claire_de_Binare only."""
    candidates: list[str] = []
    if repository:
        candidates.append(repository)
    if repo_root is not None:
        try:
            git = collect_git_info(repo_root)
            if git.remote_url:
                candidates.append(git.remote_url)
            candidates.append(git.repo_name)
        except RuntimeError as exc:
            raise PublisherError(f"Unable to resolve git repository: {exc}") from exc
    candidates.append(str(manifest.get("repo_name", "")))
    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return assert_expected_repository(candidate)
        except ValueError as exc:
            last_error = exc
            continue
    raise PublisherError(
        f"Foreign or unresolved repository (expected {EXPECTED_REPOSITORY}): "
        f"{last_error}"
    )


def build_status_payload(
    *,
    commit_sha: str,
    context: str,
    ok: bool,
    target_url: str | None,
    optional_skipped: list[dict[str, str]],
) -> StatusPayload:
    if ok:
        description = SUCCESS_SUMMARY
        if optional_skipped:
            names = ",".join(s["name"] for s in optional_skipped)
            description = f"{SUCCESS_SUMMARY} Optional skipped: {names}"
        state = "success"
    else:
        description = FAILURE_SUMMARY
        state = "failure"
    return StatusPayload(
        sha=commit_sha,
        state=state,  # type: ignore[arg-type]
        context=context,
        description=description,
        target_url=target_url,
    )


def validate_evidence_for_publish(
    evidence_dir: Path,
    *,
    commit_sha: str,
    repository: str | None = None,
    repo_root: Path | None = None,
    status_context: str = "cdb-local-ci",
    freshness_hours: float = DEFAULT_FRESHNESS_HOURS,
    required_stages: tuple[str, ...] = DEFAULT_REQUIRED_STAGES,
    target_url: str | None = None,
    publish_failure_status: bool = False,
) -> ValidationResult:
    """Validate evidence for the exact commit SHA.

    On validation failure returns ``ok=False`` with reason. Never returns a
    success payload when validation failed. When ``publish_failure_status`` is
    false (default), ``intended_payload`` is None on failure so callers do not
    accidentally post green or unintended failure noise during dry-run rejects.
    """
    run_dir = evidence_dir
    try:
        manifest = load_and_validate_manifest(run_dir, expected_commit_sha=commit_sha)
        verify_artifact_hashes(run_dir, manifest)
        assert_evidence_fresh(manifest, max_age_hours=freshness_hours)
        assert_publishable(manifest, required_stages=required_stages)
        repo_slug = resolve_repository(
            repository=repository, repo_root=repo_root, manifest=manifest
        )
        digest = manifest_digest(run_dir)
        skipped = optional_skipped_stages(manifest)
        payload = build_status_payload(
            commit_sha=commit_sha,
            context=status_context,
            ok=True,
            target_url=target_url,
            optional_skipped=skipped,
        )
        return ValidationResult(
            ok=True,
            run_id=str(manifest.get("run_id", "")),
            commit_sha=str(manifest.get("commit_sha", "")),
            repository=repo_slug,
            overall_status=str(manifest.get("overall_status", "")),
            manifest_sha256=digest,
            optional_skipped=skipped,
            intended_payload=payload,
        )
    except (EvidenceError, PublisherError, ValueError) as exc:
        reason = str(exc)
        payload = None
        if publish_failure_status:
            payload = build_status_payload(
                commit_sha=commit_sha,
                context=status_context,
                ok=False,
                target_url=target_url,
                optional_skipped=[],
            )
        # Best-effort fields from partial load.
        run_id = ""
        overall = ""
        digest = ""
        repo_slug = repository or EXPECTED_REPOSITORY
        try:
            if (run_dir / "manifest.json").is_file():
                # Do not re-raise; only for diagnostics.
                from ci.lib.evidence import sha256_bytes

                raw = (run_dir / "manifest.json").read_bytes()
                import json

                partial = json.loads(raw.decode("utf-8"))
                run_id = str(partial.get("run_id", ""))
                overall = str(partial.get("overall_status", ""))
                digest = sha256_bytes(raw)
        except Exception:  # noqa: BLE001 — diagnostics only
            pass
        return ValidationResult(
            ok=False,
            run_id=run_id,
            commit_sha=commit_sha,
            repository=repo_slug,
            overall_status=overall,
            manifest_sha256=digest,
            reason=reason,
            intended_payload=payload,
        )
