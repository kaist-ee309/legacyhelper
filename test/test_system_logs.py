"""Unit tests for system log tools."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from legacyhelper.tools.command_tool import (
    get_current_system_log_linux,
    get_previous_system_log_linux,
    get_filtered_shell_history,
)


class TestSystemLogs:
    """Test cases for system log retrieval functions."""

    def test_get_current_system_log_success(self):
        """Test retrieving current system log successfully."""
        expected_output = "kernel: error occurred\nkernel: system error\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=expected_output)

            result = get_current_system_log_linux()

            assert result == expected_output
            mock_run.assert_called_once_with(
                ["journalctl", "-p", "3", "-xb", "--no-pager"],
                capture_output=True,
                text=True,
                check=True
            )

    def test_get_current_system_log_exception(self):
        """Test handling of exception when retrieving current system log."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("journalctl not found")

            result = get_current_system_log_linux()

            assert "journalctl not found" in result

    def test_get_previous_system_log_success(self):
        """Test retrieving previous system log successfully."""
        expected_output = "kernel: previous boot error\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=expected_output)

            result = get_previous_system_log_linux()

            assert result == expected_output
            mock_run.assert_called_once_with(
                ["journalctl", "-p", "3", "-xb", "-1", "--no-pager"],
                capture_output=True,
                text=True,
                check=True
            )

    def test_get_previous_system_log_exception(self):
        """Test handling of exception when retrieving previous system log."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("No previous boot log available")

            result = get_previous_system_log_linux()

            assert "No previous boot log available" in result


class TestShellHistory:
    """Test cases for shell history retrieval."""

    def test_get_filtered_shell_history_zsh(self, temp_home):
        """Test retrieving zsh shell history."""
        # Create a mock zsh history file
        history_file = temp_home / ".zsh_history"
        history_file.write_text(
            ": 1234567890:0;ls -la\n"
            ": 1234567891:0;cd /tmp\n"
            ": 1234567892:0;echo hello\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/zsh'}):
            result = get_filtered_shell_history(ctx=None, n=2)

            # Should get the last 2 commands (n=2 means 2 most recent)
            lines = result.strip().split('\n') if result.strip() else []
            assert len(lines) <= 2
            # Should contain some commands from the history
            assert len(result) > 0

    def test_get_filtered_shell_history_bash(self, temp_home):
        """Test retrieving bash shell history."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "ls -la\n"
            "cd /tmp\n"
            "echo hello\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=2)

            # Should get the last 2 commands
            lines = result.strip().split('\n')
            assert len(lines) <= 2

    def test_get_filtered_shell_history_redacts_api_key(self, temp_home):
        """Test that API keys are redacted from history."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "export API_KEY=mysecretapikey123456789012345\n"
            "curl https://api.example.com -H 'Authorization: Bearer sk1234567890abcdef1234567890abcdef'\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            # The long token (32+ chars) should be redacted
            assert "***REDACTED***" in result
            # Short secrets may not be redacted by default, but long tokens should be
            assert "sk1234567890abcdef1234567890abcdef" not in result

    def test_get_filtered_shell_history_redacts_password(self, temp_home):
        """Test that passwords are redacted from history."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "export PASSWORD=mysecretpassword123456789012345\n"
            "mysql -u user -p mysecretpasswordtoken123456789012345\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            # Long tokens (32+ chars) should be redacted
            assert "***REDACTED***" in result
            assert "mysecretpasswordtoken123456789012345" not in result

    def test_get_filtered_shell_history_redacts_tokens(self, temp_home):
        """Test that long tokens (32+ chars) are redacted."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "curl https://api.example.com?token=abcd1234efgh5678ijkl9012mnop3456\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            assert "***REDACTED***" in result
            assert "abcd1234efgh5678ijkl9012mnop3456" not in result

    def test_get_filtered_shell_history_no_history_file(self, temp_home):
        """Test handling when no history file exists."""
        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            # Should return empty string or error message
            assert result == ""

    def test_get_filtered_shell_history_preserves_paths(self, temp_home):
        """Test that file paths are not redacted."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "cd /var/www/abcd1234efgh5678ijkl9012mnop3456/files\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            # Path should be preserved
            assert "/var/www/abcd1234efgh5678ijkl9012mnop3456/files" in result

    def test_get_filtered_shell_history_redacts_url_credentials(self, temp_home):
        """Test that URL embedded credentials are redacted."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "curl http://user:password@example.com/api\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            assert "***REDACTED***@example.com" in result
            assert "user:password" not in result

    def test_get_filtered_shell_history_n_parameter(self, temp_home):
        """Test that n parameter limits output correctly."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "cmd1\n"
            "cmd2\n"
            "cmd3\n"
            "cmd4\n"
            "cmd5\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=2)

            lines = [l for l in result.strip().split('\n') if l]
            assert len(lines) <= 2

    def test_get_filtered_shell_history_empty_lines_filtered(self, temp_home):
        """Test that empty lines are filtered from output."""
        history_file = temp_home / ".bash_history"
        history_file.write_text(
            "cmd1\n"
            "\n"
            "\n"
            "cmd2\n"
        )

        with patch.dict('os.environ', {'SHELL': '/bin/bash'}):
            result = get_filtered_shell_history(ctx=None, n=10)

            lines = result.strip().split('\n')
            # Should not have consecutive empty lines
            assert all(line.strip() != "" for line in lines if lines)
