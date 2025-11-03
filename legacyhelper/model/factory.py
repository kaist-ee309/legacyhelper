"""Model factory for creating different LLM instances."""
import os
from typing import Optional, Dict, Any
from legacyhelper.model.base import BaseModel
from legacyhelper.model.gemini import GeminiModel
from legacyhelper.model.openai import OpenAIModel
from legacyhelper.model.claude import ClaudeModel


class ModelFactory:
    """Factory for creating LLM model instances."""

    # Map of model provider names to their classes
    MODELS = {
        "gemini": GeminiModel,
        "openai": OpenAIModel,
        "claude": ClaudeModel,
    }

    # Default models for each provider
    DEFAULT_MODELS = {
        "gemini": "gemini-2.0-flash-exp",
        "openai": "gpt-4o",
        "claude": "claude-3-5-sonnet-20241022",
    }

    # Environment variable names for API keys
    API_KEY_ENV_VARS = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> BaseModel:
        """Create a model instance.

        Args:
            provider: Model provider ('gemini', 'openai', 'claude')
            api_key: API key (if None, reads from environment)
            model: Specific model name (if None, uses default for provider)
            **kwargs: Additional arguments to pass to the model constructor

        Returns:
            Model instance

        Raises:
            ValueError: If provider is not supported or API key is missing

        Examples:
            >>> # Create Gemini model with default settings
            >>> model = ModelFactory.create('gemini')

            >>> # Create OpenAI model with specific model
            >>> model = ModelFactory.create('openai', model='gpt-4-turbo')

            >>> # Create Claude with custom temperature
            >>> model = ModelFactory.create('claude', temperature=0.5)
        """
        provider = provider.lower()

        if provider not in cls.MODELS:
            available = ", ".join(cls.MODELS.keys())
            raise ValueError(
                f"Unsupported provider: '{provider}'. "
                f"Available providers: {available}"
            )

        # Get the model class
        model_class = cls.MODELS[provider]

        # Use default model if not specified
        if model is None:
            model = cls.DEFAULT_MODELS[provider]

        # Create kwargs for the model
        model_kwargs: Dict[str, Any] = {"api_key": api_key, **kwargs}

        # Add model parameter for providers that support it
        if provider in ["openai", "claude"]:
            model_kwargs["model"] = model
        # Gemini uses the model parameter differently in its constructor
        # so we don't pass it the same way

        return model_class(**model_kwargs)

    @classmethod
    def create_from_env(cls, **kwargs: Any) -> BaseModel:
        """Create a model from environment variables.

        Checks for API keys in this order:
        1. OPENAI_API_KEY -> creates OpenAI model
        2. ANTHROPIC_API_KEY -> creates Claude model
        3. GEMINI_API_KEY -> creates Gemini model

        Args:
            **kwargs: Additional arguments to pass to the model constructor

        Returns:
            Model instance

        Raises:
            ValueError: If no API key is found

        Examples:
            >>> # Will use whichever API key is set
            >>> model = ModelFactory.create_from_env()

            >>> # With custom parameters
            >>> model = ModelFactory.create_from_env(temperature=0.5)
        """
        # Check for API keys in order of preference
        if os.environ.get("OPENAI_API_KEY"):
            return cls.create("openai", **kwargs)
        elif os.environ.get("ANTHROPIC_API_KEY"):
            return cls.create("claude", **kwargs)
        elif os.environ.get("GEMINI_API_KEY"):
            return cls.create("gemini", **kwargs)
        else:
            raise ValueError(
                "No API key found. Set one of the following environment variables:\n"
                "  - OPENAI_API_KEY for OpenAI (GPT-4, GPT-3.5, etc.)\n"
                "  - ANTHROPIC_API_KEY for Claude\n"
                "  - GEMINI_API_KEY for Google Gemini"
            )

    @classmethod
    def list_providers(cls) -> list[str]:
        """Get list of available providers.

        Returns:
            List of provider names
        """
        return list(cls.MODELS.keys())

    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """Get the default model for a provider.

        Args:
            provider: Provider name

        Returns:
            Default model name

        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        if provider not in cls.DEFAULT_MODELS:
            raise ValueError(f"Unsupported provider: '{provider}'")
        return cls.DEFAULT_MODELS[provider]
