"""Typed models for status publisher payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

StatusState = Literal["error", "failure", "pending", "success"]
CheckRunConclusion = Literal["success", "failure"]
PublisherBackendName = Literal["commit-status", "check-run"]

CHECK_RUN_NAME = "cdb-local-ci"
SHADOW_CHECK_RUN_NAME = "cdb-local-ci-app-preview"
ALLOWED_CHECK_RUN_CONCLUSIONS = frozenset({"success", "failure"})


@dataclass(frozen=True)
class StatusPayload:
    """Deterministic Commit Status payload for GitHub."""

    sha: str
    state: StatusState
    context: str
    description: str
    target_url: str | None = None

    def to_api_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "state": self.state,
            "context": self.context,
            "description": self.description[:140],
        }
        if self.target_url:
            body["target_url"] = self.target_url
        return body


@dataclass(frozen=True)
class CheckRunPayload:
    """Deterministic Check Run payload bound to a GitHub App identity."""

    name: str
    head_sha: str
    conclusion: CheckRunConclusion
    started_at: str
    completed_at: str
    external_id: str
    output_title: str
    output_summary: str
    details_url: str | None = None
    status: Literal["completed"] = "completed"

    def __post_init__(self) -> None:
        if not self.head_sha:
            raise ValueError("Check Run success/failure requires exact head_sha")
        if self.conclusion not in ALLOWED_CHECK_RUN_CONCLUSIONS:
            raise ValueError(f"Unknown Check Run conclusion: {self.conclusion!r}")
        if self.status != "completed":
            raise ValueError("Check Run status must be completed")
        if not self.external_id:
            raise ValueError("Check Run external_id is required")
        if not self.name:
            raise ValueError("Check Run name is required")

    def to_api_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": self.name,
            "head_sha": self.head_sha,
            "status": self.status,
            "conclusion": self.conclusion,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "external_id": self.external_id,
            "output": {
                "title": self.output_title[:1024],
                "summary": self.output_summary[:65535],
            },
        }
        if self.details_url:
            body["details_url"] = self.details_url
        return body


def build_check_run_external_id(*, run_id: str, commit_sha: str) -> str:
    """Deterministic external_id from evidence run_id and commit SHA."""
    if not run_id or not commit_sha:
        raise ValueError("external_id requires non-empty run_id and commit_sha")
    return f"{run_id}:{commit_sha.lower()}"


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a backend publish attempt after optional remote verification."""

    ok: bool
    publisher_backend: PublisherBackendName
    github_object_type: str
    remote_id: int | None
    head_sha: str
    dry_run: bool
    idempotent_noop: bool
    remote_verification_status: str
    payload_body: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)
    external_id: str | None = None
    github_app_id: int | None = None
    github_installation_id: int | None = None
    check_run_name: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of evidence validation for publish / dry-run."""

    ok: bool
    run_id: str
    commit_sha: str
    repository: str
    overall_status: str
    manifest_sha256: str
    optional_skipped: list[dict[str, str]] = field(default_factory=list)
    reason: str | None = None
    intended_payload: StatusPayload | None = None
    started_at_utc: str | None = None
    ended_at_utc: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.intended_payload is not None:
            data["intended_payload"] = self.intended_payload.to_api_body()
            data["intended_payload"]["sha"] = self.intended_payload.sha
        return data
