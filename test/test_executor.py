"""Unit tests for command executor."""
import pytest
from legacyhelper.core.executor import CommandExecutor, InteractiveExecutor, ExecutionResult


class TestCommandExecutor:
    """Test cases for CommandExecutor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.executor = CommandExecutor(timeout=5)

    def test_execute_simple_command(self) -> None:
        """Test executing a simple command."""
        result = self.executor.execute("echo 'Hello, World!'")

        assert result.success
        assert result.exit_code == 0
        assert "Hello, World!" in result.stdout

    def test_execute_command_with_failure(self) -> None:
        """Test executing a command that fails."""
        result = self.executor.execute("ls /nonexistent_directory_12345")

        assert not result.success
        assert result.exit_code != 0
        assert len(result.stderr) > 0

    def test_command_timeout(self) -> None:
        """Test that long-running commands timeout."""
        # Use a very short timeout
        executor = CommandExecutor(timeout=1)
        result = executor.execute("sleep 10")

        assert not result.success
        assert "timed out" in result.error_message.lower()

    def test_dry_run_mode(self) -> None:
        """Test dry run mode doesn't execute commands."""
        executor = CommandExecutor(dry_run=True)
        result = executor.execute("rm -rf /")

        assert result.success  # Dry run always succeeds
        assert "DRY RUN" in result.stdout

    def test_can_execute_valid_command(self) -> None:
        """Test can_execute for valid commands."""
        can_exec, reason = self.executor.can_execute("ls -la")

        assert can_exec
        assert reason is None

    def test_can_execute_empty_command(self) -> None:
        """Test can_execute for empty commands."""
        can_exec, reason = self.executor.can_execute("")

        assert not can_exec
        assert reason is not None

    def test_can_execute_nonexistent_command(self) -> None:
        """Test can_execute for nonexistent commands."""
        can_exec, reason = self.executor.can_execute("nonexistent_cmd_xyz123")

        assert not can_exec
        assert "not found" in reason.lower()

    def test_execute_with_stderr_output(self) -> None:
        """Test command that produces stderr."""
        result = self.executor.execute("echo 'error' >&2")

        # Should succeed even with stderr
        assert result.exit_code == 0
        assert "error" in result.stderr


class TestInteractiveExecutor:
    """Test cases for InteractiveExecutor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.base_executor = CommandExecutor(timeout=5)
        self.executor = InteractiveExecutor(self.base_executor)

    def test_requires_confirmation_for_sudo(self) -> None:
        """Test that sudo commands require confirmation."""
        requires, reason = self.executor.requires_confirmation("sudo apt update")

        assert requires
        assert "privilege" in reason.lower()

    def test_requires_confirmation_for_rm(self) -> None:
        """Test that rm commands require confirmation."""
        requires, reason = self.executor.requires_confirmation("rm important_file.txt")

        assert requires
        assert "delete" in reason.lower()

    def test_requires_confirmation_for_dangerous_rm(self) -> None:
        """Test that rm -rf requires confirmation."""
        requires, reason = self.executor.requires_confirmation("rm -rf /some/path")

        assert requires
        assert "DANGER" in reason or "delete" in reason.lower()

    def test_no_confirmation_for_safe_commands(self) -> None:
        """Test that safe commands don't require confirmation."""
        requires, reason = self.executor.requires_confirmation("ls -la")

        assert not requires

    def test_execute_without_confirmation_fails(self) -> None:
        """Test that dangerous commands fail without confirmation."""
        result = self.executor.execute_with_confirmation(
            "sudo apt update",
            confirmed=False
        )

        assert not result.success
        assert "confirmation required" in result.error_message.lower()

    def test_execute_with_confirmation_succeeds(self) -> None:
        """Test that confirmed safe commands execute."""
        result = self.executor.execute_with_confirmation(
            "echo 'test'",
            confirmed=True
        )

        assert result.success
        assert "test" in result.stdout

    def test_requires_confirmation_for_chmod(self) -> None:
        """Test that chmod requires confirmation."""
        requires, reason = self.executor.requires_confirmation("chmod 777 file.txt")

        assert requires

    def test_requires_confirmation_for_systemctl(self) -> None:
        """Test that systemctl requires confirmation."""
        requires, reason = self.executor.requires_confirmation("systemctl restart nginx")

        assert requires
