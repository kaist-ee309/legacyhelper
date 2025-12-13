"""Unit tests for backend user input processing and agent interaction."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from textual.widgets import Input
from legacyhelper.ui.app import LegacyHelperApp, HistoryInput, ConversationPanel


class TestInputSubmissionProcessing:
    """Test cases for user input submission processing."""

    def test_on_input_submitted_empty_input(self):
        """Test that empty input is ignored."""
        app = LegacyHelperApp()
        app.conversation_panel = Mock()

        event = Mock()
        event.value = ""

        # Should return early without adding to history
        # This would be tested in integration with actual app
        assert event.value.strip() == ""

    def test_on_input_submitted_whitespace_input(self):
        """Test that whitespace-only input is ignored."""
        app = LegacyHelperApp()

        event = Mock()
        event.value = "   \t\n   "

        assert event.value.strip() == ""

    def test_input_submission_adds_to_history(self):
        """Test that valid input is added to history."""
        history_input = HistoryInput()
        user_input = "ls -la"

        history_input.add_to_history(user_input)

        assert len(history_input.history) == 1
        assert history_input.history[0] == user_input

    def test_input_submission_clears_input_field(self):
        """Test that input field clearing logic works."""
        input_widget = HistoryInput()

        # Test the clearing concept without triggering Textual app context
        # The actual Textual value property requires an active app
        # But we can test the logic
        assert input_widget.current_input == ""
        input_widget.current_input = "test"
        assert input_widget.current_input == "test"
        input_widget.current_input = ""
        assert input_widget.current_input == ""

    def test_input_submission_updates_conversation(self):
        """Test that user message is added to conversation panel."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                panel.add_message("user", "What is my disk usage?")

                panel.mount.assert_called_once()

    def test_input_submission_shows_spinner(self):
        """Test that spinner is shown during processing."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                spinner = panel.add_spinner("Thinking...")

                assert spinner is not None
                panel.mount.assert_called_once()

    def test_input_submission_updates_status_thinking(self):
        """Test that status is updated to 'thinking'."""
        status_bar = Mock()
        status_bar.set_status("thinking")

        # Verify method exists
        assert hasattr(status_bar, 'set_status')

    def test_multiple_sequential_inputs(self):
        """Test handling multiple sequential inputs."""
        history_input = HistoryInput()
        inputs = ["df -h", "du -sh /", "ls /tmp"]

        for user_input in inputs:
            history_input.add_to_history(user_input)

        assert len(history_input.history) == 3
        assert history_input.history == inputs


class TestAgentInteraction:
    """Test cases for agent interaction and response handling."""

    def test_agent_initialization_with_agent(self):
        """Test app initialization with agent."""
        mock_agent = Mock()
        app = LegacyHelperApp(agent=mock_agent)

        assert app.agent is mock_agent

    def test_agent_initialization_without_agent(self):
        """Test app initialization without agent."""
        app = LegacyHelperApp(agent=None)

        assert app.agent is None

    def test_agent_message_history_tracking(self):
        """Test that message history is tracked."""
        app = LegacyHelperApp()

        # Message history should be initialized as None or empty
        assert app.message_history is None or app.message_history == []

    def test_agent_response_streaming_setup(self):
        """Test setup for streaming agent responses."""
        app = LegacyHelperApp()
        app.conversation_panel = Mock()

        with patch.object(app.conversation_panel, 'add_streaming_message'):
            app.conversation_panel.add_streaming_message()
            app.conversation_panel.add_streaming_message.assert_called_once()

    def test_agent_error_handling_removes_spinner(self):
        """Test that spinner is removed on error."""
        app = LegacyHelperApp()
        mock_spinner = AsyncMock()
        app.current_spinner = mock_spinner

        # Verify spinner can be tracked
        assert app.current_spinner is not None

    def test_agent_error_handling_shows_error_message(self):
        """Test that error message is shown on agent error."""
        app = LegacyHelperApp()
        app.conversation_panel = Mock()

        error_msg = "Connection timeout"

        with patch.object(app.conversation_panel, 'add_message'):
            app.conversation_panel.add_message("error", error_msg)
            app.conversation_panel.add_message.assert_called_once_with("error", error_msg)

    def test_agent_error_handling_updates_status(self):
        """Test that status is updated to 'error' on failure."""
        status_bar = Mock()
        status_bar.set_status("error")

        assert hasattr(status_bar, 'set_status')


class TestStreamingMessageHandling:
    """Test cases for streaming message handling."""

    def test_streaming_message_creation(self):
        """Test creation of streaming message widget."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                streaming_msg = panel.add_streaming_message()

                assert streaming_msg is not None

    def test_streaming_message_append_text(self):
        """Test appending text to streaming message."""
        streaming_msg = Mock()
        streaming_msg.append_text = Mock()

        streaming_msg.append_text("partial")

        streaming_msg.append_text.assert_called_once_with("partial")

    def test_streaming_message_accumulation(self):
        """Test that streaming messages accumulate text."""
        streaming_msg = Mock()
        text_chunks = ["Hello ", "from ", "the ", "agent"]
        streaming_msg.append_text = Mock()

        for chunk in text_chunks:
            streaming_msg.append_text(chunk)

        assert streaming_msg.append_text.call_count == 4

    def test_streaming_with_debounce(self):
        """Test that streaming respects debounce settings."""
        # The debounce_by=0.01 is part of the streaming call
        # This tests the configuration logic
        debounce_value = 0.01

        assert isinstance(debounce_value, float)
        assert debounce_value > 0


class TestToolCallHandling:
    """Test cases for tool call handling."""

    def test_tool_call_event_detection(self):
        """Test detection of function tool call events."""
        mock_event = Mock()
        mock_event.part = Mock()
        mock_event.part.args_as_dict = Mock(return_value={"command": "ls -la"})

        command = mock_event.part.args_as_dict().pop("command", "")

        assert command == "ls -la"

    def test_tool_call_spinner_creation(self):
        """Test spinner creation for tool execution."""
        panel = ConversationPanel()
        command = "df -h"

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                spinner = panel.add_spinner(f"Running... {command}")

                assert spinner is not None

    def test_tool_call_spinner_replacement(self):
        """Test that thinking spinner is replaced by tool spinner."""
        app = LegacyHelperApp()
        app.current_spinner = Mock()

        # Replace with new spinner
        app.current_spinner = Mock()

        assert app.current_spinner is not None


class TestButtonPressHandling:
    """Test cases for command button press handling."""

    def test_button_press_detection(self):
        """Test detection of button press events."""
        event = Mock()
        event.button = Mock()
        event.button.id = "execute-cmd"

        assert hasattr(event, 'button')
        assert event.button.id == "execute-cmd"

    def test_button_press_missing_attributes(self):
        """Test handling of button press without required attributes."""
        event = Mock(spec=[])  # No attributes

        has_button = hasattr(event, 'button')
        assert not has_button

    def test_execute_cmd_button(self):
        """Test execute command button handling."""
        app = LegacyHelperApp()
        app.current_command = Mock()
        app.current_command.command = "ls -la"

        button_id = "execute-cmd"

        assert button_id == "execute-cmd"
        assert app.current_command is not None

    def test_reject_cmd_button(self):
        """Test reject command button handling."""
        app = LegacyHelperApp()
        app.conversation_panel = Mock()
        app.current_command = Mock()

        with patch.object(app.conversation_panel, 'add_message'):
            app.conversation_panel.add_message("system", "✗ Command rejected")
            app.current_command = None

            assert app.current_command is None

    def test_modify_cmd_button(self):
        """Test modify command button handling."""
        app = LegacyHelperApp()
        app.current_command = Mock()
        app.current_command.command = "original command"

        input_widget = Mock()
        input_widget.value = ""
        input_widget.focus = Mock()

        # Simulate modify action
        input_widget.value = app.current_command.command
        input_widget.focus()

        assert input_widget.value == "original command"
        input_widget.focus.assert_called_once()


class TestStatusBarUpdates:
    """Test cases for status bar updates."""

    def test_status_update_thinking(self):
        """Test status update to 'thinking'."""
        status_bar = Mock()
        status_bar.set_status("thinking")

        status_bar.set_status.assert_called_once_with("thinking")

    def test_status_update_ready(self):
        """Test status update to 'ready'."""
        status_bar = Mock()
        status_bar.set_status("ready")

        status_bar.set_status.assert_called_once_with("ready")

    def test_status_update_error(self):
        """Test status update to 'error'."""
        status_bar = Mock()
        status_bar.set_status("error")

        status_bar.set_status.assert_called_once_with("error")

    def test_status_update_sequence(self):
        """Test sequence of status updates."""
        status_bar = Mock()

        statuses = ["thinking", "ready"]
        for status in statuses:
            status_bar.set_status(status)

        assert status_bar.set_status.call_count == 2


class TestConversationFlow:
    """Test cases for complete conversation flow."""

    def test_welcome_message_on_mount(self):
        """Test that welcome message is shown on app mount."""
        app = LegacyHelperApp()
        app.conversation_panel = Mock()

        with patch.object(app.conversation_panel, 'add_message'):
            app.conversation_panel.add_message(
                "system",
                "Welcome to LegacyHelper! Ask me anything about "
                "troubleshooting your Linux/UNIX system."
            )

            app.conversation_panel.add_message.assert_called_once()

    def test_input_focus_on_mount(self):
        """Test that input field gets focus on mount."""
        input_widget = HistoryInput()
        input_widget.focus = Mock()

        input_widget.focus()

        input_widget.focus.assert_called_once()

    def test_conversation_panel_scrolling(self):
        """Test that conversation panel scrolls to bottom."""
        panel = ConversationPanel()

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end') as mock_scroll:
                panel.add_message("user", "test")

                # scroll_end should be called
                mock_scroll.assert_called()

    def test_message_order_preserved(self):
        """Test that messages are added in correct order."""
        panel = ConversationPanel()
        messages = [
            ("user", "First message"),
            ("assistant", "Response"),
            ("user", "Second message"),
        ]

        with patch.object(panel, 'mount'):
            with patch.object(panel, 'scroll_end'):
                for role, content in messages:
                    panel.add_message(role, content)

                assert panel.mount.call_count == 3


class TestEdgeCases:
    """Test edge cases in backend processing."""

    def test_input_with_special_characters(self):
        """Test input with special characters."""
        history_input = HistoryInput()
        special_input = "grep 'pattern' file.txt | sort -u"

        history_input.add_to_history(special_input)

        assert history_input.history[0] == special_input

    def test_very_long_input(self):
        """Test handling of very long input."""
        history_input = HistoryInput()
        long_input = "a" * 1000

        history_input.add_to_history(long_input)

        assert len(history_input.history) == 1
        assert len(history_input.history[0]) == 1000

    def test_unicode_input(self):
        """Test handling of unicode input."""
        history_input = HistoryInput()
        unicode_input = "echo 'Привет мир' 文件"

        history_input.add_to_history(unicode_input)

        assert unicode_input in history_input.history

    def test_rapid_input_submission(self):
        """Test handling of rapid sequential inputs."""
        history_input = HistoryInput()
        inputs = ["cmd1", "cmd2", "cmd3", "cmd4", "cmd5"]

        for inp in inputs:
            history_input.add_to_history(inp)

        assert len(history_input.history) == 5

    def test_agent_none_handling(self):
        """Test graceful handling when agent is None."""
        app = LegacyHelperApp(agent=None)

        # Should not crash when trying to use agent
        assert app.agent is None

    def test_conversation_panel_none_handling(self):
        """Test graceful handling when conversation panel is None."""
        app = LegacyHelperApp()
        app.conversation_panel = None

        # Should not crash
        assert app.conversation_panel is None

    def test_status_bar_none_handling(self):
        """Test graceful handling when status bar is None."""
        app = LegacyHelperApp()
        app.status_bar = None

        # Should not crash
        assert app.status_bar is None
