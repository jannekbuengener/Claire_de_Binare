"""Tests for the Data Flow & Observability Engineer Agent."""

from cdb_agent_sdk.agents.dataflow_observer import (
    DATAFLOW_OBSERVER_PROMPT,
    DATAFLOW_OBSERVER_TOOLS,
    create_dataflow_observer_options,
)
from cdb_agent_sdk.config import Config, get_config


class TestSystemPrompt:
    """Tests für den System Prompt."""

    def test_system_prompt_contains_role_definition(self):
        """System Prompt enthält Rollendefinition."""
        assert "Data Flow & Observability Engineer" in DATAFLOW_OBSERVER_PROMPT

    def test_system_prompt_contains_data_ontology(self):
        """System Prompt enthält Datenontologie."""
        assert "Event" in DATAFLOW_OBSERVER_PROMPT
        assert "State" in DATAFLOW_OBSERVER_PROMPT
        assert "Metric" in DATAFLOW_OBSERVER_PROMPT
        assert "Log" in DATAFLOW_OBSERVER_PROMPT

    def test_system_prompt_contains_governance_boundaries(self):
        """System Prompt enthält Governance-Grenzen."""
        assert "Grafana zeigt" in DATAFLOW_OBSERVER_PROMPT
        assert "entscheidet nicht" in DATAFLOW_OBSERVER_PROMPT
        assert "Redis transportiert" in DATAFLOW_OBSERVER_PROMPT
        assert "bewertet nicht" in DATAFLOW_OBSERVER_PROMPT

    def test_system_prompt_contains_data_sources(self):
        """System Prompt enthält verfügbare Datenquellen."""
        assert "stream.signals" in DATAFLOW_OBSERVER_PROMPT
        assert "market_data" in DATAFLOW_OBSERVER_PROMPT
        assert "Prometheus" in DATAFLOW_OBSERVER_PROMPT
        assert "PostgreSQL" in DATAFLOW_OBSERVER_PROMPT


class TestDefaultTools:
    """Tests für die Default Tools."""

    def test_default_tools_are_read_only_focused(self):
        """Default Tools sind primär read-only."""
        read_tools = ["Read", "Glob", "Grep"]
        for tool in read_tools:
            assert tool in DATAFLOW_OBSERVER_TOOLS

    def test_bash_is_available(self):
        """Bash ist verfügbar für Commands."""
        assert "Bash" in DATAFLOW_OBSERVER_TOOLS


class TestCreateAgentOptions:
    """Tests für create_dataflow_observer_options."""

    def test_creates_options_with_defaults(self):
        """Erstellt Options mit Default-Werten."""
        options = create_dataflow_observer_options()

        assert options.system_prompt is not None
        assert options.allowed_tools == DATAFLOW_OBSERVER_TOOLS
        assert options.permission_mode == "bypassPermissions"

    def test_allows_custom_cwd(self):
        """Erlaubt benutzerdefiniertes Working Directory."""
        cwd = "/custom/path"
        options = create_dataflow_observer_options(cwd=cwd)

        assert options.cwd == cwd


class TestConfig:
    """Tests für die Konfiguration."""

    def test_config_has_required_fields(self):
        """Config hat alle erforderlichen Felder."""
        config = get_config()

        assert hasattr(config, "cdb_root")
        assert hasattr(config, "grafana_url")
        assert hasattr(config, "redis_host")
        assert hasattr(config, "redis_port")
        assert hasattr(config, "postgres_host")

    def test_redis_url_construction(self):
        """Redis URL wird korrekt konstruiert."""
        config = Config(
            cdb_root="/tmp",
            grafana_url="http://localhost:3000",
            grafana_api_key=None,
            redis_host="localhost",
            redis_port=6379,
            redis_password=None,
            postgres_host="localhost",
            postgres_port=5432,
            postgres_db="cdb",
            postgres_user="cdb",
            postgres_password=None,
            use_mcp_docker=True,
        )

        assert config.redis_url == "redis://localhost:6379/0"

    def test_redis_url_with_password(self):
        """Redis URL mit Passwort."""
        config = Config(
            cdb_root="/tmp",
            grafana_url="http://localhost:3000",
            grafana_api_key=None,
            redis_host="localhost",
            redis_port=6379,
            redis_password="secret",
            postgres_host="localhost",
            postgres_port=5432,
            postgres_db="cdb",
            postgres_user="cdb",
            postgres_password=None,
            use_mcp_docker=True,
        )

        assert config.redis_url == "redis://:secret@localhost:6379/0"
