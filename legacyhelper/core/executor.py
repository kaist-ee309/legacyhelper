"""Safe command execution with output capture."""
import subprocess
import shlex
from typing import Tuple, Optional
from dataclasses import dataclass
import os
import signal


@dataclass
class ExecutionResult:
    """Result of command execution."""

    command: str
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    error_message: Optional[str] = None


class CommandExecutor:
    """Executes shell commands safely with timeouts and output capture."""

    def __init__(self, timeout: int = 30, dry_run: bool = False) -> None:
        """Initialize the command executor.

        Args:
            timeout: Maximum execution time in seconds
            dry_run: If True, don't actually execute commands
        """
        self.timeout = timeout
        self.dry_run = dry_run

    def execute(self, command: str, shell: bool = True) -> ExecutionResult:
        """Execute a command and return the result.

        Args:
            command: The command to execute
            shell: Whether to use shell mode (default True for complex commands)

        Returns:
            ExecutionResult with output and status
        """
        if self.dry_run:
            return ExecutionResult(
                command=command,
                stdout="[DRY RUN] Command not executed",
                stderr="",
                exit_code=0,
                success=True
            )

        try:
            # Run the command with timeout
            process = subprocess.Popen(
                command if shell else shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=shell,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )

            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                exit_code = process.returncode

                return ExecutionResult(
                    command=command,
                    stdout=stdout.strip(),
                    stderr=stderr.strip(),
                    exit_code=exit_code,
                    success=exit_code == 0
                )

            except subprocess.TimeoutExpired:
                # Kill the process group
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()

                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()

                return ExecutionResult(
                    command=command,
                    stdout=stdout.strip() if stdout else "",
                    stderr=stderr.strip() if stderr else "",
                    exit_code=-1,
                    success=False,
                    error_message=f"Command timed out after {self.timeout} seconds"
                )

        except Exception as e:
            return ExecutionResult(
                command=command,
                stdout="",
                stderr="",
                exit_code=-1,
                success=False,
                error_message=f"Execution error: {str(e)}"
            )

    def can_execute(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if a command can be executed safely.

        Args:
            command: The command to check

        Returns:
            Tuple of (can_execute, reason_if_not)
        """
        # Check if command is empty
        if not command or not command.strip():
            return False, "Empty command"

        # Extract the base command
        parts = shlex.split(command)
        if not parts:
            return False, "Invalid command format"

        base_cmd = parts[0]

        # Check if command exists
        if not self._command_exists(base_cmd):
            return False, f"Command '{base_cmd}' not found"

        return True, None

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH.

        Args:
            command: The command name to check

        Returns:
            True if command exists
        """
        # Remove sudo prefix
        if command == 'sudo' and len(command.split()) > 1:
            command = command.split()[1]

        return subprocess.run(
            ['which', command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).returncode == 0


class InteractiveExecutor:
    """Executor that requires user confirmation for dangerous operations."""

    DANGER_KEYWORDS = {
        'rm': "Delete files",
        'mkfs': "Format filesystem",
        'dd': "Low-level disk operations",
        'chmod': "Change permissions",
        'chown': "Change ownership",
        'iptables': "Modify firewall rules",
        'systemctl': "Control system services",
    }

    def __init__(self, executor: CommandExecutor) -> None:
        """Initialize interactive executor.

        Args:
            executor: The underlying command executor
        """
        self.executor = executor

    def requires_confirmation(self, command: str) -> Tuple[bool, str]:
        """Check if command requires user confirmation.

        Args:
            command: The command to check

        Returns:
            Tuple of (requires_confirmation, reason)
        """
        cmd_lower = command.lower()

        # Check for sudo
        if cmd_lower.startswith('sudo'):
            return True, "Command requires elevated privileges"

        # Check for dangerous keywords
        for keyword, description in self.DANGER_KEYWORDS.items():
            if keyword in cmd_lower:
                return True, f"{description} - Please review carefully"

        # Check for destructive patterns
        if 'rm -rf' in cmd_lower:
            return True, "⚠️  DANGER: Recursive deletion - This will permanently delete files!"

        if '>' in command and '/dev/' in command:
            return True, "⚠️  DANGER: Writing to device file"

        return False, ""

    def execute_with_confirmation(
        self,
        command: str,
        confirmed: bool = False
    ) -> ExecutionResult:
        """Execute command, requiring confirmation if dangerous.

        Args:
            command: The command to execute
            confirmed: Whether user has confirmed execution

        Returns:
            ExecutionResult
        """
        requires_confirm, reason = self.requires_confirmation(command)

        if requires_confirm and not confirmed:
            return ExecutionResult(
                command=command,
                stdout="",
                stderr="",
                exit_code=-1,
                success=False,
                error_message=f"Confirmation required: {reason}"
            )

        return self.executor.execute(command)
