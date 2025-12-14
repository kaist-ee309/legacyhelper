"""Unit tests for bash_tool module."""
import pytest
from unittest.mock import patch, MagicMock
from legacyhelper.tools.command_tool import (
    BashResult,
    MAX_OUTPUT_CHARS,
)


@pytest.fixture
def bash_tool_func():
    """Get the actual bash_tool function for testing."""
    from legacyhelper.tools.command_tool import bash_tool as tool_wrapped

    # The bash_tool is wrapped in pydantic_ai Tool, extract the original function
    # The original function is stored in the function attribute
    return tool_wrapped.function


class TestBashTool:
    """Test cases for bash_tool function."""

    def test_bash_tool_blocks_rm_rf(self, bash_tool_func):
        """Test that rm -rf commands are properly blocked."""
        result = bash_tool_func("rm -rf /home")
        assert result.stderr == "Blocked dangerous command"
        assert result.returncode == 1
        assert result.stdout == ""

    def test_bash_tool_blocks_shutdown(self, bash_tool_func):
        """Test that shutdown commands are properly blocked."""
        result = bash_tool_func("shutdown -h now")
        assert result.stderr == "Blocked dangerous command"
        assert result.returncode == 1

    def test_bash_tool_blocks_reboot(self, bash_tool_func):
        """Test that reboot commands are properly blocked."""
        result = bash_tool_func("reboot")
        assert result.stderr == "Blocked dangerous command"
        assert result.returncode == 1

    def test_bash_tool_blocks_fork_bomb(self, bash_tool_func):
        """Test that fork bomb command is blocked."""
        result = bash_tool_func(":(){:|:&};:")
        assert result.stderr == "Blocked dangerous command"
        assert result.returncode == 1

    def test_bash_tool_blocks_sudo_commands(self, bash_tool_func):
        """Test that commands starting with sudo are blocked."""
        result = bash_tool_func("sudo ls /root")
        assert result.stderr == "The command requires superuser privalige. Abort."
        assert result.returncode == 1
        assert result.stdout == ""

    def test_bash_tool_executes_safe_commands(self, bash_tool_func):
        """Test that safe commands are executed."""
        with patch('legacyhelper.tools.command_tool.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ('ls output', '')
            mock_process.returncode = 0
            mock_popen.return_value.__enter__.return_value = mock_process

            result = bash_tool_func("ls -la")

            assert result.returncode == 0
            assert result.stdout == "ls output"
            assert result.stderr == ""
            mock_popen.assert_called_once()

    def test_bash_tool_captures_command_errors(self, bash_tool_func):
        """Test that command stderr is captured correctly."""
        with patch('legacyhelper.tools.command_tool.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ('', 'command not found')
            mock_process.returncode = 127
            mock_popen.return_value.__enter__.return_value = mock_process

            result = bash_tool_func("nonexistent_command")

            assert result.returncode == 127
            assert result.stderr == "command not found"
            assert result.stdout == ""

    def test_bash_result_model_creation(self):
        """Test BashResult model creation."""
        result = BashResult(stdout="test output", stderr="", returncode=0)

        assert result.stdout == "test output"
        assert result.stderr == ""
        assert result.returncode == 0

    def test_bash_result_with_various_return_codes(self):
        """Test BashResult with various return codes."""
        test_cases = [
            (0, "success"),
            (1, "general error"),
            (127, "command not found"),
            (255, "fatal error"),
        ]

        for code, message in test_cases:
            result = BashResult(stdout="", stderr=message, returncode=code)
            assert result.returncode == code
            assert result.stderr == message

    def test_bash_result_output_limit_on_stdout(self):
        """Test that stdout exceeding limit is truncated."""
        long_output = "x" * (MAX_OUTPUT_CHARS + 1000)

        result = BashResult(stdout=long_output, stderr="", returncode=0)

        assert "Context too long" in result.stdout
        assert len(result.stdout) < MAX_OUTPUT_CHARS
        assert "⚠️" in result.stdout

    def test_bash_result_output_limit_on_stderr(self):
        """Test that stderr exceeding limit is truncated."""
        long_error = "error: " * (MAX_OUTPUT_CHARS // 7 + 100)

        result = BashResult(stdout="", stderr=long_error, returncode=1)

        assert "Context too long" in result.stderr
        assert len(result.stderr) < MAX_OUTPUT_CHARS
        assert "⚠️" in result.stderr

    def test_bash_result_output_within_limit(self):
        """Test that output within limit is preserved."""
        output = "x" * 1000

        result = BashResult(stdout=output, stderr="", returncode=0)

        assert result.stdout == output
        assert "Context too long" not in result.stdout

    def test_bash_tool_with_pipe_and_redirection(self, bash_tool_func):
        """Test that commands with pipes and redirections are allowed."""
        with patch('legacyhelper.tools.command_tool.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ('filtered output', '')
            mock_process.returncode = 0
            mock_popen.return_value.__enter__.return_value = mock_process

            result = bash_tool_func("cat /var/log/syslog | grep error")

            assert result.returncode == 0
            assert result.stdout == "filtered output"

    def test_bash_tool_multiple_dangerous_command_checks(self, bash_tool_func):
        """Test all dangerous command patterns are blocked."""
        dangerous_patterns = ["rm -rf", "shutdown", "reboot", ":(){:|:&};:"]

        for pattern in dangerous_patterns:
            result = bash_tool_func(pattern)
            assert result.returncode == 1
            assert result.stderr == "Blocked dangerous command"

    def test_bash_result_both_stdout_and_stderr_large(self):
        """Test output limiting when both stdout and stderr are large."""
        long_output = "o" * (MAX_OUTPUT_CHARS + 1000)
        long_error = "e" * (MAX_OUTPUT_CHARS + 1000)

        result = BashResult(stdout=long_output, stderr=long_error, returncode=1)

        assert "Context too long" in result.stdout
        assert "Context too long" in result.stderr
        assert len(result.stdout) < MAX_OUTPUT_CHARS
        assert len(result.stderr) < MAX_OUTPUT_CHARS
