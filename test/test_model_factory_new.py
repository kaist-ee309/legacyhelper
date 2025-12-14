"""Unit tests for ModelFactory."""
import pytest
import os
from unittest.mock import patch
from legacyhelper.model.factory import ModelFactory


class TestModelFactoryCreate:
    """Test cases for ModelFactory.create method."""

    def test_create_with_unsupported_provider(self):
        """Test creating a model with unsupported provider raises error."""
        with pytest.raises(ValueError) as exc_info:
            ModelFactory.create('unsupported_provider', api_key='test')

        assert "Unsupported provider" in str(exc_info.value)
        assert "Available providers" in str(exc_info.value)

    def test_create_provider_case_insensitive(self):
        """Test that provider name is case-insensitive."""
        # Test that uppercase provider names are converted to lowercase and work
        # The provider validation should accept uppercase names
        # Since we can't actually create models without valid APIs, we verify
        # that the lowercase conversion happens by testing the create method accepts it
        from unittest.mock import patch, MagicMock

        # Mock the provider and model classes
        with patch('legacyhelper.model.factory.GoogleProvider') as mock_provider:
            with patch('legacyhelper.model.factory.GoogleModel') as mock_model:
                # This should not raise ValueError for provider validation
                try:
                    ModelFactory.create('GEMINI', api_key='test_key')
                except TypeError:
                    # Expected - mock objects don't behave like real models
                    pass
                except ValueError as e:
                    # Should not be ValueError about unsupported provider
                    if "Unsupported provider" in str(e):
                        pytest.fail(f"Provider validation failed: {e}")

    def test_create_known_providers(self):
        """Test that all known providers are available."""
        providers = ModelFactory.list_providers()

        assert 'gemini' in providers
        assert 'openai' in providers
        assert 'claude' in providers
        assert len(providers) == 3

    def test_create_validates_provider_parameter(self):
        """Test that invalid provider names are rejected."""
        invalid_providers = ['gpt', 'deepseek', 'invalid', '']

        for provider in invalid_providers:
            with pytest.raises(ValueError):
                ModelFactory.create(provider, api_key='test')

    def test_create_provider_parameter_validation(self):
        """Test that provider parameter is validated correctly."""
        # Test that various invalid inputs raise ValueError
        test_cases = [
            'xyz',
            'anthropic',  # Should be 'claude'
            'google',      # Should be 'gemini'
            'gpt-4',       # Should be 'openai'
        ]

        for invalid in test_cases:
            with pytest.raises(ValueError):
                ModelFactory.create(invalid, api_key='test_key')


class TestModelFactoryCreateFromEnv:
    """Test cases for ModelFactory.create_from_env method."""

    def test_create_from_env_openai_priority(self):
        """Test that OPENAI_API_KEY has highest priority."""
        # Set all three API keys
        env = {
            'OPENAI_API_KEY': 'openai_key',
            'ANTHROPIC_API_KEY': 'anthropic_key',
            'GEMINI_API_KEY': 'gemini_key',
        }
        with patch.dict(os.environ, env, clear=False):
            with patch.object(ModelFactory, 'create') as mock_create:
                ModelFactory.create_from_env()
                # OpenAI should be selected first
                assert mock_create.call_args[0][0] == 'openai'

    def test_create_from_env_anthropic_second_priority(self):
        """Test that ANTHROPIC_API_KEY is second priority."""
        # Set only ANTHROPIC and GEMINI
        env = {
            'ANTHROPIC_API_KEY': 'anthropic_key',
            'GEMINI_API_KEY': 'gemini_key',
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(ModelFactory, 'create') as mock_create:
                ModelFactory.create_from_env()
                # Anthropic should be selected
                assert mock_create.call_args[0][0] == 'claude'

    def test_create_from_env_gemini_third_priority(self):
        """Test that GEMINI_API_KEY is third priority."""
        # Set only GEMINI
        env = {'GEMINI_API_KEY': 'gemini_key'}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(ModelFactory, 'create') as mock_create:
                ModelFactory.create_from_env()
                # Gemini should be selected
                assert mock_create.call_args[0][0] == 'gemini'

    def test_create_from_env_no_api_key(self):
        """Test error when no API key is found."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ModelFactory.create_from_env()

            error_msg = str(exc_info.value)
            assert "No API key found" in error_msg
            assert "OPENAI_API_KEY" in error_msg
            assert "ANTHROPIC_API_KEY" in error_msg
            assert "GEMINI_API_KEY" in error_msg

    def test_create_from_env_with_kwargs(self):
        """Test passing additional kwargs to create_from_env."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}, clear=False):
            with patch.object(ModelFactory, 'create') as mock_create:
                ModelFactory.create_from_env(temperature=0.5, max_tokens=100)

                # kwargs should be passed to create
                assert 'temperature' in mock_create.call_args[1]
                assert mock_create.call_args[1]['temperature'] == 0.5
                assert mock_create.call_args[1]['max_tokens'] == 100

    def test_create_from_env_single_api_key_present(self):
        """Test with only one API key present."""
        for api_key_env, provider in [
            ('OPENAI_API_KEY', 'openai'),
            ('ANTHROPIC_API_KEY', 'claude'),
            ('GEMINI_API_KEY', 'gemini'),
        ]:
            with patch.dict(os.environ, {api_key_env: 'test_key'}, clear=True):
                with patch.object(ModelFactory, 'create') as mock_create:
                    ModelFactory.create_from_env()
                    assert mock_create.call_args[0][0] == provider


class TestModelFactoryUtilities:
    """Test cases for ModelFactory utility methods."""

    def test_list_providers(self):
        """Test listing available providers."""
        providers = ModelFactory.list_providers()

        assert isinstance(providers, list)
        assert 'gemini' in providers
        assert 'openai' in providers
        assert 'claude' in providers
        assert len(providers) == 3

    def test_get_default_model_gemini(self):
        """Test getting default model for Gemini."""
        model = ModelFactory.get_default_model('gemini')

        assert isinstance(model, str)
        assert model == 'gemini-2.5-flash'

    def test_get_default_model_openai(self):
        """Test getting default model for OpenAI."""
        model = ModelFactory.get_default_model('openai')

        assert isinstance(model, str)
        assert model == 'gpt-4o'

    def test_get_default_model_claude(self):
        """Test getting default model for Claude."""
        model = ModelFactory.get_default_model('claude')

        assert isinstance(model, str)
        assert model == 'claude-haiku-4-5'

    def test_get_default_model_case_insensitive(self):
        """Test that get_default_model is case-insensitive."""
        model_lower = ModelFactory.get_default_model('gemini')
        model_upper = ModelFactory.get_default_model('GEMINI')
        model_mixed = ModelFactory.get_default_model('GeMinI')

        assert model_lower == model_upper == model_mixed
        assert model_lower == 'gemini-2.5-flash'

    def test_get_default_model_all_providers(self):
        """Test getting default model for all providers."""
        providers = ModelFactory.list_providers()

        for provider in providers:
            model = ModelFactory.get_default_model(provider)
            assert isinstance(model, str)
            assert len(model) > 0

    def test_get_default_model_unsupported_provider(self):
        """Test error for unsupported provider."""
        with pytest.raises(ValueError) as exc_info:
            ModelFactory.get_default_model('unsupported')

        assert "Unsupported provider" in str(exc_info.value)

    def test_default_models_are_strings(self):
        """Test that all default models are non-empty strings."""
        for provider in ModelFactory.list_providers():
            default_model = ModelFactory.get_default_model(provider)
            assert isinstance(default_model, str)
            assert len(default_model) > 0
            assert '-' in default_model or '.' in default_model  # All models have version indicators


class TestModelFactoryIntegration:
    """Integration tests for ModelFactory."""

    def test_model_factory_class_attributes(self):
        """Test that ModelFactory has expected class attributes."""
        assert hasattr(ModelFactory, 'MODELS')
        assert hasattr(ModelFactory, 'PROVIDER')
        assert hasattr(ModelFactory, 'DEFAULT_MODELS')
        assert hasattr(ModelFactory, 'API_KEY_ENV_VARS')

    def test_model_factory_class_attributes_consistency(self):
        """Test that class attributes are consistent."""
        models = ModelFactory.MODELS
        providers = ModelFactory.PROVIDER
        defaults = ModelFactory.DEFAULT_MODELS
        env_vars = ModelFactory.API_KEY_ENV_VARS

        # All should have the same keys
        assert set(models.keys()) == set(providers.keys()) == set(defaults.keys()) == set(env_vars.keys())

    def test_api_key_env_var_mapping(self):
        """Test API key environment variable mappings."""
        mapping = ModelFactory.API_KEY_ENV_VARS

        assert mapping['gemini'] == 'GEMINI_API_KEY'
        assert mapping['openai'] == 'OPENAI_API_KEY'
        assert mapping['claude'] == 'ANTHROPIC_API_KEY'
