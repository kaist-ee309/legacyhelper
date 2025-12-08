"""Custom widgets for LegacyHelper TUI."""
from textual.widgets import Static, Button, Label
from textual.containers import Container, Horizontal
from textual.app import ComposeResult
from rich.syntax import Syntax
from rich.markdown import Markdown


class MessageWidget(Static):
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

    def on_mount(self) -> None:
        """Render the message when mounted."""
        if self.role == "user":
            self.update(f"[bold cyan]You:[/bold cyan] {self.content}")
        elif self.role == "assistant":
            self.update(Markdown(f"**Assistant:** {self.content}"))
        elif self.role == "error":
            self.update(f"[bold red]Error:[/bold red] {self.content}")
        else:
            self.update(f"[dim italic]{self.content}[/dim italic]")


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
        if exit_code != 0:
            self.add_class("error-output")

    def compose(self) -> ComposeResult:
        """Compose the output display."""
        if self.exit_code == 0:
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
