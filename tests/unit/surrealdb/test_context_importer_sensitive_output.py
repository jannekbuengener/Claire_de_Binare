"""context_importer must not emit raw secrets on stdout (#2918)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.surrealdb import context_importer as importer
from tools.surrealdb.sensitive_output import REDACT_PLACEHOLDER

pytestmark = pytest.mark.unit


def test_main_internal_error_redacts_sensitive_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = MagicMock()
    args.format = "json"

    with (
        patch.object(importer, "build_parser") as mock_build_parser,
        patch.object(
            importer,
            "_handle",
            side_effect=RuntimeError("SURREAL_PASS=leaked-pass-value"),
        ),
    ):
        mock_build_parser.return_value.parse_args.return_value = args
        exit_code = importer.main([])

    captured = capsys.readouterr()
    assert exit_code == importer.EXIT_INTERNAL
    assert "leaked-pass-value" not in captured.out
    payload = json.loads(captured.out.strip())
    assert payload["error"] == "INTERNAL"
    assert REDACT_PLACEHOLDER in payload["message"]
