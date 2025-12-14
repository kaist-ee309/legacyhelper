"""Unit tests for Pydantic AI Agent using TestModel and FunctionModel.

This module tests the LegacyHelper agent with proper Pydantic AI testing patterns:
- TestModel for basic agent exercise without real LLM calls
- FunctionModel for custom tool invocation behavior
- Agent.override for replacing model in tests
- capture_run_messages for inspecting agent conversations
- ALLOW_MODEL_REQUESTS=False to block accidental LLM calls

Reference: https://ai.pydantic.dev/testing/
"""
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pytest fixtures needed. disable some linter warnings.
import re
from datetime import timezone
from typing import List
from unittest.mock import patch, MagicMock

import pytest
from dirty_equals import IsNow

from pydantic_ai import Agent, models, capture_run_messages
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai import ModelMessage

from legacyhelper.tools.command_tool import bash_tool, SYSTEM_LOG_TOOLSET
from system_prompt import SYSTEM

# Block all real model requests - safety measure
models.ALLOW_MODEL_REQUESTS = False


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def legacy_agent():
    """Create a fresh LegacyHelper agent for testing."""
    return Agent(
        model="test",  # Will be overridden
        tools=[bash_tool],
        toolsets=[SYSTEM_LOG_TOOLSET],
        system_prompt=SYSTEM,
    )


@pytest.fixture
def simple_agent():
    """Create a simple agent with just the bash tool for focused testing."""
    return Agent(
        model="test",
        tools=[bash_tool],
        system_prompt="You are a Linux system helper. Use bash tool to run commands.",
    )


@pytest.fixture
def mock_subprocess_popen():
    """Mock subprocess.Popen for safe bash tool testing."""
    with patch('legacyhelper.tools.command_tool.subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('command output', '')
        mock_process.returncode = 0
        mock_popen.return_value.__enter__.return_value = mock_process
        yield mock_popen


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for system log tools."""
    with patch('legacyhelper.tools.command_tool.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='log output')
        yield mock_run


# ============================================================================
# TestModel Tests - Basic Agent Exercise
# ============================================================================


class TestAgentWithTestModel:
    """Tests using TestModel for basic agent behavior."""

    async def test_agent_responds_with_text(self, simple_agent, mock_subprocess_popen):
        """Test that agent produces a text response using TestModel."""
        with simple_agent.override(model=TestModel()):
            result = await simple_agent.run("What is the current directory?")

            # TestModel returns JSON summary of tool calls
            assert result.output is not None
            assert isinstance(result.output, str)

    async def test_agent_calls_bash_tool(self, simple_agent, mock_subprocess_popen):
        """Test that TestModel calls the bash tool."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("List files in current directory")

        # Verify tool was called
        tool_calls = [
            msg for msg in messages
            if isinstance(msg, ModelResponse)
            and any(isinstance(p, ToolCallPart) for p in msg.parts)
        ]
        assert len(tool_calls) >= 1

        # Find bash tool call
        bash_called = False
        for msg in messages:
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart) and part.tool_name == 'bash':
                        bash_called = True
                        break
        assert bash_called, "Bash tool should have been called"

    async def test_agent_message_structure(self, simple_agent, mock_subprocess_popen):
        """Test that agent messages have correct structure."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("Hello")

        # First message should be a ModelRequest with system and user prompts
        assert len(messages) >= 1
        first_msg = messages[0]
        assert isinstance(first_msg, ModelRequest)

        # Check for system prompt
        system_parts = [p for p in first_msg.parts if isinstance(p, SystemPromptPart)]
        assert len(system_parts) >= 1

        # Check for user prompt
        user_parts = [p for p in first_msg.parts if isinstance(p, UserPromptPart)]
        assert len(user_parts) >= 1
        assert "Hello" in user_parts[0].content

    async def test_agent_with_custom_output_text(
        self, simple_agent, mock_subprocess_popen
    ):
        """Test TestModel with custom output text."""
        custom_response = "Files listed successfully: file1.txt, file2.py"

        with simple_agent.override(model=TestModel(custom_output_text=custom_response)):
            result = await simple_agent.run("List files")

        assert result.output == custom_response

    async def test_agent_tool_return_captured(self, simple_agent, mock_subprocess_popen):
        """Test that tool return values are captured in messages."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("Run pwd command")

        # Find tool return parts
        tool_returns = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_returns.append(part)

        # TestModel should have triggered tool execution
        assert len(tool_returns) >= 1

    async def test_full_agent_with_all_tools(
        self, legacy_agent, mock_subprocess_popen, mock_subprocess_run
    ):
        """Test the full LegacyHelper agent with all tools available."""
        with capture_run_messages() as messages:
            with legacy_agent.override(model=TestModel()):
                result = await legacy_agent.run("Check system status")

        assert result.output is not None

        # Verify messages were captured
        assert len(messages) >= 2  # At least request and response


class TestAgentWithTestModelMessageValidation:
    """Tests validating message content with TestModel."""

    async def test_message_timestamps(self, simple_agent, mock_subprocess_popen):
        """Test that messages have valid timestamps."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("test")

        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if hasattr(part, 'timestamp'):
                        assert part.timestamp == IsNow(tz=timezone.utc)
            elif isinstance(msg, ModelResponse):
                assert msg.timestamp == IsNow(tz=timezone.utc)

    async def test_message_run_ids(self, simple_agent, mock_subprocess_popen):
        """Test that messages are properly structured with model name."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("test")

        # Verify messages are present
        assert len(messages) >= 2

        # Verify model responses have model name
        model_responses = [m for m in messages if isinstance(m, ModelResponse)]
        assert len(model_responses) >= 1
        for response in model_responses:
            assert response.model_name == 'test'

    async def test_model_name_in_response(self, simple_agent, mock_subprocess_popen):
        """Test that model name is correctly set in response."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("test")

        model_responses = [m for m in messages if isinstance(m, ModelResponse)]
        for response in model_responses:
            assert response.model_name == 'test'


# ============================================================================
# FunctionModel Tests - Custom Tool Behavior
# ============================================================================


class TestAgentWithFunctionModel:
    """Tests using FunctionModel for custom tool invocation."""

    async def test_function_model_calls_specific_command(
        self, simple_agent, mock_subprocess_popen
    ):
        """Test FunctionModel calling bash with a specific command."""
        def call_ls_command(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                # First call - invoke bash tool with ls command
                args = {'command': 'ls -la'}
                return ModelResponse(parts=[ToolCallPart('bash', args)])
            # Second call - return final response
            return ModelResponse(parts=[TextPart('Listed files successfully')])

        with capture_run_messages() as messages:
            with simple_agent.override(model=FunctionModel(call_ls_command)):
                result = await simple_agent.run("List files")

        assert result.output == 'Listed files successfully'

        # Verify bash was called with ls -la
        tool_calls = []
        for msg in messages:
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        tool_calls.append(part)

        assert len(tool_calls) >= 1
        assert tool_calls[0].args.get('command') == 'ls -la'

    async def test_function_model_extracts_from_prompt(
        self, simple_agent, mock_subprocess_popen
    ):
        """Test FunctionModel extracting command from user prompt."""
        def extract_command_from_prompt(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                # Extract command from user prompt
                user_prompt = messages[0].parts[-1]
                if hasattr(user_prompt, 'content'):
                    # Look for backticks in the prompt
                    match = re.search(r'`([^`]+)`', user_prompt.content)
                    if match:
                        cmd = match.group(1)
                    else:
                        cmd = 'echo "No command found"'
                else:
                    cmd = 'echo "No content"'
                args = {'command': cmd}
                return ModelResponse(parts=[ToolCallPart('bash', args)])
            tool_return = messages[-1].parts[0]
            if hasattr(tool_return, 'content'):
                return ModelResponse(
                    parts=[TextPart(f'Command result: {tool_return.content}')]
                )
            return ModelResponse(parts=[TextPart('Command executed')])

        with simple_agent.override(model=FunctionModel(extract_command_from_prompt)):
            result = await simple_agent.run("Please run `pwd` for me")

        assert 'Command result:' in result.output or 'Command executed' in result.output

    async def test_function_model_handles_dangerous_commands(self, simple_agent):
        """Test that dangerous commands are blocked even with FunctionModel."""
        def try_dangerous_command(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                # Try to run a dangerous command
                args = {'command': 'rm -rf /'}
                return ModelResponse(parts=[ToolCallPart('bash', args)])
            tool_return = messages[-1].parts[0]
            return ModelResponse(
                parts=[TextPart(f'Result: {tool_return.content}')]
            )

        with capture_run_messages() as messages:
            with simple_agent.override(model=FunctionModel(try_dangerous_command)):
                await simple_agent.run("Delete everything")

        # Verify the command was blocked
        tool_returns = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_returns.append(part)

        # BashResult should contain blocked message
        assert any('Blocked dangerous command' in str(tr.content) for tr in tool_returns)

    async def test_function_model_multi_tool_sequence(
        self, legacy_agent, mock_subprocess_popen, mock_subprocess_run
    ):
        """Test FunctionModel with multiple tool calls in sequence."""
        call_count = [0]

        def multi_tool_workflow(
            _messages: List[ModelMessage], _info: AgentInfo
        ) -> ModelResponse:
            call_count[0] += 1

            if call_count[0] == 1:
                # First: get system log
                return ModelResponse(
                    parts=[ToolCallPart('get_current_system_log', {})]
                )
            if call_count[0] == 2:
                # Second: run a diagnostic command
                return ModelResponse(
                    parts=[ToolCallPart('bash', {'command': 'uname -a'})]
                )
            # Final response
            return ModelResponse(
                parts=[TextPart('System diagnostics complete')]
            )

        with legacy_agent.override(model=FunctionModel(multi_tool_workflow)):
            result = await legacy_agent.run("Diagnose system issues")

        assert result.output == 'System diagnostics complete'
        assert call_count[0] == 3  # Two tool calls + final response


class TestFunctionModelEdgeCases:
    """Edge case tests with FunctionModel."""

    async def test_function_model_no_tool_calls(self, simple_agent):
        """Test FunctionModel that returns text without calling tools."""
        def direct_response(
            _messages: List[ModelMessage], _info: AgentInfo
        ) -> ModelResponse:
            return ModelResponse(
                parts=[TextPart('I can help you with Linux commands.')]
            )

        with simple_agent.override(model=FunctionModel(direct_response)):
            result = await simple_agent.run("What can you do?")

        assert result.output == 'I can help you with Linux commands.'

    async def test_function_model_with_tool_info(
        self, simple_agent, mock_subprocess_popen
    ):
        """Test that FunctionModel receives correct AgentInfo."""
        received_info = [None]

        def capture_info(
            _messages: List[ModelMessage], info: AgentInfo
        ) -> ModelResponse:
            received_info[0] = info
            return ModelResponse(parts=[TextPart('Done')])

        with simple_agent.override(model=FunctionModel(capture_info)):
            await simple_agent.run("test")

        assert received_info[0] is not None
        # AgentInfo should have function_tools attribute
        assert hasattr(received_info[0], 'function_tools')

    async def test_function_model_sudo_blocked(self, simple_agent):
        """Test that sudo commands are blocked via FunctionModel."""
        def try_sudo(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                args = {'command': 'sudo apt update'}
                return ModelResponse(parts=[ToolCallPart('bash', args)])
            tool_return = messages[-1].parts[0]
            return ModelResponse(
                parts=[TextPart(f'Result: {tool_return.content}')]
            )

        with simple_agent.override(model=FunctionModel(try_sudo)):
            result = await simple_agent.run("Update system")

        # Verify sudo was rejected
        assert 'superuser' in result.output.lower() or 'abort' in result.output.lower()


# ============================================================================
# Agent.override Tests
# ============================================================================


class TestAgentOverride:
    """Tests for Agent.override functionality."""

    async def test_override_context_manager(self, simple_agent, mock_subprocess_popen):
        """Test that override works as context manager."""
        # Before override - model is 'test' (placeholder)
        original_model = simple_agent.model

        with simple_agent.override(model=TestModel()):
            result = await simple_agent.run("test")
            assert result.output is not None

        # After override - model should be restored
        # (The original was 'test' string, not an actual model)
        assert simple_agent.model == original_model

    async def test_override_with_custom_text(self, simple_agent):
        """Test override with custom output text."""
        response1 = "Response 1"
        response2 = "Response 2"

        with simple_agent.override(model=TestModel(custom_output_text=response1)):
            result1 = await simple_agent.run("query 1")

        with simple_agent.override(model=TestModel(custom_output_text=response2)):
            result2 = await simple_agent.run("query 2")

        assert result1.output == response1
        assert result2.output == response2

    async def test_nested_overrides(self, simple_agent, mock_subprocess_popen):
        """Test nested override contexts."""
        outer_response = "Outer model response"
        inner_response = "Inner model response"

        with simple_agent.override(model=TestModel(custom_output_text=outer_response)):
            with simple_agent.override(
                model=TestModel(custom_output_text=inner_response)
            ):
                inner_result = await simple_agent.run("inner query")
            outer_result = await simple_agent.run("outer query")

        assert inner_result.output == inner_response
        assert outer_result.output == outer_response


# ============================================================================
# capture_run_messages Tests
# ============================================================================


class TestCaptureRunMessages:
    """Tests for capture_run_messages functionality."""

    async def test_capture_basic_conversation(
        self, simple_agent, mock_subprocess_popen
    ):
        """Test capturing a basic conversation."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("Hello, help me with Linux")

        # Should have at least request and response
        assert len(messages) >= 2

        # First should be request with system + user prompt
        assert isinstance(messages[0], ModelRequest)

        # Should end with a response
        responses = [m for m in messages if isinstance(m, ModelResponse)]
        assert len(responses) >= 1

    async def test_capture_tool_interactions(self, simple_agent, mock_subprocess_popen):
        """Test capturing tool call and return in messages."""
        with capture_run_messages() as messages:
            with simple_agent.override(model=TestModel()):
                await simple_agent.run("Run ls command")

        # Find all tool-related parts
        tool_calls = []
        tool_returns = []

        for msg in messages:
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        tool_calls.append(part)
            elif isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_returns.append(part)

        # TestModel should have made at least one tool call
        assert len(tool_calls) >= 1

    async def test_capture_multiple_runs(self, simple_agent, mock_subprocess_popen):
        """Test capturing messages from multiple runs."""
        with capture_run_messages() as msgs:
            with simple_agent.override(model=TestModel(custom_output_text="Run 1")):
                await simple_agent.run("First query")
            messages1 = list(msgs)

        with capture_run_messages() as msgs:
            with simple_agent.override(model=TestModel(custom_output_text="Run 2")):
                await simple_agent.run("Second query")
            messages2 = list(msgs)

        # Each capture should have its own messages
        assert len(messages1) >= 2
        assert len(messages2) >= 2


# ============================================================================
# System Prompt Integration Tests
# ============================================================================


class TestSystemPromptIntegration:
    """Tests for system prompt behavior."""

    async def test_system_prompt_included(
        self, legacy_agent, mock_subprocess_popen, mock_subprocess_run
    ):
        """Test that system prompt is included in messages."""
        with capture_run_messages() as messages:
            with legacy_agent.override(model=TestModel()):
                await legacy_agent.run("Help me")

        # Find system prompt
        system_prompts = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        system_prompts.append(part)

        assert len(system_prompts) >= 1
        # Check for key phrases from the system prompt
        system_content = system_prompts[0].content
        assert 'linux' in system_content.lower() or 'unix' in system_content.lower()

    async def test_custom_system_prompt(self, mock_subprocess_popen):
        """Test agent with custom system prompt."""
        custom_prompt = "You are a Python expert. Help with Python code."

        agent = Agent(
            model="test",
            tools=[bash_tool],
            system_prompt=custom_prompt,
        )

        with capture_run_messages() as messages:
            with agent.override(model=TestModel()):
                await agent.run("Help me with Python")

        # Find and verify system prompt
        system_prompts = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, SystemPromptPart):
                        system_prompts.append(part)

        assert len(system_prompts) >= 1
        assert 'Python expert' in system_prompts[0].content


# ============================================================================
# Tool Integration Tests
# ============================================================================


class TestToolIntegration:
    """Tests for tool integration with the agent."""

    async def test_bash_tool_integration(self, simple_agent, mock_subprocess_popen):
        """Test bash tool is properly integrated with agent."""
        def run_specific_bash(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                return ModelResponse(
                    parts=[ToolCallPart('bash', {'command': 'echo hello'})]
                )
            tool_return = messages[-1].parts[0]
            return ModelResponse(
                parts=[TextPart(f'Output: {tool_return.content}')]
            )

        with capture_run_messages() as messages:
            with simple_agent.override(model=FunctionModel(run_specific_bash)):
                await simple_agent.run("Say hello")

        # Verify the tool was called and returned
        tool_returns = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_returns.append(part)

        assert len(tool_returns) >= 1

    async def test_system_log_tool_integration(
        self, legacy_agent, mock_subprocess_run, mock_subprocess_popen
    ):
        """Test system log tools are properly integrated."""
        def get_system_log(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                return ModelResponse(
                    parts=[ToolCallPart('get_current_system_log', {})]
                )
            return ModelResponse(parts=[TextPart('Log retrieved')])

        with legacy_agent.override(model=FunctionModel(get_system_log)):
            result = await legacy_agent.run("Show system log")

        assert result.output == 'Log retrieved'

    async def test_shell_history_tool_integration(
        self, legacy_agent, mock_subprocess_popen, tmp_path, monkeypatch
    ):
        """Test shell history tool is properly integrated."""
        # Setup mock history file
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("SHELL", "/bin/bash")
        history_file = tmp_path / ".bash_history"
        history_file.write_text("ls -la\ncd /tmp\npwd\n")

        def get_history(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                return ModelResponse(
                    parts=[ToolCallPart('get_filtered_shell_history', {'n': 3})]
                )
            tool_return = messages[-1].parts[0]
            return ModelResponse(
                parts=[TextPart(f'History: {tool_return.content}')]
            )

        with legacy_agent.override(model=FunctionModel(get_history)):
            result = await legacy_agent.run("Show my command history")

        assert 'History:' in result.output


# ============================================================================
# Message History Tests
# ============================================================================


class TestMessageHistory:
    """Tests for message history handling."""

    async def test_conversation_continuity(self, simple_agent, mock_subprocess_popen):
        """Test that message history enables conversation continuity."""
        history = None

        with simple_agent.override(
            model=TestModel(custom_output_text="First response")
        ):
            result1 = await simple_agent.run("First message")
            history = result1.all_messages()

        assert history is not None
        assert len(history) >= 2

        # Second run with history
        with simple_agent.override(
            model=TestModel(custom_output_text="Second response")
        ):
            result2 = await simple_agent.run(
                "Second message",
                message_history=history
            )

        # New history should include previous messages
        new_history = result2.all_messages()
        assert len(new_history) > len(history)

    async def test_all_messages_structure(self, simple_agent, mock_subprocess_popen):
        """Test the structure of all_messages() output."""
        with simple_agent.override(model=TestModel()):
            result = await simple_agent.run("Test query")
            messages = result.all_messages()

        # Should have alternating request/response pattern
        assert len(messages) >= 2

        # Messages should be properly typed
        for msg in messages:
            assert isinstance(msg, (ModelRequest, ModelResponse))


# ============================================================================
# Pytest Fixture Override Pattern Tests
# ============================================================================


@pytest.fixture
def override_simple_agent(simple_agent):
    """Fixture that pre-overrides the agent with TestModel."""
    with simple_agent.override(model=TestModel()):
        yield simple_agent


class TestFixtureOverridePattern:
    """Tests demonstrating the pytest fixture override pattern."""

    async def test_with_fixture_override(
        self, override_simple_agent, mock_subprocess_popen
    ):
        """Test using the fixture-based override pattern."""
        # Agent is already overridden via fixture
        result = await override_simple_agent.run("Test with fixture")

        assert result.output is not None

    async def test_fixture_isolation(
        self, override_simple_agent, mock_subprocess_popen
    ):
        """Test that fixture provides proper test isolation."""
        result1 = await override_simple_agent.run("Query 1")
        result2 = await override_simple_agent.run("Query 2")

        # Each should get a response
        assert result1.output is not None
        assert result2.output is not None


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in agent interactions."""

    async def test_tool_exception_handling(self, simple_agent):
        """Test that tool exceptions are handled gracefully."""
        def call_with_error(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                # Call bash with a command that will fail
                return ModelResponse(
                    parts=[ToolCallPart('bash', {'command': 'nonexistent_cmd_12345'})]
                )
            return ModelResponse(parts=[TextPart('Handled error')])

        # Mock to simulate command not found
        with patch('legacyhelper.tools.command_tool.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ('', 'command not found')
            mock_process.returncode = 127
            mock_popen.return_value.__enter__.return_value = mock_process

            with simple_agent.override(model=FunctionModel(call_with_error)):
                result = await simple_agent.run("Run invalid command")

        assert result.output == 'Handled error'

    async def test_blocked_command_in_agent_flow(self, simple_agent):
        """Test that blocked commands don't crash the agent."""
        def try_blocked(
            messages: List[ModelMessage], info: AgentInfo  # pylint: disable=unused-argument
        ) -> ModelResponse:
            if len(messages) == 1:
                return ModelResponse(
                    parts=[ToolCallPart('bash', {'command': 'shutdown -h now'})]
                )
            tool_return = messages[-1].parts[0]
            # Check if it was blocked
            if 'Blocked' in str(tool_return.content):
                return ModelResponse(
                    parts=[TextPart('Command was safely blocked')]
                )
            return ModelResponse(parts=[TextPart('Unexpected result')])

        with simple_agent.override(model=FunctionModel(try_blocked)):
            result = await simple_agent.run("Shutdown the system")

        assert result.output == 'Command was safely blocked'
