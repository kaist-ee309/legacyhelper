from typing import Optional
from legacyhelper.model.gemini import GeminiModel
from legacyhelper.model.base import BaseModel
from legacyhelper.core.history_reader import read_recent_history, format_history_context
from rich.console import Console
from rich.prompt import Prompt


class Agent:
    """AI Agent for troubleshooting legacy systems."""

    def __init__(self, model: Optional[BaseModel] = None) -> None:
        """Initialize the agent.

        Args:
            model: Optional model instance. Defaults to GeminiModel.
        """
        self.model = model if model is not None else GeminiModel()
        self.console = Console()
        self.conversation_history: list[dict[str, str]] = []

    def _build_prompt_with_history(self, prompt: str) -> str:
        """Build a prompt with shell history context.

        Args:
            prompt: The user's original prompt

        Returns:
            Prompt with history context prepended
        """
        history = read_recent_history(count=10)
        if not history:
            return prompt
        
        history_context = format_history_context(history)
        return f"{history_context}\n\nUser question: {prompt}"

    def get_response(self, prompt: str) -> str:
        """Get a response from the agent with history context.

        Args:
            prompt: The user's prompt

        Returns:
            The agent's response
        """
        enhanced_prompt = self._build_prompt_with_history(prompt)
        return self.model.get_response(enhanced_prompt)

    def run(self, prompt: str) -> str:
        """Run the agent with a prompt (legacy CLI mode).

        Args:
            prompt: The user's prompt

        Returns:
            The agent's response
        """
        response = self.get_response(prompt)

        # For now, we'll just present the response as a choice.
        # In the future, we will parse the response to extract commands.
        self.console.print("Proposed command:")
        self.console.print(f"[bold green]{response}[/bold green]")

        choice = Prompt.ask("Execute command?", choices=["y", "n"], default="n")

        if choice == "y":
            # We'll implement command execution in the next step.
            self.console.print("Executing command...")
        else:
            self.console.print("Command not executed.")

        return response

    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to conversation history.

        Args:
            role: The role (user/assistant/system)
            content: The message content
        """
        self.conversation_history.append({"role": role, "content": content})