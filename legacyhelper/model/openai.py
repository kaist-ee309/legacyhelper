"""OpenAI model implementation."""
import os
from typing import Optional
from openai import OpenAI
from legacyhelper.model.base import BaseModel


class OpenAIModel(BaseModel):
    """OpenAI GPT model implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> None:
        """Initialize OpenAI model.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var
            model: Model name (gpt-4o, gpt-4, gpt-3.5-turbo, etc.)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
        """
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Set it with: export OPENAI_API_KEY='your-key-here'"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_response(self, prompt: str) -> str:
        """Get a response from OpenAI.

        Args:
            prompt: The user's prompt

        Returns:
            The model's response text
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful Linux/UNIX system troubleshooting assistant. "
                    "When suggesting commands, format them in markdown code blocks using ```bash syntax. "
                    "Explain what each command does and any potential risks."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        return response.choices[0].message.content or ""
