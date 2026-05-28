"""Unit tests for SurrealDBLocalQueryAdapter (#2459)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.surrealdb.context_query import (
    ConfigValidationError,
    InputNotFoundError,
    QueryAdapterError,
    SurrealDBLocalQueryAdapter,
    WriteDeniedError,
    _load_query_credentials,
    _NoRedirectHandler,
    build_artifact_query,
    build_doc_query,
    load_config,
)

EXAMPLE_CONFIG = Path(
    "infrastructure/config/surrealdb/context_query.local.example.yaml"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(
    url: str = "http://127.0.0.1:8010",
    user: str | None = None,
    password: str | None = None,
    hard_mode: bool = False,
) -> SurrealDBLocalQueryAdapter:
    return SurrealDBLocalQueryAdapter(
        surreal_url=url,
        namespace="cdb_context_local",
        database="cdb_context_intel",
        user=user,
        password=password,
        timeout=5,
        hard_mode=hard_mode,
    )


def _mock_response(rows: list[dict]) -> MagicMock:
    """Build a mock urllib response that returns a SurrealDB-style JSON array."""
    body = json.dumps([{"time": "0ns", "status": "OK", "result": rows}]).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _mock_opener(response: MagicMock) -> MagicMock:
    """Return a mock opener (as returned by build_opener) whose .open() returns response."""
    mock_opener = MagicMock()
    mock_opener.open.return_value = response
    return mock_opener


def _mock_opener_raising(exc: Exception) -> MagicMock:
    """Return a mock opener (as returned by build_opener) whose .open() raises exc."""
    mock_opener = MagicMock()
    mock_opener.open.side_effect = exc
    return mock_opener


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_http_localhost_ip_accepted() -> None:
    adapter = _make_adapter(url="http://127.0.0.1:8010")
    assert adapter.status == "surrealdb-local"


@pytest.mark.unit
def test_http_localhost_name_accepted() -> None:
    adapter = _make_adapter(url="http://localhost:8010")
    assert adapter.status == "surrealdb-local"


@pytest.mark.unit
def test_https_local_accepted() -> None:
    adapter = _make_adapter(url="https://127.0.0.1:8010")
    assert adapter.status == "surrealdb-local"


@pytest.mark.unit
def test_remote_url_rejected() -> None:
    with pytest.raises(ConfigValidationError) as excinfo:
        _make_adapter(url="http://remote.example.com:8010")
    assert "local host" in excinfo.value.message


@pytest.mark.unit
def test_ws_url_rejected() -> None:
    with pytest.raises(ConfigValidationError) as excinfo:
        _make_adapter(url="ws://127.0.0.1:8010")
    assert "http or https" in excinfo.value.message


@pytest.mark.unit
def test_wss_url_rejected() -> None:
    with pytest.raises(ConfigValidationError) as excinfo:
        _make_adapter(url="wss://127.0.0.1:8010")
    assert "http or https" in excinfo.value.message


# ---------------------------------------------------------------------------
# HTTP request structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_execute_select_posts_to_sql_endpoint() -> None:
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ) as mock_build:
        result = adapter.execute("SELECT * FROM repo_artifact")
    assert result == []
    req = mock_build.return_value.open.call_args[0][0]
    assert req.full_url == "http://127.0.0.1:8010/sql"
    assert req.get_method() == "POST"
    assert req.data == b"SELECT * FROM repo_artifact"


@pytest.mark.unit
def test_correct_headers_sent() -> None:
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ) as mock_build:
        adapter.execute("SELECT * FROM repo_artifact")
    req = mock_build.return_value.open.call_args[0][0]
    assert req.get_header("Accept") == "application/json"
    assert req.get_header("Content-type") == "text/plain"
    assert req.get_header("Surreal-ns") == "cdb_context_local"
    assert req.get_header("Surreal-db") == "cdb_context_intel"


@pytest.mark.unit
def test_auth_none_sends_no_authorization_header() -> None:
    adapter = _make_adapter(user=None, password=None)
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ) as mock_build:
        adapter.execute("SELECT * FROM doc_chunk")
    req = mock_build.return_value.open.call_args[0][0]
    assert req.get_header("Authorization") is None


@pytest.mark.unit
def test_auth_root_sends_basic_authorization() -> None:
    adapter = _make_adapter(user="admin", password="secret")
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ) as mock_build:
        adapter.execute("SELECT * FROM doc_chunk")
    req = mock_build.return_value.open.call_args[0][0]
    auth = req.get_header("Authorization")
    assert auth is not None
    assert auth.startswith("Basic ")
    # Must NOT contain raw secret
    assert "secret" not in auth


@pytest.mark.unit
def test_secret_not_in_error_message() -> None:
    """Raw credentials must not appear in QueryAdapterError messages."""
    import urllib.error

    adapter = _make_adapter(user="admin", password="local_test")
    http_error = urllib.error.HTTPError(
        url="http://127.0.0.1:8010/sql",
        code=500,
        msg="Internal Server Error",
        hdrs=MagicMock(),
        fp=None,
    )
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(http_error)
    ):
        with pytest.raises(QueryAdapterError) as excinfo:
            adapter.execute("SELECT * FROM repo_artifact")
    assert "local_test" not in excinfo.value.message


# ---------------------------------------------------------------------------
# Write-denial BEFORE HTTP
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "stmt",
    [
        "CREATE repo_artifact SET name = 'x'",
        "UPDATE repo_artifact SET name = 'x'",
        "UPSERT repo_artifact:id SET name = 'x'",
        "DELETE repo_artifact",
        "DEFINE TABLE foo SCHEMAFULL",
        "USE NS test DB test",
        "LIVE SELECT * FROM repo_artifact",
        "KILL 'query-id'",
    ],
)
def test_write_statements_denied_before_http(stmt: str) -> None:
    adapter = _make_adapter()
    with patch("urllib.request.build_opener") as mock_build:
        with pytest.raises(WriteDeniedError):
            adapter.execute(stmt)
    mock_build.assert_not_called()


@pytest.mark.unit
def test_multi_statement_denied_before_http() -> None:
    adapter = _make_adapter()
    with patch("urllib.request.build_opener") as mock_build:
        with pytest.raises(WriteDeniedError):
            adapter.execute("SELECT * FROM repo_artifact; SELECT * FROM doc_chunk")
    mock_build.assert_not_called()


# ---------------------------------------------------------------------------
# SurrealDB error responses
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_surrealdb_err_response_raises_query_adapter_error() -> None:
    err_body = json.dumps(
        [{"time": "0ns", "status": "ERR", "result": "There was a problem"}]
    ).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = err_body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    adapter = _make_adapter()
    with patch("urllib.request.build_opener", return_value=_mock_opener(mock_resp)):
        with pytest.raises(QueryAdapterError) as excinfo:
            adapter.execute("SELECT * FROM repo_artifact")
    assert "ERR" in excinfo.value.message


@pytest.mark.unit
def test_http_500_raises_query_adapter_error() -> None:
    import urllib.error

    http_error = urllib.error.HTTPError(
        url="http://127.0.0.1:8010/sql",
        code=500,
        msg="Internal Server Error",
        hdrs=MagicMock(),
        fp=None,
    )
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(http_error)
    ):
        with pytest.raises(QueryAdapterError) as excinfo:
            adapter.execute("SELECT * FROM repo_artifact")
    assert "500" in excinfo.value.message


# ---------------------------------------------------------------------------
# Unreachable DB — soft vs hard mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_urlError_soft_mode_returns_empty_and_sets_unavailable() -> None:
    import urllib.error

    adapter = _make_adapter(hard_mode=False)
    url_error = urllib.error.URLError(reason="Connection refused")
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(url_error)
    ):
        result = adapter.execute("SELECT * FROM repo_artifact")
    assert result == []
    assert adapter.status == "surrealdb-local-unavailable"


@pytest.mark.unit
def test_urlError_hard_mode_raises_query_adapter_error() -> None:
    import urllib.error

    adapter = _make_adapter(hard_mode=True)
    url_error = urllib.error.URLError(reason="Connection refused")
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(url_error)
    ):
        with pytest.raises(QueryAdapterError):
            adapter.execute("SELECT * FROM repo_artifact")
    assert adapter.status == "surrealdb-local-unavailable"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_empty_result_returns_empty_list() -> None:
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ):
        result = adapter.execute("SELECT * FROM repo_artifact")
    assert result == []


@pytest.mark.unit
def test_rows_returned_correctly() -> None:
    rows = [{"id": "repo_artifact:1", "source_path": "core/foo.py"}]
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response(rows))
    ):
        result = adapter.execute("SELECT * FROM repo_artifact")
    assert result == rows


@pytest.mark.unit
def test_adapter_status_connected_after_success() -> None:
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ):
        adapter.execute("SELECT * FROM repo_artifact")
    assert adapter.status == "surrealdb-local"


@pytest.mark.unit
def test_adapter_status_unavailable_after_urlError() -> None:
    import urllib.error

    adapter = _make_adapter(hard_mode=False)
    with patch(
        "urllib.request.build_opener",
        return_value=_mock_opener_raising(urllib.error.URLError("refused")),
    ):
        adapter.execute("SELECT * FROM repo_artifact")
    assert adapter.status == "surrealdb-local-unavailable"


# ---------------------------------------------------------------------------
# Schema-compatibility: no tombstone = false in default queries
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_artifact_query_default_no_tombstone_filter() -> None:
    query = build_artifact_query()
    assert "tombstoned" not in query


@pytest.mark.unit
def test_build_doc_query_default_no_tombstone_filter() -> None:
    query = build_doc_query()
    assert "tombstoned" not in query


@pytest.mark.unit
def test_build_artifact_query_with_filters_no_tombstone_filter() -> None:
    query = build_artifact_query(
        source_path="src/", file_type="python", include_tombstoned=False
    )
    assert "tombstoned" not in query


# ---------------------------------------------------------------------------
# _load_query_credentials
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_credentials_none_mode_returns_none_pair() -> None:
    config = load_config(EXAMPLE_CONFIG)
    # config has auth_mode = root from YAML; create a mock config-like object instead
    from dataclasses import replace

    config_none = replace(config, auth_mode="none")
    user, password = _load_query_credentials(config_none, secrets_path=None)
    assert user is None
    assert password is None


@pytest.mark.unit
def test_load_credentials_root_without_secrets_path_raises(tmp_path: Path) -> None:
    config = load_config(EXAMPLE_CONFIG)
    with pytest.raises(ConfigValidationError) as excinfo:
        _load_query_credentials(config, secrets_path=None)
    assert "secrets-path" in excinfo.value.message


@pytest.mark.unit
def test_load_credentials_root_missing_env_file_raises(tmp_path: Path) -> None:
    config = load_config(EXAMPLE_CONFIG)
    with pytest.raises(InputNotFoundError):
        _load_query_credentials(config, secrets_path=tmp_path)


@pytest.mark.unit
def test_load_credentials_root_valid_env_file(tmp_path: Path) -> None:
    config = load_config(EXAMPLE_CONFIG)
    env_file = tmp_path / "SURREALDB_ENV"
    env_file.write_text(
        "SURREAL_USER=testuser\nSURREAL_PASS=testpass\n", encoding="utf-8"
    )
    user, password = _load_query_credentials(config, secrets_path=tmp_path)
    assert user == "testuser"
    assert password == "testpass"


@pytest.mark.unit
def test_load_credentials_root_missing_pass_raises(tmp_path: Path) -> None:
    config = load_config(EXAMPLE_CONFIG)
    env_file = tmp_path / "SURREALDB_ENV"
    env_file.write_text("SURREAL_USER=testuser\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError) as excinfo:
        _load_query_credentials(config, secrets_path=tmp_path)
    assert "SURREAL_PASS" in excinfo.value.message


# ---------------------------------------------------------------------------
# Redirect blocking — credential-leak prevention (#2459 / PR #2465 Thread 5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_redirect_handler_redirect_request_raises() -> None:
    """_NoRedirectHandler.redirect_request must raise QueryAdapterError immediately."""
    handler = _NoRedirectHandler()
    with pytest.raises(QueryAdapterError) as excinfo:
        handler.redirect_request(
            req=MagicMock(),
            fp=MagicMock(),
            code=302,
            msg="Found",
            headers=MagicMock(),
            newurl="https://example.com/collect",
        )
    assert "redirect denied" in excinfo.value.message
    assert "302" in excinfo.value.message


@pytest.mark.unit
def test_no_redirect_handler_redirect_request_raises_for_301() -> None:
    """_NoRedirectHandler must block 301 Moved Permanently as well."""
    handler = _NoRedirectHandler()
    with pytest.raises(QueryAdapterError) as excinfo:
        handler.redirect_request(
            req=MagicMock(),
            fp=MagicMock(),
            code=301,
            msg="Moved Permanently",
            headers=MagicMock(),
            newurl="https://attacker.example.com/steal",
        )
    assert "redirect denied" in excinfo.value.message
    assert "301" in excinfo.value.message


@pytest.mark.unit
def test_redirect_response_is_denied_without_following() -> None:
    """HTTP redirect from local DB must raise QueryAdapterError, never be followed."""
    adapter = _make_adapter()
    redirect_error = QueryAdapterError(
        "redirect denied for local SurrealDB query request (HTTP 302)"
    )
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(redirect_error)
    ):
        with pytest.raises(QueryAdapterError) as excinfo:
            adapter.execute("SELECT * FROM repo_artifact")
    assert "redirect denied" in excinfo.value.message
    assert "302" in excinfo.value.message


@pytest.mark.unit
def test_redirect_does_not_leak_authorization_header() -> None:
    """Redirect must never forward Authorization header to a remote host.

    The opener.open() is called exactly once.  No retry, no follow.
    Error message must not contain raw credentials.
    """
    adapter = _make_adapter(user="root", password="s3cr3t_k3y")
    redirect_error = QueryAdapterError(
        "redirect denied for local SurrealDB query request (HTTP 301)"
    )
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(redirect_error)
    ) as mock_build:
        with pytest.raises(QueryAdapterError) as excinfo:
            adapter.execute("SELECT * FROM repo_artifact")
    # Must have attempted exactly one request, then stopped
    mock_build.return_value.open.assert_called_once()
    # Error message must not leak raw credentials
    assert "s3cr3t_k3y" not in excinfo.value.message
    assert "root" not in excinfo.value.message


@pytest.mark.unit
def test_no_redirect_handler_is_passed_to_build_opener() -> None:
    """build_opener must be called with a _NoRedirectHandler instance."""
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response([]))
    ) as mock_build:
        adapter.execute("SELECT * FROM repo_artifact")
    call_args = mock_build.call_args
    assert len(call_args[0]) == 1
    assert isinstance(call_args[0][0], _NoRedirectHandler)


@pytest.mark.unit
def test_success_still_posts_to_local_sql_endpoint() -> None:
    """Regression: successful SELECT still works correctly after redirect-block change."""
    rows = [{"id": "repo_artifact:1", "source_path": "core/foo.py"}]
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener(_mock_response(rows))
    ) as mock_build:
        result = adapter.execute("SELECT * FROM repo_artifact")
    assert result == rows
    req = mock_build.return_value.open.call_args[0][0]
    assert req.full_url == "http://127.0.0.1:8010/sql"
    assert req.get_method() == "POST"


@pytest.mark.unit
def test_http_500_still_raises_query_adapter_error() -> None:
    """Regression: HTTP 500 from local DB still raises QueryAdapterError."""
    import urllib.error

    http_error = urllib.error.HTTPError(
        url="http://127.0.0.1:8010/sql",
        code=500,
        msg="Internal Server Error",
        hdrs=MagicMock(),
        fp=None,
    )
    adapter = _make_adapter()
    with patch(
        "urllib.request.build_opener", return_value=_mock_opener_raising(http_error)
    ):
        with pytest.raises(QueryAdapterError) as excinfo:
            adapter.execute("SELECT * FROM repo_artifact")
    assert "500" in excinfo.value.message
