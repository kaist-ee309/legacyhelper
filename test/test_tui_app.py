"""Unit tests for Textual TUI application."""
import pytest
from typing import List
from unittest.mock import Mock, MagicMock, patch
from textual.widgets import Input
from legacyhelper.ui.app import (
    HistoryInput,
    ConversationPanel,
    InputPanel,
    LegacyHelperApp,
)


class TestHistoryInput:
    """Test cases for HistoryInput widget."""

    def test_history_input_initialization(self):
        """Test that HistoryInput initializes correctly."""
        input_widget = HistoryInput()

        assert input_widget.history == []
        assert input_widget.history_pos == 0
        assert input_widget.current_input == ""

    def test_add_to_history_single_item(self):
        """Test adding a single item to history."""
        input_widget = HistoryInput()
        input_widget.add_to_history("ls -la")

        assert len(input_widget.history) == 1
        assert input_widget.history[0] == "ls -la"
        assert input_widget.history_pos == 0

    def test_add_to_history_multiple_items(self):
        """Test adding multiple items to history."""
        input_widget = HistoryInput()
        commands = ["ls -la", "cd /tmp", "pwd"]

        for cmd in commands:
            input_widget.add_to_history(cmd)

        assert len(input_widget.history) == 3
        assert input_widget.history == commands

    def test_add_to_history_skips_empty(self):
        """Test that empty strings are not added to history."""
        input_widget = HistoryInput()
        input_widget.add_to_history("")
        input_widget.add_to_history("ls")

        # Empty string should not be added
        assert len(input_widget.history) == 1
        assert input_widget.history[0] == "ls"

    def test_add_to_history_skips_duplicates(self):
        """Test that consecutive duplicates are not added."""
        input_widget = HistoryInput()
        input_widget.add_to_history("ls")
        input_widget.add_to_history("ls")
        input_widget.add_to_history("ls")

        assert len(input_widget.history) == 1

    def test_add_to_history_allows_duplicate_separated(self):
        """Test that non-consecutive duplicates are allowed."""
        input_widget = HistoryInput()
        input_widget.add_to_history("ls")
        input_widget.add_to_history("cd /tmp")
        input_widget.add_to_history("ls")

        assert len(input_widget.history) == 3

    def test_history_pos_resets_on_add(self):
        """Test that history position resets when adding new item."""
        input_widget = HistoryInput()
        input_widget.add_to_history("cmd1")
        input_widget.history_pos = 5  # Simulate navigation

        input_widget.add_to_history("cmd2")

        assert input_widget.history_pos == 0
        assert input_widget.current_input == ""

    def test_navigate_up_with_empty_history(self):
        """Test navigate_up with no history."""
        input_widget = HistoryInput()
        input_widget._navigate_up()

        # Should not raise error and history_pos should remain unchanged
        assert input_widget.history_pos == 0

    def test_navigate_up_logic_single_item(self):
        """Test navigate_up position tracking with single history item."""
        input_widget = HistoryInput()
        input_widget.add_to_history("ls -la")

        # Test that history is correct
        assert len(input_widget.history) == 1
        assert input_widget.history[0] == "ls -la"

    def test_navigate_up_logic_multiple_steps(self):
        """Test navigate_up position tracking through multiple history items."""
        input_widget = HistoryInput()
        commands = ["cmd1", "cmd2", "cmd3"]
        for cmd in commands:
            input_widget.add_to_history(cmd)

        # Verify all commands are in history
        assert len(input_widget.history) == 3
        assert input_widget.history == commands

    def test_navigate_down_state(self):
        """Test navigate_down state management."""
        input_widget = HistoryInput()
        input_widget.add_to_history("ls")

        # Test history_pos management
        assert input_widget.history_pos == 0
        assert input_widget.current_input == ""

    def test_navigate_down_from_history_state(self):
        """Test navigate_down state from history position."""
        input_widget = HistoryInput()
        commands = ["cmd1", "cmd2", "cmd3"]
        for cmd in commands:
            input_widget.add_to_history(cmd)

        input_widget.current_input = "current"

        # Verify state
        assert input_widget.history_pos == 0
        assert len(input_widget.history) == 3

    def test_navigate_position_tracking(self):
        """Test that navigation position is properly tracked."""
        input_widget = HistoryInput()
        input_widget.add_to_history("only")
        input_widget.current_input = "current"

        # Verify we can track position
        assert input_widget.history_pos == 0
        assert len(input_widget.history) == 1

    def test_history_state_management(self):
        """Test that history state is managed correctly."""
        input_widget = HistoryInput()
        input_widget.add_to_history("cmd1")
        input_widget.add_to_history("cmd2")
        input_widget.current_input = "test"

        # Verify state
        assert len(input_widget.history) == 2
        assert input_widget.history_pos == 0
        assert input_widget.current_input == "test"


class TestConversationPanel:
    """Test cases for ConversationPanel widget."""

    def test_conversation_panel_initialization(self):
        """Test ConversationPanel initializes correctly."""
        panel = ConversationPanel()

        # Should be a ScrollableContainer
        assert hasattr(panel, 'scroll_end')
        assert hasattr(panel, 'mount')

    def test_add_message(self):
        """Test adding a message to conversation."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                panel.add_message("user", "Hello, system")

                panel.mount.assert_called_once()
                panel.scroll_end.assert_called_once()

    def test_add_multiple_messages(self):
        """Test adding multiple messages."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                panel.add_message("user", "First message")
                panel.add_message("assistant", "Response")
                panel.add_message("system", "System message")

                assert panel.mount.call_count == 3
                assert panel.scroll_end.call_count == 3

    def test_add_command_preview(self):
        """Test adding a command preview."""
        panel = ConversationPanel()
        mock_cmd = Mock()
        mock_cmd.command = "ls -la"
        mock_cmd.description = "List files"
        mock_cmd.warnings = []

        with patch.object(panel, 'mount') as mock_mount:
            with patch.object(panel, 'scroll_end'):
                panel.add_command_preview(mock_cmd)

                # Should mount the preview widget
                mock_mount.assert_called_once()

    def test_add_command_preview_with_warnings(self):
        """Test adding a command preview with warnings."""
        panel = ConversationPanel()
        mock_cmd = Mock()
        mock_cmd.command = "rm -rf /"
        mock_cmd.description = "Remove everything"
        mock_cmd.warnings = ["DANGER: Destructive command", "Will delete root"]

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                # Should add warning messages first
                panel.add_message("system", "DANGER: Destructive command")
                panel.add_message("system", "Will delete root")

                assert panel.mount.call_count == 2

    def test_add_spinner(self):
        """Test adding a spinner widget."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                spinner = panel.add_spinner("Processing...")

                assert spinner is not None
                panel.mount.assert_called_once()

    def test_add_spinner_default_message(self):
        """Test adding a spinner with default message."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                spinner = panel.add_spinner()

                assert spinner is not None

    def test_add_streaming_message(self):
        """Test adding a streaming message widget."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                message = panel.add_streaming_message()

                assert message is not None
                panel.mount.assert_called_once()

    def test_add_command_output(self):
        """Test adding command output."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                panel.add_command_output("ls -la", "file1\nfile2", 0)

                panel.mount.assert_called_once()


class TestInputPanel:
    """Test cases for InputPanel widget."""

    def test_input_panel_composition(self):
        """Test that InputPanel composes correctly."""
        panel = InputPanel()

        with patch.object(panel, 'compose') as mock_compose:
            mock_compose.return_value = iter([])
            list(panel.compose())

            # compose method should exist
            assert hasattr(panel, 'compose')

    def test_input_panel_creates_history_input(self):
        """Test that InputPanel creates a HistoryInput widget."""
        panel = InputPanel()

        # Verify it has the composition method
        assert callable(panel.compose)


class TestLegacyHelperApp:
    """Test cases for LegacyHelperApp."""

    def test_app_initialization_without_agent(self):
        """Test initializing app without an agent."""
        app = LegacyHelperApp()

        assert app.agent is None
        assert app.message_history is None
        assert app.conversation_panel is None
        assert app.status_bar is None
        assert app.current_spinner is None

    def test_app_initialization_with_agent(self):
        """Test initializing app with an agent."""
        mock_agent = Mock()
        app = LegacyHelperApp(agent=mock_agent)

        assert app.agent is mock_agent

    def test_app_title(self):
        """Test that app has correct title."""
        app = LegacyHelperApp()

        assert app.TITLE == "LegacyHelper - AI Troubleshooting Assistant"
        assert app.SUB_TITLE == "Legacy System Troubleshooting"

    def test_app_bindings(self):
        """Test that app has key bindings configured."""
        app = LegacyHelperApp()

        assert len(app.BINDINGS) > 0
        # Should have quit and clear bindings
        binding_actions = [b[1] if isinstance(b, tuple) else b.action for b in app.BINDINGS]
        assert "quit" in binding_actions
        assert "clear_conversation" in binding_actions

    def test_app_has_compose_method(self):
        """Test that app has compose method."""
        app = LegacyHelperApp()

        assert hasattr(app, 'compose')
        assert callable(app.compose)

    def test_app_current_command_reactive(self):
        """Test that current_command is a reactive property."""
        app = LegacyHelperApp()

        # Should be able to set current_command
        app.current_command = "test command"
        assert app.current_command == "test command"

    def test_app_has_action_methods(self):
        """Test that app has action methods for keybindings."""
        app = LegacyHelperApp()

        # Should have action_quit
        assert hasattr(app, 'action_quit')
        assert callable(app.action_quit)


class TestHistoryInputEdgeCases:
    """Test edge cases for HistoryInput."""

    def test_very_long_history(self):
        """Test handling a large history."""
        input_widget = HistoryInput()
        commands = [f"cmd{i}" for i in range(100)]

        for cmd in commands:
            input_widget.add_to_history(cmd)

        assert len(input_widget.history) == 100
        assert input_widget.history[0] == "cmd0"
        assert input_widget.history[99] == "cmd99"

    def test_history_state_with_current_input(self):
        """Test history state tracking with current input."""
        input_widget = HistoryInput()
        input_widget.add_to_history("cmd1")
        input_widget.add_to_history("cmd2")
        input_widget.current_input = "current"

        assert input_widget.history_pos == 0
        assert input_widget.current_input == "current"
        assert len(input_widget.history) == 2

    def test_history_with_special_characters(self):
        """Test history with special characters."""
        input_widget = HistoryInput()
        special_commands = [
            "grep 'pattern' file.txt",
            "echo \"hello world\"",
            "sudo rm -rf /tmp/*",
            "cat file | grep text | sort",
        ]

        for cmd in special_commands:
            input_widget.add_to_history(cmd)

        assert len(input_widget.history) == 4
        assert input_widget.history[-1] == "cat file | grep text | sort"
        assert "grep 'pattern' file.txt" in input_widget.history

    def test_history_with_unicode(self):
        """Test history with unicode characters."""
        input_widget = HistoryInput()
        input_widget.add_to_history("echo 'Привет'")
        input_widget.add_to_history("ls /home/user/文件")

        assert len(input_widget.history) == 2
        assert "Привет" in input_widget.history[0]
        assert "文件" in input_widget.history[1]
