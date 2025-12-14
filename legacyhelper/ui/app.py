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
    StatusBarWidget,
    SpinnerWidget,
    StreamingMessageWidget
)
from legacyhelper.core.workflow import Workflow, WorkflowCallbacks


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
        if not self.history_pos:
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

        if not self.history_pos:
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

    def add_spinner(self, message: str = "Thinking...") -> SpinnerWidget:
        """Add a spinner widget to show processing state.

        Args:
            message: The message to display with the spinner

        Returns:
            The mounted SpinnerWidget
        """
        spinner = SpinnerWidget(message)
        self.mount(spinner)
        self.scroll_end(animate=True)
        return spinner

    def add_streaming_message(self) -> StreamingMessageWidget:
        """Add a streaming message widget.

        Returns:
            The mounted StreamingMessageWidget
        """
        message = StreamingMessageWidget(parent_container=self)
        self.mount(message)
        self.scroll_end(animate=True)
        return message

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

    def __init__(self, agent: Agent = None, **kwargs) -> None:
        """Initialize the app.

        Args:
            agent: The LegacyHelper agent instance to use
        """
        super().__init__(**kwargs)
        self.agent = agent
        self.conversation_panel: Optional[ConversationPanel] = None
        self.status_bar: Optional[StatusBarWidget] = None
        self.current_spinner: Optional[SpinnerWidget] = None
        self.streaming_message: Optional[StreamingMessageWidget] = None
        # Locks for thread-safe access to shared state
        self._spinner_lock = asyncio.Lock()
        self._streaming_lock = asyncio.Lock()
        self._processing = False  # Flag to prevent concurrent submissions
        # Instantiate workflow object that supervises agent state and message history
        self.workflow = Workflow()

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

    async def _add_spinner(self, message: str) -> None:
        """Thread-safe method to add a spinner.

        Args:
            message: Message to display with spinner
        """
        async with self._spinner_lock:
            if self.current_spinner is None and self.conversation_panel:
                self.current_spinner = self.conversation_panel.add_spinner(message)

    async def _remove_spinner(self) -> None:
        """Thread-safe method to remove the current spinner."""
        async with self._spinner_lock:
            if self.current_spinner:
                await self.current_spinner.remove()
                self.current_spinner = None

    async def _add_streaming_message(self) -> Optional[StreamingMessageWidget]:
        """Thread-safe method to add a streaming message widget.

        Returns:
            The created StreamingMessageWidget or None
        """
        async with self._streaming_lock:
            if self.conversation_panel:
                self.streaming_message = self.conversation_panel.add_streaming_message()
            return self.streaming_message

    async def _append_to_stream(self, text: str) -> None:
        """Thread-safe method to append text to streaming message.

        Args:
            text: Text chunk to append
        """
        async with self._streaming_lock:
            if self.streaming_message:
                self.streaming_message.append_text(text)

    async def _clear_streaming_message(self) -> None:
        """Thread-safe method to clear the streaming message reference."""
        async with self._streaming_lock:
            self.streaming_message = None

    def _update_status(self, status: str) -> None:
        """Update the status bar.

        Args:
            status: The new status
        """
        if self.status_bar:
            self.status_bar.set_status(status)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission.

        Args:
            event: The input submission event
        """
        user_input = event.value.strip()
        if not user_input:
            return

        # Prevent concurrent submissions
        if self._processing:
            return
        self._processing = True

        try:
            # Add to history and clear input
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.add_to_history(user_input)
            event.input.value = ""

            # Add user message to conversation
            if self.conversation_panel:
                self.conversation_panel.add_message("user", user_input)

            # Add spinner (thread-safe)
            await self._add_spinner("Thinking...")

            # Update status
            if self.status_bar:
                self.status_bar.set_status("thinking")

            # Get response from agent with streaming
            if self.agent:
                callbacks = WorkflowCallbacks(
                    on_spinner_add=self._add_spinner,
                    on_spinner_remove=self._remove_spinner,
                    on_streaming_start=self._add_streaming_message,
                    on_stream_append=self._append_to_stream,
                    on_stream_clear=self._clear_streaming_message,
                    on_error=self._handle_error,
                    on_status_update=self._update_status,
                )
                await self.workflow.process_agent_response(
                    self.agent, user_input, callbacks
                )

        except Exception as exc:  # pylint: disable=broad-except
            await self._handle_error(exc)
        finally:
            self._processing = False

    async def _handle_error(self, error: Exception) -> None:
        """Handle errors during processing.

        Args:
            error: The exception that occurred
        """
        # Remove spinner on error (thread-safe)
        await self._remove_spinner()
        # Clear streaming message reference
        await self._clear_streaming_message()

        if self.conversation_panel:
            self.conversation_panel.add_message("error", str(error))

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
            pass

        elif button_id == "reject-cmd":
            pass

        elif button_id == "modify-cmd" and self.current_command:
            pass

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
