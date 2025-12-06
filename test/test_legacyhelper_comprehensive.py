"""Comprehensive pytest test suite for the entire legacyhelper module."""
import pytest
import os
from unittest.mock import patch, mock_open, MagicMock, Mock
from pathlib import Path
from typing import Optional

# Import all modules to test
from legacyhelper.core.agent import Agent
from legacyhelper.core.history_reader import (
    get_shell_history_path,
    filter_sensitive_data,
    read_recent_history,
    format_history_context
)
from legacyhelper.core.command_parser import CommandParser, ParsedCommand
from legacyhelper.core.executor import CommandExecutor, InteractiveExecutor, ExecutionResult
from legacyhelper.model.base import BaseModel
from legacyhelper.model.gemini import GeminiModel
from legacyhelper.model.openai import OpenAIModel
from legacyhelper.model.claude import ClaudeModel
from legacyhelper.model.factory import ModelFactory


# ============================================================================
# Core Module Tests: Agent
# ============================================================================

class TestAgent:
    """Comprehensive tests for Agent class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_model = MagicMock(spec=BaseModel)
        self.mock_model.get_response.return_value = "Test response"

    @patch('legacyhelper.core.agent.GeminiModel')
    def test_agent_init_without_model(self, mock_gemini):
        """Test Agent initialization without providing a model."""
        mock_gemini_instance = MagicMock()
        mock_gemini.return_value = mock_gemini_instance

        agent = Agent()

        assert agent.model == mock_gemini_instance
        assert agent.conversation_history == []
        assert agent.console is not None

    def test_agent_init_with_model(self):
        """Test Agent initialization with a provided model."""
        agent = Agent(model=self.mock_model)

        assert agent.model == self.mock_model
        assert agent.conversation_history == []

    @patch('legacyhelper.core.history_reader.read_recent_history')
    @patch('legacyhelper.core.history_reader.format_history_context')
    def test_get_response_with_history(self, mock_format, mock_read):
        """Test get_response includes history context."""
        mock_read.return_value = ["ls -la", "cd /home"]
        mock_format.return_value = "Recent shell history:\n1. ls -la\n2. cd /home"
        self.mock_model.get_response.return_value = "Response with history"

        agent = Agent(model=self.mock_model)
        result = agent.get_response("test prompt")

        assert result == "Response with history"
        mock_read.assert_called_once_with(count=10)
        # Verify the model was called with enhanced prompt
        call_args = self.mock_model.get_response.call_args[0][0]
        assert "Recent shell history" in call_args
        assert "test prompt" in call_args

    @patch('legacyhelper.core.history_reader.read_recent_history')
    def test_get_response_without_history(self, mock_read):
        """Test get_response when no history is available."""
        mock_read.return_value = []
        self.mock_model.get_response.return_value = "Response without history"

        agent = Agent(model=self.mock_model)
        result = agent.get_response("test prompt")

        assert result == "Response without history"
        # Should call model with original prompt when no history
        self.mock_model.get_response.assert_called_once_with("test prompt")

    def test_add_to_history(self):
        """Test adding messages to conversation history."""
        agent = Agent(model=self.mock_model)

        agent.add_to_history("user", "Hello")
        agent.add_to_history("assistant", "Hi there")

        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0] == {"role": "user", "content": "Hello"}
        assert agent.conversation_history[1] == {"role": "assistant", "content": "Hi there"}

    @patch('legacyhelper.core.agent.Prompt')
    @patch('legacyhelper.core.agent.Console')
    def test_run_method(self, mock_console_class, mock_prompt):
        """Test the run method (legacy CLI mode)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_prompt.ask.return_value = "n"

        agent = Agent(model=self.mock_model)
        result = agent.run("test prompt")

        assert result == "Test response"
        mock_console.print.assert_called()
        mock_prompt.ask.assert_called_once()


# ============================================================================
# Core Module Tests: History Reader
# ============================================================================

class TestHistoryReader:
    """Comprehensive tests for history_reader module."""

    @patch('legacyhelper.core.history_reader.Path.home')
    @patch.dict('os.environ', {'SHELL': '/bin/zsh'})
    def test_get_shell_history_path_zsh(self, mock_home):
        """Test getting zsh history path."""
        mock_home_dir = MagicMock()
        mock_home.return_value = mock_home_dir
        mock_history = MagicMock()
        mock_history.exists.return_value = True
        mock_home_dir.__truediv__ = MagicMock(return_value=mock_history)

        result = get_shell_history_path()

        assert result == mock_history

    def test_filter_sensitive_data_api_key(self):
        """Test filtering API keys."""
        entry = 'export API_KEY=sk-1234567890abcdef'
        result = filter_sensitive_data(entry)
        assert 'API_KEY=***REDACTED***' in result
        assert 'sk-1234567890abcdef' not in result

    def test_filter_sensitive_data_password(self):
        """Test filtering passwords."""
        entry = 'export PASSWORD="mypassword123"'
        result = filter_sensitive_data(entry)
        assert 'PASSWORD=***REDACTED***' in result
        assert 'mypassword123' not in result

    def test_filter_sensitive_data_url_credentials(self):
        """Test filtering URL credentials."""
        entry = 'git clone https://user:pass@github.com/repo.git'
        result = filter_sensitive_data(entry)
        assert 'https://***REDACTED***@github.com' in result
        assert 'user:pass' not in result

    def test_filter_sensitive_data_preserves_normal_commands(self):
        """Test that normal commands are preserved."""
        entry = 'ls -la /home/user'
        result = filter_sensitive_data(entry)
        assert result == entry

    @patch('legacyhelper.core.history_reader.get_shell_history_path')
    def test_read_recent_history(self, mock_get_path):
        """Test reading recent history."""
        mock_path = MagicMock()
        mock_get_path.return_value = mock_path
        history_data = "ls -la\ncd /home\necho hello\n"

        with patch('builtins.open', mock_open(read_data=history_data)):
            result = read_recent_history(count=3)

        assert len(result) == 3
        assert 'ls -la' in result

    def test_format_history_context(self):
        """Test formatting history context."""
        history = ["ls -la", "cd /home"]
        result = format_history_context(history)

        assert "Recent shell history" in result
        assert "1. ls -la" in result
        assert "2. cd /home" in result

    def test_format_history_context_empty(self):
        """Test formatting empty history."""
        result = format_history_context([])
        assert result == ""


# ============================================================================
# Core Module Tests: Command Parser
# ============================================================================

class TestCommandParserComprehensive:
    """Comprehensive tests for CommandParser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_extract_commands_from_code_block(self):
        """Test extracting commands from markdown code blocks."""
        text = "```bash\ndf -h\n```"
        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert any("df -h" in cmd.command for cmd in commands)

    def test_extract_commands_from_inline_code(self):
        """Test extracting commands from inline code."""
        text = "Use `ls -la` to list files."
        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert any("ls" in cmd.command for cmd in commands)

    def test_dangerous_command_detection(self):
        """Test detection of dangerous commands."""
        text = "```bash\nrm -rf /\n```"
        commands = self.parser.extract_commands(text)

        assert len(commands) > 0
        assert not commands[0].is_safe
        assert len(commands[0].warnings) > 0

    def test_get_best_command(self):
        """Test getting the best command from text."""
        text = "You can use `ls` or ```bash\ndf -h\n```"
        best = self.parser.get_best_command(text)

        assert best is not None
        assert best.command == "df -h"


# ============================================================================
# Core Module Tests: Command Executor
# ============================================================================

class TestCommandExecutorComprehensive:
    """Comprehensive tests for CommandExecutor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.executor = CommandExecutor(timeout=5)

    def test_execute_simple_command(self):
        """Test executing a simple command."""
        result = self.executor.execute("echo 'test'")

        assert result.success
        assert result.exit_code == 0
        assert "test" in result.stdout

    def test_execute_failing_command(self):
        """Test executing a command that fails."""
        result = self.executor.execute("ls /nonexistent_directory_xyz123")

        assert not result.success
        assert result.exit_code != 0

    def test_can_execute_valid_command(self):
        """Test can_execute for valid commands."""
        can_exec, reason = self.executor.can_execute("ls")

        assert can_exec
        assert reason is None

    def test_can_execute_invalid_command(self):
        """Test can_execute for invalid commands."""
        can_exec, reason = self.executor.can_execute("nonexistent_cmd_xyz123")

        assert not can_exec
        assert reason is not None


class TestInteractiveExecutorComprehensive:
    """Comprehensive tests for InteractiveExecutor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.base_executor = CommandExecutor(timeout=5)
        self.executor = InteractiveExecutor(self.base_executor)

    def test_requires_confirmation_for_sudo(self):
        """Test that sudo commands require confirmation."""
        requires, reason = self.executor.requires_confirmation("sudo apt update")

        assert requires
        assert "privilege" in reason.lower()

    def test_requires_confirmation_for_rm(self):
        """Test that rm commands require confirmation."""
        requires, reason = self.executor.requires_confirmation("rm file.txt")

        assert requires
        assert "delete" in reason.lower()

    def test_no_confirmation_for_safe_commands(self):
        """Test that safe commands don't require confirmation."""
        requires, reason = self.executor.requires_confirmation("ls -la")

        assert not requires

    def test_execute_with_confirmation(self):
        """Test executing with confirmation."""
        result = self.executor.execute_with_confirmation(
            "echo 'test'",
            confirmed=True
        )

        assert result.success
        assert "test" in result.stdout


# ============================================================================
# Model Module Tests: Base Model
# ============================================================================

class TestBaseModel:
    """Tests for BaseModel abstract class."""

    def test_base_model_is_abstract(self):
        """Test that BaseModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseModel()  # type: ignore

    def test_base_model_has_abstract_method(self):
        """Test that BaseModel defines abstract get_response method."""
        assert hasattr(BaseModel, 'get_response')
        assert getattr(BaseModel.get_response, '__isabstractmethod__', False)


# ============================================================================
# Model Module Tests: Gemini Model
# ============================================================================

class TestGeminiModel:
    """Comprehensive tests for GeminiModel."""

    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
    @patch('legacyhelper.model.gemini.genai')
    def test_gemini_init_with_env_key(self, mock_genai):
        """Test GeminiModel initialization with environment key."""
        mock_genai.configure = MagicMock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel = MagicMock(return_value=mock_model)

        model = GeminiModel()

        assert model.model == mock_model
        mock_genai.configure.assert_called_once_with(api_key='test-key')

    def test_gemini_init_with_api_key(self):
        """Test GeminiModel initialization with provided API key."""
        with patch('legacyhelper.model.gemini.genai') as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)

            model = GeminiModel(api_key="provided-key")

            assert model.model == mock_model
            mock_genai.configure.assert_called_once_with(api_key="provided-key")

    @patch.dict('os.environ', {}, clear=True)
    def test_gemini_init_without_key(self):
        """Test GeminiModel initialization without API key raises error."""
        with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
            GeminiModel()

    @patch('legacyhelper.model.gemini.genai')
    def test_gemini_get_response(self, mock_genai):
        """Test GeminiModel get_response method."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
        mock_genai.configure = MagicMock()

        model = GeminiModel(api_key="test-key")
        result = model.get_response("test prompt")

        assert result == "Test response"
        mock_model.generate_content.assert_called_once_with("test prompt")


# ============================================================================
# Model Module Tests: OpenAI Model
# ============================================================================

class TestOpenAIModel:
    """Comprehensive tests for OpenAIModel."""

    @patch('legacyhelper.model.openai.OpenAI')
    def test_openai_init_with_api_key(self, mock_openai_class):
        """Test OpenAIModel initialization with API key."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        model = OpenAIModel(api_key="test-key")

        assert model.client == mock_client
        assert model.model == "gpt-4o"
        assert model.temperature == 0.7

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'})
    @patch('legacyhelper.model.openai.OpenAI')
    def test_openai_init_with_env_key(self, mock_openai_class):
        """Test OpenAIModel initialization with environment key."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        model = OpenAIModel()

        assert model.client == mock_client
        mock_openai_class.assert_called_once_with(api_key='env-key')

    @patch.dict('os.environ', {}, clear=True)
    def test_openai_init_without_key(self):
        """Test OpenAIModel initialization without API key raises error."""
        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            OpenAIModel()

    @patch('legacyhelper.model.openai.OpenAI')
    def test_openai_get_response(self, mock_openai_class):
        """Test OpenAIModel get_response method."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Test response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        model = OpenAIModel(api_key="test-key")
        result = model.get_response("test prompt")

        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once()


# ============================================================================
# Model Module Tests: Claude Model
# ============================================================================

class TestClaudeModel:
    """Comprehensive tests for ClaudeModel."""

    @patch('legacyhelper.model.claude.Anthropic')
    def test_claude_init_with_api_key(self, mock_anthropic_class):
        """Test ClaudeModel initialization with API key."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        model = ClaudeModel(api_key="test-key")

        assert model.client == mock_client
        assert model.model == "claude-3-5-sonnet-20241022"
        assert model.temperature == 0.7

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'})
    @patch('legacyhelper.model.claude.Anthropic')
    def test_claude_init_with_env_key(self, mock_anthropic_class):
        """Test ClaudeModel initialization with environment key."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        model = ClaudeModel()

        assert model.client == mock_client
        mock_anthropic_class.assert_called_once_with(api_key='env-key')

    @patch.dict('os.environ', {}, clear=True)
    def test_claude_init_without_key(self):
        """Test ClaudeModel initialization without API key raises error."""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            ClaudeModel()

    @patch('legacyhelper.model.claude.Anthropic')
    def test_claude_get_response(self, mock_anthropic_class):
        """Test ClaudeModel get_response method."""
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Test response"
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        model = ClaudeModel(api_key="test-key")
        result = model.get_response("test prompt")

        assert result == "Test response"
        mock_client.messages.create.assert_called_once()


# ============================================================================
# Model Module Tests: Model Factory
# ============================================================================

class TestModelFactoryComprehensive:
    """Comprehensive tests for ModelFactory."""

    def test_list_providers(self):
        """Test listing available providers."""
        providers = ModelFactory.list_providers()

        assert isinstance(providers, list)
        assert len(providers) >= 3
        assert "gemini" in providers
        assert "openai" in providers
        assert "claude" in providers

    def test_get_default_model(self):
        """Test getting default models."""
        gemini_default = ModelFactory.get_default_model("gemini")
        openai_default = ModelFactory.get_default_model("openai")
        claude_default = ModelFactory.get_default_model("claude")

        assert isinstance(gemini_default, str)
        assert len(gemini_default) > 0

    def test_create_gemini_model(self):
        """Test creating Gemini model."""
        with patch('legacyhelper.model.gemini.genai') as mock_genai:
            mock_genai.configure = MagicMock()
            mock_model = MagicMock()
            mock_genai.GenerativeModel = MagicMock(return_value=mock_model)

            model = ModelFactory.create("gemini", api_key="test-key")

            assert isinstance(model, GeminiModel)

    def test_create_openai_model(self):
        """Test creating OpenAI model."""
        with patch('legacyhelper.model.openai.OpenAI'):
            model = ModelFactory.create("openai", api_key="test-key")

            assert isinstance(model, OpenAIModel)

    def test_create_claude_model(self):
        """Test creating Claude model."""
        with patch('legacyhelper.model.claude.Anthropic'):
            model = ModelFactory.create("claude", api_key="test-key")

            assert isinstance(model, ClaudeModel)

    def test_create_invalid_provider(self):
        """Test creating model with invalid provider."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            ModelFactory.create("invalid_provider", api_key="test-key")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for multiple modules working together."""

    def test_agent_with_history_and_model(self):
        """Test Agent using history reader and model together."""
        mock_model = MagicMock(spec=BaseModel)
        mock_model.get_response.return_value = "Response"

        with patch('legacyhelper.core.history_reader.read_recent_history') as mock_read:
            mock_read.return_value = ["ls -la", "cd /home"]

            agent = Agent(model=mock_model)
            result = agent.get_response("test")

            assert result == "Response"
            # Verify history was included
            call_args = mock_model.get_response.call_args[0][0]
            assert "Recent shell history" in call_args

    def test_command_parser_with_executor(self):
        """Test CommandParser and CommandExecutor integration."""
        parser = CommandParser()
        executor = CommandExecutor(timeout=5)

        text = "```bash\necho 'test'\n```"
        commands = parser.extract_commands(text)

        assert len(commands) > 0
        best = parser.get_best_command(text)
        assert best is not None

        # Execute the command
        result = executor.execute(best.command)
        assert result.success
        assert "test" in result.stdout


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
