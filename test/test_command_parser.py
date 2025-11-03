"""Unit tests for command parser."""
import pytest
from legacyhelper.core.command_parser import CommandParser, ParsedCommand


class TestCommandParser:
    """Test cases for CommandParser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_extract_from_code_block(self) -> None:
        """Test extracting commands from markdown code blocks."""
        text = """
        Here's how to check disk space:
        ```bash
        df -h
        ```
        """
        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert commands[0].command == "df -h"
        assert commands[0].confidence > 0.8

    def test_extract_from_inline_code(self) -> None:
        """Test extracting commands from inline code."""
        text = "You can use `ls -la` to list all files."

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert "ls -la" in commands[0].command

    def test_extract_multiple_commands(self) -> None:
        """Test extracting multiple commands from text."""
        text = """
        First run `df -h` to check disk space.
        Then use ```bash
        du -sh /*
        ```
        to see directory sizes.
        """

        commands = self.parser.extract_commands(text)

        assert len(commands) >= 2

    def test_dangerous_command_detection(self) -> None:
        """Test detection of dangerous commands."""
        dangerous_text = """
        ```bash
        rm -rf /
        ```
        """

        commands = self.parser.extract_commands(dangerous_text)

        assert len(commands) > 0
        assert not commands[0].is_safe
        assert len(commands[0].warnings) > 0

    def test_safe_command_detection(self) -> None:
        """Test that safe commands are marked as safe."""
        safe_text = """
        ```bash
        df -h
        ```
        """

        commands = self.parser.extract_commands(safe_text)

        assert len(commands) > 0
        assert commands[0].is_safe

    def test_rm_command_warning(self) -> None:
        """Test that rm commands get warnings."""
        text = "Use `rm old_file.txt` to remove it."

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert any("delete" in w.lower() for w in commands[0].warnings)

    def test_sudo_command_warning(self) -> None:
        """Test that sudo commands get warnings."""
        text = "Run `sudo systemctl restart nginx`"

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert any("privilege" in w.lower() for w in commands[0].warnings)

    def test_command_description_generation(self) -> None:
        """Test that descriptions are generated correctly."""
        text = "`df -h`"

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert len(commands[0].description) > 0
        assert "disk" in commands[0].description.lower()

    def test_get_best_command(self) -> None:
        """Test getting the best command from multiple options."""
        text = """
        You can check with `ls` or use:
        ```bash
        df -h
        ```
        """

        best = self.parser.get_best_command(text)

        assert best is not None
        # Code block should have higher confidence
        assert best.command == "df -h"

    def test_no_commands_in_text(self) -> None:
        """Test handling text with no commands."""
        text = "This is just plain text about Linux systems."

        commands = self.parser.extract_commands(text)

        # Should return empty list or no high-confidence commands
        assert len(commands) == 0 or all(c.confidence < 0.5 for c in commands)

    def test_command_with_pipe(self) -> None:
        """Test parsing commands with pipes."""
        text = "`ps aux | grep python`"

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert "|" in commands[0].command

    def test_multiline_code_block(self) -> None:
        """Test parsing multiline code blocks."""
        text = """
        ```bash
        cd /var/log
        tail -f syslog
        ```
        """

        commands = self.parser.extract_commands(text)

        # Should extract both commands
        assert len(commands) >= 2

    def test_command_prefix_removal(self) -> None:
        """Test that $ and # prefixes are removed."""
        text = "`$ df -h`"

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert not commands[0].command.startswith("$")

    def test_chmod_warning(self) -> None:
        """Test chmod commands get appropriate warnings."""
        text = "`chmod 777 file.txt`"

        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert any("permission" in w.lower() for w in commands[0].warnings)
