"""
Unit tests for context.package handler.

Tests the package handler input validation, output structure,
truncation, format handling, and contract compliance.
#2100
"""

from tools.mcp.context_bridge import create_bridge


class TestContextPackageHandler:
    """Tests for context.package tool handler."""

    def test_missing_artifacts_returns_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_artifacts"

    def test_none_artifacts_returns_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {"artifacts": None})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_artifacts"

    def test_string_artifacts_returns_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {"artifacts": "not_a_list"})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_artifacts"

    def test_empty_artifacts_list_returns_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {"artifacts": []})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_artifacts"

    def test_valid_artifacts_returns_ok(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001", "art_002"]}
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.package"
        assert "package" in result

    def test_package_items_capped_at_ten(self) -> None:
        bridge = create_bridge()
        many = [f"art_{i:03d}" for i in range(15)]
        result = bridge.execute_tool("context.package", {"artifacts": many})
        assert result["status"] == "ok"
        assert len(result["package"]["items"]) <= 10

    def test_truncation_warning_when_over_limit(self) -> None:
        bridge = create_bridge()
        many = [f"art_{i:03d}" for i in range(15)]
        result = bridge.execute_tool("context.package", {"artifacts": many})
        assert "artifacts_limit_exceeded_truncated" in result["package"]["warnings"]

    def test_no_truncation_warning_within_limit(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001", "art_002"]}
        )
        assert "artifacts_limit_exceeded_truncated" not in result["package"]["warnings"]

    def test_format_json_default(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        assert result["package"]["format"] == "json"

    def test_format_markdown_accepted(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"], "format": "markdown"}
        )
        assert result["status"] == "ok"
        assert result["package"]["format"] == "markdown"

    def test_invalid_format_returns_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"], "format": "xml"}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "format_unsupported"

    def test_include_metadata_default_true(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        assert result["package"]["metadata"]["include_metadata"] is True

    def test_include_metadata_false_omits_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package",
            {"artifacts": ["art_001"], "include_metadata": False},
        )
        assert result["package"]["metadata"] == {}

    def test_include_metadata_non_bool_defaults_true(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package",
            {"artifacts": ["art_001"], "include_metadata": "yes"},
        )
        assert result["package"]["metadata"]["include_metadata"] is True

    def test_package_id_is_deterministic(self) -> None:
        bridge = create_bridge()
        result1 = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001", "art_002"]}
        )
        result2 = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001", "art_002"]}
        )
        assert result1["package"]["package_id"] == result2["package"]["package_id"]

    def test_package_contains_stop_conditions(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        assert "stop_conditions" in result["package"]
        assert isinstance(result["package"]["stop_conditions"], list)

    def test_package_item_has_required_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        item = result["package"]["items"][0]
        for field in ("id", "type", "summary", "source_refs", "confidence", "freshness"):
            assert field in item, f"Package item missing field: {field}"

    def test_package_contains_created_at(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        assert "created_at" in result["package"]

    def test_missing_context_present_in_ok_result(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        assert "missing_context" in result["package"]
        assert isinstance(result["package"]["missing_context"], list)

    def test_single_artifact_no_truncation_no_empty_warning(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["art_001"]}
        )
        assert "artifacts_limit_exceeded_truncated" not in result["package"]["warnings"]
        assert "empty_package" not in result["package"]["warnings"]

    def test_error_response_has_required_structure(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {})
        assert result["status"] == "error"
        assert "tool" in result
        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]