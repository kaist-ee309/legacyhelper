"""Main Textual application for LegacyHelper."""
import asyncio
from typing import Optional, List
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Input
from textual.binding import Binding
from textual.reactive import reactive
from textual import events
from pydantic_ai import Agent

from legacyhelper.ui.widgets import (
    MessageWidget,
    CommandPreviewWidget,
    CommandOutputWidget,
    StatusBarWidget
)


class HistoryInput(Input):
    """Input widget with command history navigation using up/down arrows."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize input with history support."""
        super().__init__(*args, **kwargs)
        self.history: List[str] = []
        # 0 = current input, 1 = most recent, 2 = second most recent, etc.
        self.history_pos: int = 0
        self.current_input: str = ""

    def add_to_history(self, text: str) -> None:
        """Add a command to history.

        Args:
            text: The text to add to history
        """
        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self.history_pos = 0
        self.current_input = ""

    def on_key(self, event: events.Key) -> None:
        """Handle key events for history navigation.

        Args:
            event: The key event
        """
        if event.key == "up":
            event.prevent_default()
            self._navigate_up()
        elif event.key == "down":
            event.prevent_default()
            self._navigate_down()

    def _navigate_up(self) -> None:
        """Go to older (previous) history entry."""
        if not self.history:
            return

        # Save current input when starting navigation
        if self.history_pos == 0:
            self.current_input = self.value

        # If at overflow, wrap back to most recent
        if self.history_pos > len(self.history):
            self.history_pos = 1
            self.value = self.history[-self.history_pos]
            self.cursor_position = len(self.value)
        elif self.history_pos < len(self.history):
            self.history_pos += 1
            # Get item from end of list (most recent first)
            self.value = self.history[-self.history_pos]
            self.cursor_position = len(self.value)
        else:
            # At oldest - go to empty (overflow)
            self.history_pos = len(self.history) + 1
            self.value = ""
            self.cursor_position = 0

    def _navigate_down(self) -> None:
        """Go to newer (more recent) history entry."""
        if self.history_pos <= 0:
            # Already at current or no history - go empty
            self.history_pos = 0
            self.value = ""
            self.cursor_position = 0
            self.current_input = ""
            return

        self.history_pos -= 1

        if self.history_pos == 0:
            # Back to current input
            self.value = self.current_input
            self.cursor_position = len(self.value)
        elif self.history_pos <= len(self.history):
            self.value = self.history[-self.history_pos]
            self.cursor_position = len(self.value)
        else:
            # Overflow - go empty
            self.value = ""
            self.cursor_position = 0


class ConversationPanel(ScrollableContainer):
    """Scrollable container for conversation messages."""

    DEFAULT_CSS = """
    ConversationPanel {
        height: 1fr;
        width: 100%;
        background: $background;
    }
    """

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation.

        Args:
            role: The role of the message sender
            content: The message content
        """
        message = MessageWidget(role, content)
        self.mount(message)
        self.scroll_end(animate=True)

    def add_command_preview(self, parsed_cmd) -> CommandPreviewWidget:
        """Add a command preview widget.

        Args:
            parsed_cmd: The parsed command with metadata

        Returns:
            The mounted CommandPreviewWidget
        """
        # Add warnings as system messages
        for warning in parsed_cmd.warnings:
            self.add_message("system", warning)

        preview = CommandPreviewWidget(parsed_cmd.command, parsed_cmd.description)
        self.mount(preview)
        self.scroll_end(animate=True)
        return preview

    def add_command_output(self, command: str, output: str, exit_code: int) -> None:
        """Add command execution output.

        Args:
            command: The executed command
            output: The command output
            exit_code: The exit code
        """
        output_widget = CommandOutputWidget(command, output, exit_code)
        self.mount(output_widget)
        self.scroll_end(animate=True)


class InputPanel(Container):
    """Container for user input and controls."""

    DEFAULT_CSS = """
    InputPanel {
        height: auto;
        width: 100%;
        background: $surface;
        padding: 1 2;
        dock: bottom;
    }

    InputPanel Input {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the input panel."""
        yield HistoryInput(
            placeholder="Type your question or command here... (up/down for history)",
            id="user-input"
        )


class LegacyHelperApp(App[None]):
    """Main LegacyHelper TUI application."""

    CSS = """
    Screen {
        background: $background;
    }

    #main-container {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+d", "quit", "Quit"),
        ("ctrl+l", "clear_conversation", "Clear"),
    ]

    TITLE = "LegacyHelper - AI Troubleshooting Assistant"
    SUB_TITLE = "Legacy System Troubleshooting"

    current_command: reactive = reactive(None)

    def __init__(self, agent:Agent=None, **kwargs) -> None:
        """Initialize the app.

        Args:
            agent: The LegacyHelper agent instance to use
        """
        super().__init__(**kwargs)
        self.agent = agent
        self.message_history = None
        self.conversation_panel: Optional[ConversationPanel] = None
        self.status_bar: Optional[StatusBarWidget] = None

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        with Container(id="main-container"):
            self.conversation_panel = ConversationPanel()
            yield self.conversation_panel
            yield InputPanel()
        self.status_bar = StatusBarWidget()
        yield self.status_bar
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - show welcome message."""
        if self.conversation_panel:
            self.conversation_panel.add_message(
                "system",
                "Welcome to LegacyHelper! Ask me anything about "
                "troubleshooting your Linux/UNIX system."
            )

        # Focus the input field
        input_widget = self.query_one("#user-input", HistoryInput)
        input_widget.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission.

        Args:
            event: The input submission event
        """
        user_input = event.value.strip()
        if not user_input:
            return

        # Add to history and clear input
        input_widget = self.query_one("#user-input", HistoryInput)
        input_widget.add_to_history(user_input)
        event.input.value = ""

        # Add user message to conversation
        if self.conversation_panel:
            self.conversation_panel.add_message("user", user_input)
            self.conversation_panel.add_message(
                "system",
                "🤔 Thinking..."
            )

        # Update status
        if self.status_bar:
            self.status_bar.set_status("thinking")

        # Get response from agent
        if self.agent:
            try:
                result = await self.agent.run(
                    user_input, message_history=self.message_history
                )
                response = str(result.output)
                self.message_history = result.all_messages()

                # Remove "thinking" message
                if self.conversation_panel:
                    messages = list(self.conversation_panel.query("MessageWidget"))
                    if messages and "Thinking" in str(messages[-1].content):
                        await messages[-1].remove()
                    self.conversation_panel.add_message("assistant", response)

                # Update status
                if self.status_bar:
                    self.status_bar.set_status("ready")

            except Exception as e:
                if self.conversation_panel:
                    messages = list(self.conversation_panel.query("MessageWidget"))
                    if messages:
                        await messages[-1].remove()
                    self.conversation_panel.add_message(
                        "error",
                        f"{str(e)}"
                    )

                if self.status_bar:
                    self.status_bar.set_status("error")

    async def on_button_pressed(self, event) -> None:
        """Handle button presses.

        Args:
            event: The button press event
        """
        if not hasattr(event, 'button') or not hasattr(event.button, 'id'):
            return

        button_id = event.button.id

        if button_id == "execute-cmd" and self.current_command:
            await self._execute_current_command()
            await event.button.parent.remove()

        elif button_id == "reject-cmd":
            if self.conversation_panel:
                self.conversation_panel.add_message(
                    "system",
                    "✗ Command rejected"
                )
            await event.button.parent.remove()
            self.current_command = None

        elif button_id == "modify-cmd" and self.current_command:
            # Pre-fill input with current command
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.value = self.current_command.command
            input_widget.focus()
            await event.button.parent.remove()
            self.current_command = None

    async def _execute_current_command(self) -> None:
        """Execute the currently selected command."""
        if not self.current_command or not self.conversation_panel:
            return

        command = self.current_command.command

        # Update status
        if self.status_bar:
            self.status_bar.set_status("thinking")

        self.conversation_panel.add_message(
            "system",
            f"⚙️ Executing: `{command}`"
        )

        # Check if we can execute
        can_exec, reason = self.command_executor.can_execute(command)
        if not can_exec:
            self.conversation_panel.add_message(
                "error",
                f"Cannot execute: {reason}"
            )
            if self.status_bar:
                self.status_bar.set_status("error")
            self.current_command = None
            return

        # Execute the command in a thread pool
        result = await asyncio.to_thread(
            self.interactive_executor.execute_with_confirmation,
            command,
            confirmed=True
        )

        # Display results
        if result.success:
            output = result.stdout if result.stdout else result.stderr
            self.conversation_panel.add_command_output(
                command,
                output,
                result.exit_code
            )
        else:
            error_msg = result.error_message or result.stderr or "Command failed"
            self.conversation_panel.add_message(
                "error",
                f"Execution failed: {error_msg}"
            )
            if result.stderr or result.stdout:
                self.conversation_panel.add_command_output(
                    command,
                    result.stderr or result.stdout,
                    result.exit_code
                )

        # Update status
        if self.status_bar:
            self.status_bar.set_status("ready" if result.success else "error")

        self.current_command = None

    def action_clear_conversation(self) -> None:
        """Clear the conversation panel."""
        if self.conversation_panel:
            for widget in self.conversation_panel.query(
                "MessageWidget, CommandPreviewWidget, CommandOutputWidget"
            ):
                widget.remove()
            self.conversation_panel.add_message(
                "system",
                "Conversation cleared. How can I help you?"
            )

        if self.status_bar:
            self.status_bar.set_status("ready")

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
