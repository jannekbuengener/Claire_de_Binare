"""Unit tests for Context Query search commands (#2082)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from argparse import Namespace

import pytest

from tools.surrealdb.context_query import (
    EXIT_OK,
    ContextQueryConfig,
    QueryAdapter,
    build_artifact_query,
    build_doc_query,
    handle_find_artifact,
    handle_find_doc,
    load_config,
)

EXAMPLE_CONFIG = "infrastructure/config/surrealdb/context_query.local.example.yaml"

# Minimal mock fixtures
MOCK_ARTIFACTS = [
    {
        "artifact_id": "artifact-1",
        "source_path": "docs/example.md",
        "file_type": "markdown",
        "normalized_sha256": "abc123",
    },
    {
        "artifact_id": "artifact-2",
        "source_path": "src/main.py",
        "file_type": "python",
        "normalized_sha256": "def456",
    },
]

MOCK_CHUNKS = [
    {
        "chunk_id": "chunk-1",
        "content": "example content for search",
        "source_path": "docs/example.md",
        "heading_path": ["Example"],
    },
    {
        "chunk_id": "chunk-2",
        "content": "another searchable text",
        "source_path": "docs/other.md",
        "heading_path": ["Other"],
    },
]


class MockQueryAdapter(QueryAdapter):
    """Mock adapter that returns in-memory fixture data."""

    def __init__(
        self,
        config: ContextQueryConfig | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        chunks: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(config)
        self.status = "mock-in-memory"
        self.artifacts = artifacts or []
        self.chunks = chunks or []

    def execute(self, query: str) -> list[dict[str, Any]]:
        """Return mock data based on query string (simple parser)."""
        if "FROM repo_artifact" in query:
            return list(self.artifacts)
        if "FROM doc_chunk" in query:
            return list(self.chunks)
        return []


@pytest.fixture()
def config() -> ContextQueryConfig:
    """Load example config for tests."""
    return load_config(Path(EXAMPLE_CONFIG))


@pytest.fixture()
def adapter(config: ContextQueryConfig) -> MockQueryAdapter:
    """Create a mock adapter with fixture data."""
    return MockQueryAdapter(config=config, artifacts=MOCK_ARTIFACTS, chunks=MOCK_CHUNKS)


# Tests for build_artifact_query
class TestBuildArtifactQuery:
    """Tests for build_artifact_query()."""

    @pytest.mark.unit
    def test_no_filters(self) -> None:
        query = build_artifact_query()
        assert query == "SELECT * FROM repo_artifact WHERE tombstoned = false"

    @pytest.mark.unit
    def test_source_path_filter(self) -> None:
        query = build_artifact_query(source_path="docs/")
        assert "source_path CONTAINS 'docs/'" in query
        assert "tombstoned = false" in query

    @pytest.mark.unit
    def test_file_type_filter(self) -> None:
        query = build_artifact_query(file_type="markdown")
        assert "file_type = 'markdown'" in query

    @pytest.mark.unit
    def test_hash_filter(self) -> None:
        query = build_artifact_query(hash_value="abc123")
        assert "normalized_sha256 = 'abc123'" in query

    @pytest.mark.unit
    def test_include_tombstoned(self) -> None:
        query = build_artifact_query(include_tombstoned=True)
        assert "tombstoned = false" not in query

    @pytest.mark.unit
    def test_with_limit(self) -> None:
        query = build_artifact_query(limit=50)
        assert "LIMIT 50" in query


# Tests for build_doc_query
class TestBuildDocQuery:
    """Tests for build_doc_query()."""

    @pytest.mark.unit
    def test_no_filters(self) -> None:
        query = build_doc_query()
        assert query == "SELECT * FROM doc_chunk WHERE tombstoned = false"

    @pytest.mark.unit
    def test_query_text_filter(self) -> None:
        query = build_doc_query(query_text="search")
        assert "content CONTAINS 'search'" in query

    @pytest.mark.unit
    def test_source_path_filter(self) -> None:
        query = build_doc_query(source_path="docs/")
        assert "source_path CONTAINS 'docs/'" in query

    @pytest.mark.unit
    def test_heading_filter(self) -> None:
        query = build_doc_query(heading="Example")
        assert "heading_path CONTAINS 'Example'" in query

    @pytest.mark.unit
    def test_include_tombstoned(self) -> None:
        query = build_doc_query(include_tombstoned=True)
        assert "tombstoned = false" not in query


# Tests for handle_find_artifact
class TestHandleFindArtifact:
    """Tests for handle_find_artifact()."""

    @pytest.mark.unit
    def test_basic_search(
        self, config: ContextQueryConfig, adapter: MockQueryAdapter
    ) -> None:
        args = Namespace(
            config=Path(EXAMPLE_CONFIG),
            source_path=None,
            file_type=None,
            hash=None,
            limit=config.max_limit_default,
            include_tombstoned=False,
        )
        payload, exit_code = handle_find_artifact(args, config, adapter)
        assert exit_code == EXIT_OK
        assert payload["status"] == "ok"
        assert payload["command"] == "find-artifact"
        assert payload["count"] == 2
        assert len(payload["results"]) == 2

    @pytest.mark.unit
    def test_with_source_path(
        self, config: ContextQueryConfig, adapter: MockQueryAdapter
    ) -> None:
        args = Namespace(
            config=Path(EXAMPLE_CONFIG),
            source_path="docs/",
            file_type=None,
            hash=None,
            limit=config.max_limit_default,
            include_tombstoned=False,
        )
        payload, exit_code = handle_find_artifact(args, config, adapter)
        assert exit_code == EXIT_OK
        assert payload["count"] == 2


# Tests for handle_find_doc
class TestHandleFindDoc:
    """Tests for handle_find_doc()."""

    @pytest.mark.unit
    def test_basic_search(
        self, config: ContextQueryConfig, adapter: MockQueryAdapter
    ) -> None:
        args = Namespace(
            config=Path(EXAMPLE_CONFIG),
            query=None,
            source_path=None,
            heading=None,
            limit=config.max_limit_default,
            include_tombstoned=False,
        )
        payload, exit_code = handle_find_doc(args, config, adapter)
        assert exit_code == EXIT_OK
        assert payload["status"] == "ok"
        assert payload["command"] == "find-doc"
        assert payload["count"] == 2


# Tests for CLI integration
class TestCLIIntegration:
    """Integration tests via main()."""

    @pytest.mark.unit
    def test_find_artifact_help(self, capsys) -> None:
        from tools.surrealdb.context_query import main

        with pytest.raises(SystemExit) as exc_info:
            main(["find-artifact", "--help"])
        assert exc_info.value.code == 0
        assert "find-artifact" in capsys.readouterr().out

    @pytest.mark.unit
    def test_find_doc_help(self, capsys) -> None:
        from tools.surrealdb.context_query import main

        with pytest.raises(SystemExit) as exc_info:
            main(["find-doc", "--help"])
        assert exc_info.value.code == 0
        assert "find-doc" in capsys.readouterr().out

    @pytest.mark.unit
    def test_find_artifact_json_output(self, capsys) -> None:
        from tools.surrealdb.context_query import main

        exit_code = main(
            [
                "--config",
                EXAMPLE_CONFIG,
                "--format",
                "json",
                "find-artifact",
                "--source-path",
                "docs/",
            ]
        )
        assert exit_code == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "ok"
        assert payload["command"] == "find-artifact"

    @pytest.mark.unit
    def test_find_doc_text_output(self, capsys) -> None:
        from tools.surrealdb.context_query import main

        exit_code = main(
            [
                "--config",
                EXAMPLE_CONFIG,
                "--format",
                "text",
                "find-doc",
                "--query",
                "search",
            ]
        )
        assert exit_code == EXIT_OK
        output = capsys.readouterr().out
        assert "status: ok" in output
