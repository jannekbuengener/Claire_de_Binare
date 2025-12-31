"""
Unit tests for infrastructure.scripts.smart_startup module.
Tests list-based subprocess execution without shell=True.

Security context:
    These tests verify that run_command uses list-based subprocess execution
    (shell=False) to prevent command injection vulnerabilities as documented
    in OWASP_TOP10_AUDIT.md (Finding #1).
"""

import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

from infrastructure.scripts.smart_startup import run_command


class TestRunCommand:
    """Tests for run_command() function"""

    def test_command_executes_as_list(self):
        """Test that commands are executed as a list, not a string"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            cmd = ["docker", "compose", "up", "-d"]
            run_command(cmd, "Test command")

            # Verify subprocess.run was called with the list directly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == cmd, "Command should be passed as a list"

    def test_shell_false_is_default(self):
        """Test that shell=False is used (default behavior)"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            run_command(["echo", "test"], "Test command")

            # Verify shell is not set to True in the call
            call_kwargs = mock_run.call_args.kwargs
            assert "shell" not in call_kwargs or call_kwargs.get("shell") is False, (
                "shell=True must not be used for security reasons"
            )

    def test_returns_true_on_success(self):
        """Test that run_command returns True when command succeeds"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = run_command(["echo", "test"], "Test command")

            assert result is True

    def test_returns_false_on_failure(self):
        """Test that run_command returns False when command fails"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Command failed"
            mock_run.return_value = mock_result

            result = run_command(["invalid", "command"], "Test command")

            assert result is False

    def test_returns_false_on_timeout(self):
        """Test that run_command returns False when command times out"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=30)

            result = run_command(["long", "running", "command"], "Test command")

            assert result is False

    def test_returns_false_on_exception(self):
        """Test that run_command returns False when an exception occurs"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Something went wrong")

            result = run_command(["bad", "command"], "Test command")

            assert result is False

    def test_captures_output(self):
        """Test that command output is captured"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            run_command(["echo", "test"], "Test command")

            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("capture_output") is True

    def test_uses_text_mode(self):
        """Test that command uses text mode for output"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            run_command(["echo", "test"], "Test command")

            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("text") is True

    def test_has_timeout(self):
        """Test that command has a timeout set"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            run_command(["echo", "test"], "Test command")

            call_kwargs = mock_run.call_args.kwargs
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"] > 0


class TestSecurityRequirements:
    """Tests specifically validating OWASP security requirements"""

    def test_shell_true_not_used_prevents_injection(self):
        """
        Verify that shell=True is not used to prevent command injection.

        OWASP Finding #1: Using subprocess.run with shell=True enables
        potential command injection if command construction ever changes.
        The implementation must use list-based commands with shell=False.
        """
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Test with a typical command
            run_command(["docker", "compose", "up", "-d"], "Start Docker")

            # Verify subprocess.run was called
            mock_run.assert_called_once()

            # Verify shell is not True
            call_args = mock_run.call_args
            call_kwargs = call_args.kwargs if call_args.kwargs else {}

            # shell should either not be present (defaults to False) or explicitly False
            shell_value = call_kwargs.get("shell", False)
            assert shell_value is False, (
                "shell=True must not be used - this is a command injection vulnerability"
            )

    def test_command_passed_as_list_not_string(self):
        """
        Verify that commands are passed as lists, not strings.

        When shell=False (the secure default), commands must be passed as a
        list of arguments. Passing a string with shell=False would cause issues.
        """
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            cmd = ["docker", "compose", "up", "-d"]
            run_command(cmd, "Start Docker")

            # Get the first positional argument (the command)
            call_args = mock_run.call_args
            passed_cmd = call_args[0][0]

            assert isinstance(passed_cmd, list), (
                "Command must be passed as a list for shell=False execution"
            )

    def test_command_elements_are_strings(self):
        """
        Verify that command list elements are strings.

        Each element in the command list should be a string representing
        a single argument. This prevents argument injection attacks.
        """
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            cmd = ["docker", "compose", "up", "-d"]
            run_command(cmd, "Start Docker")

            # Get the first positional argument (the command)
            call_args = mock_run.call_args
            passed_cmd = call_args[0][0]

            for element in passed_cmd:
                assert isinstance(element, str), (
                    "Each command element must be a string"
                )


class TestDockerComposeIntegration:
    """Tests for docker compose command execution"""

    def test_docker_compose_command_format(self):
        """Test that docker compose commands use the correct format"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # This is the expected command format from smart_startup
            cmd = ["docker", "compose", "up", "-d"]
            run_command(cmd, "Start Docker infrastructure")

            # Verify the command was passed correctly
            call_args = mock_run.call_args
            passed_cmd = call_args[0][0]

            assert passed_cmd == ["docker", "compose", "up", "-d"]

    def test_docker_compose_v2_syntax(self):
        """Test that Docker Compose v2 syntax is used (docker compose, not docker-compose)"""
        with patch("infrastructure.scripts.smart_startup.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            cmd = ["docker", "compose", "up", "-d"]
            run_command(cmd, "Start Docker infrastructure")

            # Verify the command was passed correctly
            call_args = mock_run.call_args
            passed_cmd = call_args[0][0]

            # Should use 'docker' and 'compose' as separate arguments (v2 syntax)
            assert passed_cmd[0] == "docker"
            assert passed_cmd[1] == "compose"
            # Should NOT be a single 'docker-compose' string (v1 syntax)
            assert "docker-compose" not in passed_cmd
