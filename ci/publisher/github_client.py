"""GitHub Commit Status client (Phase 3a). Check Runs require a GitHub App."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote

from ci.publisher.exceptions import AuthenticationError, GitHubApiError
from ci.publisher.models import StatusPayload
from ci.publisher.redaction import redact_mapping, redact_text

GITHUB_API = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class GitHubResponse:
    status_code: int
    body: Any
    headers: dict[str, str]


Transport = Callable[[str, str, dict[str, str], bytes | None, float], GitHubResponse]


def resolve_token(*, explicit: str | None = None) -> str:
    """Resolve token from explicit value or environment / gh CLI.

    Never logs the token. Prefer ``GITHUB_TOKEN``, then ``GH_TOKEN``, then
    ``gh auth token``.
    """
    if explicit:
        # Callers must not pass CLI secrets; still accept programmatic inject for tests.
        token = explicit.strip()
        if token:
            return token
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthenticationError(
            f"Unable to resolve GitHub token from environment or gh: {exc}"
        ) from exc
    token = (result.stdout or "").strip()
    if result.returncode != 0 or not token:
        raise AuthenticationError(
            "No GitHub token available. Set GITHUB_TOKEN or authenticate via gh."
        )
    return token


def _default_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
) -> GitHubResponse:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            parsed: Any
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    parsed = {"raw": redact_text(raw.decode("utf-8", errors="replace"))}
            else:
                parsed = {}
            header_map = {k.lower(): v for k, v in response.headers.items()}
            return GitHubResponse(
                status_code=getattr(response, "status", 200),
                body=redact_mapping(parsed),
                headers=header_map,
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        parsed: Any
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {"message": str(exc)}
        except json.JSONDecodeError:
            parsed = {"message": redact_text(raw.decode("utf-8", errors="replace"))}
        headers = {
            k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])
        }
        return GitHubResponse(
            status_code=exc.code,
            body=redact_mapping(parsed),
            headers=headers,
        )
    except urllib.error.URLError as exc:
        raise GitHubApiError(
            f"Network failure talking to GitHub API: {redact_text(str(exc.reason))}"
        ) from exc
    except TimeoutError as exc:
        raise GitHubApiError("GitHub API request timed out") from exc


class GitHubStatusClient:
    """Minimal Commit Status client. Does not create Check Runs."""

    def __init__(
        self,
        *,
        token: str,
        owner: str = "jannekbuengener",
        repo: str = "Claire_de_Binare",
        transport: Transport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not token:
            raise AuthenticationError("Empty GitHub token")
        self._token = token
        self.owner = owner
        self.repo = repo
        self._transport = transport or _default_transport
        self._timeout = timeout_seconds
        self.write_calls: list[dict[str, Any]] = []

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cdb-local-ci-status-publisher",
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
            raise GitHubApiError("GitHub API request timed out") from exc
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining == "0" and response.status_code in {403, 429}:
            raise GitHubApiError("GitHub API rate limit prevents reliable verification")
        return response

    def get_commit_status(self, sha: str) -> dict[str, Any]:
        path = f"/repos/{self.owner}/{self.repo}/commits/{quote(sha)}/status"
        response = self._request("GET", path)
        if response.status_code == 404:
            raise GitHubApiError(f"Commit SHA not found on GitHub: {sha}")
        if response.status_code == 403:
            raise AuthenticationError("Insufficient permissions to read commit status")
        if response.status_code >= 400:
            raise GitHubApiError(
                f"Ambiguous GitHub status read HTTP {response.status_code}: "
                f"{response.body}"
            )
        if not isinstance(response.body, dict):
            raise GitHubApiError("Ambiguous GitHub status payload")
        return response.body

    def assert_commit_exists(self, sha: str) -> None:
        path = f"/repos/{self.owner}/{self.repo}/commits/{quote(sha)}"
        response = self._request("GET", path)
        if response.status_code == 404:
            raise GitHubApiError(f"Commit SHA not found on GitHub: {sha}")
        if response.status_code == 403:
            raise AuthenticationError("Insufficient permissions to verify commit")
        if response.status_code == 401:
            raise AuthenticationError("GitHub authentication failed")
        if response.status_code >= 400:
            raise GitHubApiError(
                f"Ambiguous commit verification HTTP {response.status_code}"
            )

    def get_pull_request_head_sha(self, pr_number: int) -> str:
        path = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        response = self._request("GET", path)
        if response.status_code == 404:
            raise GitHubApiError(f"Pull request #{pr_number} not found")
        if response.status_code in {401, 403}:
            raise AuthenticationError("Insufficient permissions to read pull request")
        if response.status_code >= 400 or not isinstance(response.body, dict):
            raise GitHubApiError(
                f"Ambiguous PR read HTTP {response.status_code}: {response.body}"
            )
        head = response.body.get("head") or {}
        sha = head.get("sha")
        if not sha:
            raise GitHubApiError("PR head SHA missing from GitHub response")
        return str(sha)

    def create_commit_status(
        self, payload: StatusPayload, *, dry_run: bool = False
    ) -> dict[str, Any]:
        """Create a commit status for the exact SHA. Never writes in dry-run."""
        body = payload.to_api_body()
        record = {"sha": payload.sha, "body": body, "dry_run": dry_run}
        self.write_calls.append(record)
        if dry_run:
            return {"dry_run": True, "sha": payload.sha, "body": body}
        if payload.state == "success" and not payload.sha:
            raise GitHubApiError("Refusing success status without commit SHA")
        path = f"/repos/{self.owner}/{self.repo}/statuses/{quote(payload.sha)}"
        response = self._request("POST", path, body=body)
        if response.status_code in {401, 403}:
            raise AuthenticationError(
                "Insufficient token permissions to create commit status "
                "(need Commit statuses: Write or classic repo scope)"
            )
        if response.status_code >= 400:
            raise GitHubApiError(
                f"Commit status create failed HTTP {response.status_code}: "
                f"{response.body}"
            )
        if not isinstance(response.body, dict):
            raise GitHubApiError("Ambiguous commit status create response")
        # Ensure we never report success when API returned failure body.
        if body.get("state") == "success" and response.status_code not in {200, 201}:
            raise GitHubApiError("Success status was not accepted by GitHub")
        return response.body
