"""Anthropic Claude model implementation."""
import os
from typing import Optional
from anthropic import Anthropic
from legacyhelper.model.base import BaseModel


class ClaudeModel(BaseModel):
    """Anthropic Claude model implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> None:
        """Initialize Claude model.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var
            model: Model name (claude-3-5-sonnet-20241022, claude-3-opus-20240229, etc.)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
        """
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables. "
                "Set it with: export ANTHROPIC_API_KEY='your-key-here'"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_response(self, prompt: str) -> str:
        """Get a response from Claude.

        Args:
            prompt: The user's prompt

        Returns:
            The model's response text
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=(
                "You are a helpful Linux/UNIX system troubleshooting assistant. "
                "When suggesting commands, format them in markdown code blocks using ```bash syntax. "
                "Explain what each command does and any potential risks."
            ),
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract text from the response
        if message.content and len(message.content) > 0:
            return message.content[0].text
        return ""
