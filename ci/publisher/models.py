"""Typed models for status publisher payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

StatusState = Literal["error", "failure", "pending", "success"]


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

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.intended_payload is not None:
            data["intended_payload"] = self.intended_payload.to_api_body()
            data["intended_payload"]["sha"] = self.intended_payload.sha
        return data
