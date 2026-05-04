"""
Unit tests for error cases in Context MCP Bridge.

Tests execution errors, adapter failures, empty result handling,
and handler-level exception propagation.
#2100
"""

import pytest
from unittest.mock import patch, MagicMock
from tools.mcp.context_bridge import create_bridge


class TestSearchExecutionError:
    """Tests for search adapter execution errors."""

    def test_adapter_exception_returns_execution_error(self) -> None:
        bridge = create_bridge()
        with patch(
            "tools.surrealdb.context_query.NoopQueryAdapter"
        ) as MockAdapter:
            mock_instance = MagicMock()
            mock_instance.execute.side_effect = RuntimeError("DB connection lost")
            MockAdapter.return_value = mock_instance
            result = bridge.execute_tool(
                "context.search", {"query": "risk decisions"}
            )
            assert result["status"] == "error"
            assert result["error"]["code"] == "execution_error"

    def test_adapter_exception_includes_message(self) -> None:
        bridge = create_bridge()
        with patch(
            "tools.surrealdb.context_query.NoopQueryAdapter"
        ) as MockAdapter:
            mock_instance = MagicMock()
            mock_instance.execute.side_effect = RuntimeError("timeout exceeded")
            MockAdapter.return_value = mock_instance
            result = bridge.execute_tool(
                "context.search", {"query": "risk decisions"}
            )
            assert "timeout exceeded" in result["error"]["message"]

    def test_search_empty_results_has_zero_hits(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "test"})
        assert result["metadata"]["total_hits"] == 0
        assert result["results"] == []


class TestBridgeHandlerErrorPropagation:
    """Tests for handler-level exception handling."""

    def test_search_handler_type_error_caught(self) -> None:
        bridge = create_bridge()
        with patch(
            "tools.surrealdb.context_query.NoopQueryAdapter"
        ) as MockAdapter:
            mock_instance = MagicMock()
            mock_instance.execute.side_effect = TypeError("bad type")
            MockAdapter.return_value = mock_instance
            result = bridge.execute_tool(
                "context.search", {"query": "test"}
            )
            assert result["status"] == "error"
            assert result["error"]["code"] == "execution_error"

    def test_search_handler_value_error_caught(self) -> None:
        bridge = create_bridge()
        with patch(
            "tools.surrealdb.context_query.NoopQueryAdapter"
        ) as MockAdapter:
            mock_instance = MagicMock()
            mock_instance.execute.side_effect = ValueError("bad value")
            MockAdapter.return_value = mock_instance
            result = bridge.execute_tool(
                "context.search", {"query": "test"}
            )
            assert result["status"] == "error"
            assert result["error"]["code"] == "execution_error"


class TestHandlerEdgeCases:
    """Edge case tests across handlers."""

    def test_package_handler_with_integer_artifacts_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": 123}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_artifacts"

    def test_trace_depth_zero_resets_to_default(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace",
            {"target_id": "evt_001", "depth": 0},
        )
        assert result["status"] == "ok"

    def test_trace_depth_negative_resets_to_default(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace",
            {"target_id": "evt_001", "depth": -1},
        )
        assert result["status"] == "ok"

    def test_explain_source_whitespace_ref_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "   "}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_source_ref"

    def test_search_whitespace_query_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "  "})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_query"

    def test_search_non_string_query_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": 42})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_query"