"""Custom widgets for LegacyHelper TUI."""
import re
from typing import Optional
from textual.widgets import Static, Button, Label
from textual.containers import Container, Horizontal
from textual.app import ComposeResult
from textual.message import Message
from rich.syntax import Syntax
from rich.markdown import Markdown


def parse_markdown_segments(text: str) -> list:
    """Parse markdown into segments of text and code blocks.

    Only matches code blocks with a language specifier (```bash, ```python, etc.)

    Args:
        text: Markdown text containing code blocks

    Returns:
        List of tuples: ('text', content) or ('code', code, language)
    """
    segments = []
    remaining = text

    # Pattern for fenced code blocks with language: ```lang\ncode\n```
    # Requires at least one character for language (\w+)
    fenced_pattern = r'```([a-zA-Z]+)\n([\s\S]*?)```'

    last_end = 0
    for match in re.finditer(fenced_pattern, remaining):
        # Add text before this code block
        if match.start() > last_end:
            text_before = remaining[last_end:match.start()].strip()
            if text_before:
                segments.append(('text', text_before))

        # Add the code block
        lang = match.group(1)
        code = match.group(2).strip()
        if code:
            segments.append(('code', code, lang))

        last_end = match.end()

    # Add remaining text after last code block
    if last_end < len(remaining):
        text_after = remaining[last_end:].strip()
        if text_after:
            segments.append(('text', text_after))

    # If no fenced blocks found, return whole text
    if not segments:
        segments.append(('text', text))

    return segments


class CopyButton(Button):
    """A small copy button for copying content."""

    DEFAULT_CSS = """
    CopyButton {
        min-width: 5;
        width: 5;
        height: 3;
        min-height: 3;
        padding: 0 1;
        margin: 0;
        background: $surface;
        border: solid $primary-darken-1;
        content-align: center middle;
    }

    CopyButton:hover {
        background: $primary;
    }

    CopyButton.-copied {
        background: $success;
        border: solid $success;
    }
    """

    class Copied(Message):
        """Message emitted when content is copied."""

        def __init__(self, content: str) -> None:
            self.content = content
            super().__init__()

    def __init__(self, content_to_copy: str, **kwargs) -> None:
        """Initialize copy button.

        Args:
            content_to_copy: The content to copy when clicked
        """
        super().__init__("📋", **kwargs)
        self.content_to_copy = content_to_copy

    def on_click(self) -> None:
        """Handle click to copy content."""
        self.app.copy_to_clipboard(self.content_to_copy)
        self.label = "✓"
        self.add_class("-copied")
        self.set_timer(1.5, self._reset_button)

    def _reset_button(self) -> None:
        """Reset button to original state."""
        self.label = "📋"
        self.remove_class("-copied")


class MessageContent(Static):
    """Static widget for message content."""

    DEFAULT_CSS = """
    MessageContent {
        width: 1fr;
    }
    """


class CodeBlockWidget(Container):
    """Widget for displaying a code block with copy button on the right."""

    DEFAULT_CSS = """
    CodeBlockWidget {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 1 0;
    }

    CodeBlockWidget .code-content {
        width: 1fr;
        background: $surface-darken-2;
        padding: 1;
        border-left: thick $success;
    }

    CodeBlockWidget CopyButton {
        width: auto;
        height: auto;
        margin-left: 1;
    }
    """

    def __init__(self, code: str, language: str = "bash", **kwargs) -> None:
        """Initialize code block widget.

        Args:
            code: The code content
            language: The programming language for syntax highlighting
        """
        super().__init__(**kwargs)
        self.code = code
        self.language = language

    def compose(self) -> ComposeResult:
        """Compose the code block with copy button."""
        yield Static(
            Syntax(self.code, self.language, theme="monokai", line_numbers=False),
            classes="code-content"
        )
        yield CopyButton(self.code)


class MessageWidget(Container):
    """Widget for displaying a single message in the conversation."""

    DEFAULT_CSS = """
    MessageWidget {
        width: 100%;
        height: auto;
        padding: 1 2;
        margin-bottom: 1;
    }

    MessageWidget.user-message {
        background: $primary-darken-2;
        border-left: thick $primary;
    }

    MessageWidget.assistant-message {
        background: $surface-darken-1;
        border-left: thick $accent;
    }

    MessageWidget.system-message {
        background: $warning-darken-3;
        border-left: thick $warning;
    }

    MessageWidget.error-message {
        background: $error-darken-3;
        border-left: thick $error;
    }

    MessageWidget .assistant-label {
        margin-bottom: 1;
    }

    MessageWidget .text-content {
        width: 100%;
    }
    """

    def __init__(self, role: str, content: str, **kwargs) -> None:
        """Initialize message widget.

        Args:
            role: The role of the message sender (user, assistant, system, error)
            content: The message content
        """
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.add_class(f"{role}-message")

    def compose(self) -> ComposeResult:
        """Compose the message widget."""
        if self.role == "assistant":
            # Label on its own line
            yield Static("[bold magenta]Assistant:[/bold magenta]",
                         classes="assistant-label")
            # Parse content into text and code segments
            segments = parse_markdown_segments(self.content)
            for segment in segments:
                if segment[0] == 'text':
                    # Render text as markdown
                    yield Static(Markdown(segment[1]), classes="text-content")
                elif segment[0] == 'code':
                    # Render code block with copy button
                    yield CodeBlockWidget(segment[1], segment[2])
        else:
            content_widget = MessageContent()
            if self.role == "user":
                content_widget.update(f"[bold cyan]You:[/bold cyan] {self.content}")
            elif self.role == "error":
                content_widget.update(f"[bold red]Error:[/bold red] {self.content}")
            else:
                content_widget.update(f"[dim italic]{self.content}[/dim italic]")
            yield content_widget


class StreamingMessageWidget(Container):
    """Widget for displaying a streaming assistant message with incremental text updates."""

    DEFAULT_CSS = """
    StreamingMessageWidget {
        width: 100%;
        height: auto;
        padding: 1 2;
        margin-bottom: 1;
        background: $surface-darken-1;
        border-left: thick $accent;
    }

    StreamingMessageWidget .assistant-label {
        margin-bottom: 1;
    }

    StreamingMessageWidget .text-content {
        width: 100%;
    }
    """

    def __init__(self, parent_container=None, **kwargs) -> None:
        """Initialize streaming message widget.

        Args:
            parent_container: Reference to parent ScrollableContainer for auto-scroll
        """
        super().__init__(**kwargs)
        self.add_class("assistant-message")
        self.text_content: Optional[Static] = None
        self.accumulated_text: str = ""
        self.parent_container = parent_container
        self._update_pending = False

    def compose(self) -> ComposeResult:
        """Compose the streaming message widget."""
        yield Static("[bold magenta]Assistant:[/bold magenta]",
                     classes="assistant-label")
        self.text_content = Static("", classes="text-content", id="stream-text")
        yield self.text_content

    def append_text(self, chunk: str) -> None:
        """Append text chunk to the message.

        Thread-safe: Uses call_later to ensure UI updates happen on main thread.

        Args:
            chunk: Text chunk to append
        """
        self.accumulated_text += chunk
        # Schedule UI update on main thread to avoid race conditions
        if not self._update_pending:
            self._update_pending = True
            self.call_later(self._do_update)

    def _do_update(self) -> None:
        """Perform the actual UI update on the main thread."""
        self._update_pending = False

        if self.text_content:
            self.text_content.update(Markdown(self.accumulated_text))

        # Auto-scroll parent container to keep new text visible
        if self.parent_container:
            self.parent_container.scroll_end(animate=False)

    def get_content(self) -> str:
        """Get the complete accumulated text.

        Returns:
            The complete message content
        """
        return self.accumulated_text


class CommandPreviewWidget(Container):
    """Widget for displaying and selecting proposed commands."""

    DEFAULT_CSS = """
    CommandPreviewWidget {
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
        margin: 1 2;
    }

    CommandPreviewWidget > .command-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    CommandPreviewWidget > .command-description {
        color: $text-muted;
        margin-bottom: 1;
    }

    CommandPreviewWidget > .command-code {
        background: $surface-darken-2;
        padding: 1;
        margin-bottom: 1;
        border-left: thick $success;
    }

    CommandPreviewWidget > Horizontal {
        height: auto;
        width: 100%;
        align: center middle;
    }

    CommandPreviewWidget Button {
        margin: 0 1;
    }
    """

    def __init__(self, command: str, description: str = "", **kwargs) -> None:
        """Initialize command preview widget.

        Args:
            command: The command to preview
            description: Optional description of what the command does
        """
        super().__init__(**kwargs)
        self.command = command
        self.description = description

    def compose(self) -> ComposeResult:
        """Compose the command preview."""
        yield Label("🔧 Proposed Command:", classes="command-title")
        if self.description:
            yield Static(f"[dim]{self.description}[/dim]", classes="command-description")
        yield Static(
            Syntax(self.command, "bash", theme="monokai", line_numbers=False),
            classes="command-code"
        )
        with Horizontal():
            yield Button("✓ Execute", variant="success", id="execute-cmd")
            yield Button("✗ Reject", variant="error", id="reject-cmd")
            yield Button("✎ Modify", variant="primary", id="modify-cmd")


class CommandOutputWidget(Container):
    """Widget for displaying command execution output."""

    DEFAULT_CSS = """
    CommandOutputWidget {
        height: auto;
        border: solid $success;
        background: $surface-darken-1;
        padding: 1 2;
        margin: 1 2;
    }

    CommandOutputWidget.error-output {
        border: solid $error;
    }

    CommandOutputWidget > .output-title {
        text-style: bold;
        margin-bottom: 1;
    }

    CommandOutputWidget > .output-content {
        background: $surface-darken-3;
        padding: 1;
        color: $text;
        font: "Monospace";
    }

    CommandOutputWidget > .output-metadata {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        command: str,
        output: str,
        exit_code: int,
        **kwargs
    ) -> None:
        """Initialize command output widget.

        Args:
            command: The executed command
            output: The command output
            exit_code: The exit code
        """
        super().__init__(**kwargs)
        self.command = command
        self.output = output
        self.exit_code = exit_code
        if exit_code:
            self.add_class("error-output")

    def compose(self) -> ComposeResult:
        """Compose the output display."""
        if not self.exit_code:
            yield Label("✓ Command Output:", classes="output-title")
        else:
            yield Label(f"✗ Command Failed (exit code: {self.exit_code}):", classes="output-title")

        yield Static(
            f"$ {self.command}",
            classes="output-metadata"
        )
        yield Static(
            self.output if self.output else "[dim](no output)[/dim]",
            classes="output-content"
        )


class SpinnerWidget(Container):
    """Animated spinner widget for indicating processing state."""

    DEFAULT_CSS = """
    SpinnerWidget {
        width: 100%;
        height: auto;
        padding: 1 2;
        margin-bottom: 1;
        background: $warning-darken-3;
        border-left: thick $warning;
    }
    """

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Thinking...", **kwargs) -> None:
        """Initialize spinner widget.

        Args:
            message: The message to display alongside the spinner
        """
        super().__init__(**kwargs)
        self.message = message
        self.frame_index = 0
        self.content_widget = None

    def compose(self) -> ComposeResult:
        """Compose the spinner widget."""
        self.content_widget = MessageContent()
        yield self.content_widget

    def on_mount(self) -> None:
        """Start the spinner animation when mounted."""
        self.update_spinner()
        self.set_interval(0.1, self.update_spinner)

    def update_spinner(self) -> None:
        """Update the spinner to the next frame."""
        if self.content_widget:
            frame = self.SPINNER_FRAMES[self.frame_index]
            self.content_widget.update(
                f"[dim italic]{frame} {self.message}[/dim italic]"
            )
            self.frame_index = (self.frame_index + 1) % len(self.SPINNER_FRAMES)


class StatusBarWidget(Static):
    """Custom status bar with model info and connection status."""

    DEFAULT_CSS = """
    StatusBarWidget {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }

    StatusBarWidget .status-connected {
        color: $success;
    }

    StatusBarWidget .status-error {
        color: $error;
    }

    StatusBarWidget .status-thinking {
        color: $warning;
    }
    """

    def __init__(self, model_name: str = "Gemini", **kwargs) -> None:
        """Initialize status bar.

        Args:
            model_name: The name of the AI model being used
        """
        super().__init__(**kwargs)
        self.model_name = model_name
        self.status = "ready"

    def on_mount(self) -> None:
        """Update status on mount."""
        self.update_status()

    def set_status(self, status: str) -> None:
        """Set the current status.

        Args:
            status: Status string (ready, thinking, error)
        """
        self.status = status
        self.update_status()

    def update_status(self) -> None:
        """Update the status bar display."""
        status_icon = {
            "ready": "●",
            "thinking": "◐",
            "error": "✗"
        }.get(self.status, "○")

        status_class = {
            "ready": "status-connected",
            "thinking": "status-thinking",
            "error": "status-error"
        }.get(self.status, "")

        status_text = self.status.capitalize()

        self.update(
            f"[b]{self.model_name}[/b] [{status_class}]"
            f" {status_icon} {status_text}[/{status_class}] | "
            f"[dim]Ctrl+C: Quit | Ctrl+L: Clear[/dim]"
        )
