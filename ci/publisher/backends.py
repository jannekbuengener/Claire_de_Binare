"""Publisher backends: Commit Status (interim) and App-bound Check Runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

from ci.publisher import EXPECTED_REPOSITORY
from ci.publisher.app_auth import (
    APP_ID_ALIAS_ENV,
    APP_ID_ENV,
    INSTALLATION_ID_ALIAS_ENV,
    INSTALLATION_ID_ENV,
    mint_installation_token,
)
from ci.publisher.exceptions import AuthenticationError, GitHubApiError, PublisherError
from ci.publisher.github_client import (
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_API,
    GitHubResponse,
    GitHubStatusClient,
    Transport,
    _default_transport,
)
from ci.publisher.models import (
    CHECK_RUN_NAME,
    CheckRunPayload,
    PublishResult,
    StatusPayload,
)
from ci.publisher.redaction import redact_mapping, redact_text

APP_INSTALLATION_TOKEN_ENV = "CDB_GH_APP_INSTALLATION_TOKEN"
EXPECTED_APP_ID_ENV = APP_ID_ENV
EXPECTED_INSTALLATION_ID_ENV = INSTALLATION_ID_ENV
ALLOWED_BACKENDS = frozenset({"commit-status", "check-run"})
_DEFAULT_OWNER, _DEFAULT_REPO = EXPECTED_REPOSITORY.split("/", 1)


def parse_positive_int(value: object, *, field_name: str) -> int:
    """Parse a required positive integer (App / Installation ID)."""
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PublisherError(
            f"{field_name} must be a positive integer, got {value!r}"
        ) from exc
    if parsed <= 0:
        raise PublisherError(f"{field_name} must be a positive integer, got {parsed}")
    return parsed


def resolve_app_installation_token(
    *,
    explicit: str | None = None,
    transport: Transport | None = None,
) -> str:
    """Resolve GitHub App installation token — never gh auth / GITHUB_TOKEN / GH_TOKEN.

    Priority:
    1. explicit test inject
    2. ``CDB_GH_APP_INSTALLATION_TOKEN``
    3. auto-mint from App ID + Installation ID + private key (path or inline)
    4. ``AuthenticationError`` (no PAT / ``gh auth`` fallback)
    """
    if explicit is not None:
        token = explicit.strip()
        if not token:
            raise AuthenticationError("Empty GitHub App installation token")
        return token
    token = (os.environ.get(APP_INSTALLATION_TOKEN_ENV) or "").strip()
    if token:
        return token
    try:
        return mint_installation_token(transport=transport)
    except AuthenticationError as exc:
        raise AuthenticationError(
            f"Missing {APP_INSTALLATION_TOKEN_ENV} and App credential auto-mint "
            f"failed ({exc}); Check Run mode refuses GITHUB_TOKEN / GH_TOKEN / "
            "gh auth token as App identity proof"
        ) from exc
    except (GitHubApiError, PublisherError) as exc:
        raise AuthenticationError(
            f"Missing {APP_INSTALLATION_TOKEN_ENV} and App credential auto-mint "
            f"failed ({exc}); Check Run mode refuses GITHUB_TOKEN / GH_TOKEN / "
            "gh auth token as App identity proof"
        ) from exc


def resolve_expected_app_id(
    *, cli_value: int | None = None, require: bool = True
) -> int | None:
    if cli_value is not None:
        return parse_positive_int(cli_value, field_name="expected-app-id")
    env_raw = (os.environ.get(EXPECTED_APP_ID_ENV) or "").strip()
    if not env_raw:
        env_raw = (os.environ.get(APP_ID_ALIAS_ENV) or "").strip()
    if env_raw:
        return parse_positive_int(env_raw, field_name=EXPECTED_APP_ID_ENV)
    if require:
        raise PublisherError(
            f"Check Run mode requires --expected-app-id or {EXPECTED_APP_ID_ENV} "
            f"(alias {APP_ID_ALIAS_ENV})"
        )
    return None


def resolve_expected_installation_id(
    *, cli_value: int | None = None, require: bool = True
) -> int | None:
    if cli_value is not None:
        return parse_positive_int(cli_value, field_name="expected-installation-id")
    env_raw = (os.environ.get(EXPECTED_INSTALLATION_ID_ENV) or "").strip()
    if not env_raw:
        env_raw = (os.environ.get(INSTALLATION_ID_ALIAS_ENV) or "").strip()
    if env_raw:
        return parse_positive_int(env_raw, field_name=EXPECTED_INSTALLATION_ID_ENV)
    if require:
        raise PublisherError(
            "Check Run mode requires --expected-installation-id or "
            f"{EXPECTED_INSTALLATION_ID_ENV} (alias {INSTALLATION_ID_ALIAS_ENV})"
        )
    return None


class PublisherBackend(Protocol):
    """Internal protocol for deterministic publish + remote verification."""

    name: str

    def publish(
        self,
        *,
        status_payload: StatusPayload | None = None,
        check_run_payload: CheckRunPayload | None = None,
        dry_run: bool = False,
    ) -> PublishResult: ...


@dataclass(frozen=True)
class CommitStatusBackend:
    """Wraps existing Commit Status publish behaviour during the transition."""

    client: GitHubStatusClient
    name: str = "commit-status"

    def publish(
        self,
        *,
        status_payload: StatusPayload | None = None,
        check_run_payload: CheckRunPayload | None = None,
        dry_run: bool = False,
    ) -> PublishResult:
        if check_run_payload is not None:
            raise PublisherError(
                "CommitStatusBackend rejects Check Run payloads "
                "(no silent backend mix)"
            )
        if status_payload is None:
            raise PublisherError("CommitStatusBackend requires StatusPayload")
        body = status_payload.to_api_body()
        if dry_run:
            raw = {"dry_run": True, "sha": status_payload.sha, "body": body}
            return PublishResult(
                ok=True,
                publisher_backend="commit-status",
                github_object_type="commit_status",
                remote_id=None,
                head_sha=status_payload.sha,
                dry_run=True,
                idempotent_noop=False,
                remote_verification_status="dry_run",
                payload_body=body,
                raw=raw,
            )
        raw = self.client.create_commit_status(status_payload, dry_run=False)
        status_id = raw.get("id")
        return PublishResult(
            ok=True,
            publisher_backend="commit-status",
            github_object_type="commit_status",
            remote_id=int(status_id) if status_id is not None else None,
            head_sha=status_payload.sha,
            dry_run=False,
            idempotent_noop=False,
            remote_verification_status="written",
            payload_body=body,
            raw=redact_mapping(raw) if isinstance(raw, dict) else {"result": raw},
        )


class CheckRunBackend:
    """Create and verify GitHub Check Runs with an App installation token only."""

    name = "check-run"

    def __init__(
        self,
        *,
        token: str,
        expected_app_id: int,
        expected_installation_id: int,
        owner: str = _DEFAULT_OWNER,
        repo: str = _DEFAULT_REPO,
        transport: Transport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not token:
            raise AuthenticationError("Empty GitHub App installation token")
        self._token = token
        self.expected_app_id = parse_positive_int(
            expected_app_id, field_name="expected_app_id"
        )
        self.expected_installation_id = parse_positive_int(
            expected_installation_id, field_name="expected_installation_id"
        )
        self.owner = owner
        self.repo = repo
        if f"{owner}/{repo}" != EXPECTED_REPOSITORY:
            raise PublisherError(
                "CheckRunBackend refuses non-canonical repository target"
            )
        self._transport = transport or _default_transport
        self._timeout = timeout_seconds
        self.write_calls: list[dict[str, Any]] = []

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cdb-local-ci-check-run-publisher",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> GitHubResponse:
        url = f"{GITHUB_API}{path}"
        encoded = (
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if body is not None
            else None
        )
        try:
            response = self._transport(
                method, url, self._headers(), encoded, self._timeout
            )
        except TimeoutError as exc:
            raise GitHubApiError("GitHub Check Run API request timed out") from exc
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining == "0" and response.status_code in {403, 429}:
            raise GitHubApiError("GitHub API rate limit prevents reliable verification")
        return response

    def _raise_for_status(self, response: GitHubResponse, *, action: str) -> None:
        if response.status_code in {401, 403}:
            raise AuthenticationError(
                f"Insufficient App permission to {action} Check Run"
            )
        if response.status_code == 429:
            raise GitHubApiError("GitHub API rate limit prevents Check Run publish")
        if response.status_code in {404, 422}:
            raise GitHubApiError(
                f"Check Run {action} failed HTTP {response.status_code}: "
                f"{redact_mapping(response.body)}"
            )
        if response.status_code >= 400:
            raise GitHubApiError(
                f"Ambiguous Check Run {action} HTTP {response.status_code}: "
                f"{redact_mapping(response.body)}"
            )

    def get_check_run(self, check_run_id: int) -> dict[str, Any]:
        path = f"/repos/{self.owner}/{self.repo}/check-runs/{int(check_run_id)}"
        response = self._request("GET", path)
        self._raise_for_status(response, action="read")
        if not isinstance(response.body, dict):
            raise GitHubApiError("Ambiguous Check Run read payload")
        return response.body

    def list_check_runs_for_sha(
        self, sha: str, *, check_name: str | None = None
    ) -> list[dict[str, Any]]:
        path = f"/repos/{self.owner}/{self.repo}/commits/{quote(sha)}/check-runs"
        if check_name:
            path = f"{path}?check_name={quote(check_name)}&filter=latest"
        response = self._request("GET", path)
        self._raise_for_status(response, action="list")
        body = response.body
        if not isinstance(body, dict):
            raise GitHubApiError("Ambiguous Check Run list payload")
        runs = body.get("check_runs")
        if not isinstance(runs, list):
            raise GitHubApiError("Ambiguous Check Run list check_runs field")
        return [item for item in runs if isinstance(item, dict)]

    def find_by_external_id(
        self, *, sha: str, external_id: str, check_name: str
    ) -> dict[str, Any] | None:
        matches = [
            run
            for run in self.list_check_runs_for_sha(sha, check_name=check_name)
            if str(run.get("external_id") or "") == external_id
        ]
        if not matches:
            # Broader scan without name filter in case name drifted.
            matches = [
                run
                for run in self.list_check_runs_for_sha(sha)
                if str(run.get("external_id") or "") == external_id
            ]
        if not matches:
            return None
        if len(matches) > 1:
            raise GitHubApiError(
                f"Ambiguous Check Run external_id {external_id!r}: "
                f"{len(matches)} matches"
            )
        return matches[0]

    def verify_remote_check_run(
        self,
        remote: dict[str, Any],
        *,
        payload: CheckRunPayload,
    ) -> dict[str, Any]:
        app = remote.get("app")
        if not isinstance(app, dict) or app.get("id") is None:
            raise GitHubApiError("Remote Check Run missing app identity")
        remote_app_id = parse_positive_int(app.get("id"), field_name="remote app.id")
        if remote_app_id != self.expected_app_id:
            raise GitHubApiError(
                f"Remote app.id {remote_app_id} does not match expected "
                f"{self.expected_app_id}"
            )
        remote_name = str(remote.get("name") or "")
        if remote_name != payload.name:
            raise GitHubApiError(
                f"Remote Check Run name {remote_name!r} != {payload.name!r}"
            )
        remote_sha = str(remote.get("head_sha") or "").lower()
        if remote_sha != payload.head_sha.lower():
            raise GitHubApiError(
                f"Remote head_sha {remote_sha} != {payload.head_sha.lower()}"
            )
        if str(remote.get("status") or "") != "completed":
            raise GitHubApiError(
                f"Remote Check Run status is not completed: {remote.get('status')!r}"
            )
        if str(remote.get("conclusion") or "") != payload.conclusion:
            raise GitHubApiError(
                f"Remote conclusion {remote.get('conclusion')!r} != "
                f"{payload.conclusion!r}"
            )
        if str(remote.get("external_id") or "") != payload.external_id:
            raise GitHubApiError(
                f"Remote external_id {remote.get('external_id')!r} != "
                f"{payload.external_id!r}"
            )
        return {
            "remote_verification_status": "verified",
            "github_app_id": remote_app_id,
            "github_check_run_id": int(remote["id"]) if remote.get("id") else None,
            "check_run_name": remote_name,
            "head_sha": remote_sha,
            "external_id": payload.external_id,
        }

    def _assert_no_external_id_conflict(
        self, existing: dict[str, Any], payload: CheckRunPayload
    ) -> None:
        existing_sha = str(existing.get("head_sha") or "").lower()
        if existing_sha and existing_sha != payload.head_sha.lower():
            raise PublisherError(
                f"external_id {payload.external_id!r} already bound to SHA "
                f"{existing_sha}, refusing {payload.head_sha.lower()}"
            )
        existing_conclusion = str(existing.get("conclusion") or "")
        if existing_conclusion and existing_conclusion != payload.conclusion:
            raise PublisherError(
                f"external_id {payload.external_id!r} already concluded "
                f"{existing_conclusion!r}, refusing {payload.conclusion!r}"
            )

    def publish(
        self,
        *,
        status_payload: StatusPayload | None = None,
        check_run_payload: CheckRunPayload | None = None,
        dry_run: bool = False,
    ) -> PublishResult:
        if status_payload is not None:
            raise PublisherError(
                "CheckRunBackend rejects Commit Status payloads "
                "(no silent fallback to Commit Status)"
            )
        if check_run_payload is None:
            raise PublisherError("CheckRunBackend requires CheckRunPayload")
        payload = check_run_payload
        if payload.conclusion == "success" and not payload.head_sha:
            raise GitHubApiError("Refusing success Check Run without commit SHA")
        body = payload.to_api_body()
        record = {
            "head_sha": payload.head_sha,
            "body": body,
            "dry_run": dry_run,
            "expected_app_id": self.expected_app_id,
            "expected_installation_id": self.expected_installation_id,
        }
        self.write_calls.append(record)
        if dry_run:
            return PublishResult(
                ok=True,
                publisher_backend="check-run",
                github_object_type="check_run",
                remote_id=None,
                head_sha=payload.head_sha,
                dry_run=True,
                idempotent_noop=False,
                remote_verification_status="dry_run",
                payload_body=body,
                raw={"dry_run": True, "body": body},
                external_id=payload.external_id,
                github_app_id=self.expected_app_id,
                github_installation_id=self.expected_installation_id,
                check_run_name=payload.name,
            )

        existing = self.find_by_external_id(
            sha=payload.head_sha,
            external_id=payload.external_id,
            check_name=payload.name or CHECK_RUN_NAME,
        )
        if existing is not None:
            self._assert_no_external_id_conflict(existing, payload)
            verified = self.verify_remote_check_run(existing, payload=payload)
            return PublishResult(
                ok=True,
                publisher_backend="check-run",
                github_object_type="check_run",
                remote_id=verified.get("github_check_run_id"),
                head_sha=payload.head_sha,
                dry_run=False,
                idempotent_noop=True,
                remote_verification_status="verified",
                payload_body=body,
                raw=redact_mapping(existing),
                external_id=payload.external_id,
                github_app_id=self.expected_app_id,
                github_installation_id=self.expected_installation_id,
                check_run_name=payload.name,
            )

        path = f"/repos/{self.owner}/{self.repo}/check-runs"
        try:
            response = self._request("POST", path, body=body)
        except GitHubApiError as exc:
            # Ambiguous write → attempt readback by external_id instead of blind retry.
            if "timed out" in str(exc).lower():
                recovered = self.find_by_external_id(
                    sha=payload.head_sha,
                    external_id=payload.external_id,
                    check_name=payload.name,
                )
                if recovered is None:
                    raise GitHubApiError(
                        "Check Run write timed out and remote readback found nothing"
                    ) from exc
                self._assert_no_external_id_conflict(recovered, payload)
                verified = self.verify_remote_check_run(recovered, payload=payload)
                return PublishResult(
                    ok=True,
                    publisher_backend="check-run",
                    github_object_type="check_run",
                    remote_id=verified.get("github_check_run_id"),
                    head_sha=payload.head_sha,
                    dry_run=False,
                    idempotent_noop=False,
                    remote_verification_status="verified_after_timeout",
                    payload_body=body,
                    raw=redact_mapping(recovered),
                    external_id=payload.external_id,
                    github_app_id=self.expected_app_id,
                    github_installation_id=self.expected_installation_id,
                    check_run_name=payload.name,
                )
            raise

        self._raise_for_status(response, action="create")
        if not isinstance(response.body, dict):
            raise GitHubApiError("Ambiguous Check Run create response")
        created = response.body
        check_run_id = created.get("id")
        if check_run_id is None:
            raise GitHubApiError("Check Run create response missing id")
        # Mandatory readback — publish is confirmed only after verified remote.
        remote = self.get_check_run(int(check_run_id))
        verified = self.verify_remote_check_run(remote, payload=payload)
        return PublishResult(
            ok=True,
            publisher_backend="check-run",
            github_object_type="check_run",
            remote_id=verified.get("github_check_run_id"),
            head_sha=payload.head_sha,
            dry_run=False,
            idempotent_noop=False,
            remote_verification_status="verified",
            payload_body=body,
            raw=redact_mapping(remote),
            external_id=payload.external_id,
            github_app_id=self.expected_app_id,
            github_installation_id=self.expected_installation_id,
            check_run_name=payload.name,
        )


def build_publisher_backend(
    *,
    backend: str,
    status_client: GitHubStatusClient | None = None,
    app_token: str | None = None,
    expected_app_id: int | None = None,
    expected_installation_id: int | None = None,
    owner: str = _DEFAULT_OWNER,
    repo: str = _DEFAULT_REPO,
    transport: Transport | None = None,
) -> PublisherBackend:
    if backend not in ALLOWED_BACKENDS:
        raise PublisherError(
            f"Unknown publisher backend {backend!r}; "
            f"allowed: {sorted(ALLOWED_BACKENDS)}"
        )
    if backend == "commit-status":
        if status_client is None:
            raise PublisherError("commit-status backend requires GitHubStatusClient")
        return CommitStatusBackend(client=status_client)
    token = resolve_app_installation_token(explicit=app_token)
    app_id = resolve_expected_app_id(cli_value=expected_app_id, require=True)
    installation_id = resolve_expected_installation_id(
        cli_value=expected_installation_id, require=True
    )
    assert app_id is not None and installation_id is not None
    return CheckRunBackend(
        token=token,
        expected_app_id=app_id,
        expected_installation_id=installation_id,
        owner=owner,
        repo=repo,
        transport=transport,
    )
