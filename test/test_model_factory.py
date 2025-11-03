"""Unit tests for model factory."""
import pytest
import os
from legacyhelper.model.factory import ModelFactory
from legacyhelper.model.base import BaseModel
from legacyhelper.model.gemini import GeminiModel
from legacyhelper.model.openai import OpenAIModel
from legacyhelper.model.claude import ClaudeModel


class TestModelFactory:
    """Test cases for ModelFactory."""

    def test_list_providers(self) -> None:
        """Test listing available providers."""
        providers = ModelFactory.list_providers()

        assert isinstance(providers, list)
        assert len(providers) > 0
        assert "gemini" in providers
        assert "openai" in providers
        assert "claude" in providers

    def test_get_default_model(self) -> None:
        """Test getting default models for providers."""
        gemini_default = ModelFactory.get_default_model("gemini")
        openai_default = ModelFactory.get_default_model("openai")
        claude_default = ModelFactory.get_default_model("claude")

        assert isinstance(gemini_default, str)
        assert isinstance(openai_default, str)
        assert isinstance(claude_default, str)
        assert len(gemini_default) > 0
        assert len(openai_default) > 0
        assert len(claude_default) > 0

    def test_get_default_model_invalid_provider(self) -> None:
        """Test getting default model for invalid provider."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            ModelFactory.get_default_model("invalid_provider")

    def test_create_invalid_provider(self) -> None:
        """Test creating model with invalid provider."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            ModelFactory.create("invalid_provider", api_key="fake-key")

    def test_create_gemini_with_api_key(self) -> None:
        """Test creating Gemini model with API key."""
        model = ModelFactory.create("gemini", api_key="fake-key-for-testing")

        assert isinstance(model, GeminiModel)
        assert isinstance(model, BaseModel)

    def test_create_openai_with_api_key(self) -> None:
        """Test creating OpenAI model with API key."""
        model = ModelFactory.create("openai", api_key="fake-key-for-testing")

        assert isinstance(model, OpenAIModel)
        assert isinstance(model, BaseModel)

    def test_create_claude_with_api_key(self) -> None:
        """Test creating Claude model with API key."""
        model = ModelFactory.create("claude", api_key="fake-key-for-testing")

        assert isinstance(model, ClaudeModel)
        assert isinstance(model, BaseModel)

    def test_create_with_custom_model(self) -> None:
        """Test creating models with custom model names."""
        openai_model = ModelFactory.create(
            "openai",
            api_key="fake-key",
            model="gpt-3.5-turbo"
        )
        assert openai_model.model == "gpt-3.5-turbo"

        claude_model = ModelFactory.create(
            "claude",
            api_key="fake-key",
            model="claude-3-opus-20240229"
        )
        assert claude_model.model == "claude-3-opus-20240229"

    def test_create_with_temperature(self) -> None:
        """Test creating models with custom temperature."""
        model = ModelFactory.create(
            "openai",
            api_key="fake-key",
            temperature=0.5
        )
        assert model.temperature == 0.5

    def test_create_from_env_no_keys(self) -> None:
        """Test create_from_env when no API keys are set."""
        # Save original env vars
        orig_openai = os.environ.get("OPENAI_API_KEY")
        orig_anthropic = os.environ.get("ANTHROPIC_API_KEY")
        orig_gemini = os.environ.get("GEMINI_API_KEY")

        try:
            # Clear all API keys
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
                if key in os.environ:
                    del os.environ[key]

            # Should raise ValueError
            with pytest.raises(ValueError, match="No API key found"):
                ModelFactory.create_from_env()

        finally:
            # Restore original env vars
            if orig_openai:
                os.environ["OPENAI_API_KEY"] = orig_openai
            if orig_anthropic:
                os.environ["ANTHROPIC_API_KEY"] = orig_anthropic
            if orig_gemini:
                os.environ["GEMINI_API_KEY"] = orig_gemini

    def test_create_from_env_with_openai(self) -> None:
        """Test create_from_env prefers OpenAI if key is set."""
        # Save original
        orig = os.environ.get("OPENAI_API_KEY")

        try:
            os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

            model = ModelFactory.create_from_env()

            assert isinstance(model, OpenAIModel)

        finally:
            if orig:
                os.environ["OPENAI_API_KEY"] = orig
            elif "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_api_key_env_vars(self) -> None:
        """Test that API_KEY_ENV_VARS contains correct mappings."""
        assert "gemini" in ModelFactory.API_KEY_ENV_VARS
        assert "openai" in ModelFactory.API_KEY_ENV_VARS
        assert "claude" in ModelFactory.API_KEY_ENV_VARS

        assert ModelFactory.API_KEY_ENV_VARS["gemini"] == "GEMINI_API_KEY"
        assert ModelFactory.API_KEY_ENV_VARS["openai"] == "OPENAI_API_KEY"
        assert ModelFactory.API_KEY_ENV_VARS["claude"] == "ANTHROPIC_API_KEY"

    def test_case_insensitive_provider(self) -> None:
        """Test that provider names are case-insensitive."""
        model1 = ModelFactory.create("OPENAI", api_key="fake-key")
        model2 = ModelFactory.create("OpenAI", api_key="fake-key")
        model3 = ModelFactory.create("openai", api_key="fake-key")

        assert isinstance(model1, OpenAIModel)
        assert isinstance(model2, OpenAIModel)
        assert isinstance(model3, OpenAIModel)
