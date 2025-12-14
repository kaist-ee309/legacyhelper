"""Unit tests for workflow.py module."""
import pytest
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock, patch, call
from typing import Optional, AsyncIterator, List

from pydantic_ai import FinalResultEvent, FunctionToolCallEvent, Agent

# Mock the circular imports before importing the actual module
sys.modules['legacyhelper.ui.widgets'] = MagicMock()
sys.modules['textual'] = MagicMock()
sys.modules['textual.app'] = MagicMock()

from legacyhelper.core.workflow import Workflow, WorkflowCallbacks


# Helper to create async iterables
async def async_iter(items: List):
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item


@pytest.fixture
def workflow():
    """Create a Workflow instance for testing."""
    return Workflow()


@pytest.fixture
def mock_callbacks():
    """Create mock callbacks for workflow events."""
    callbacks = WorkflowCallbacks(
        on_spinner_add=AsyncMock(),
        on_spinner_remove=AsyncMock(),
        on_streaming_start=AsyncMock(return_value=MagicMock()),
        on_stream_append=AsyncMock(),
        on_stream_clear=AsyncMock(),
        on_error=AsyncMock(),
        on_status_update=MagicMock(),
    )
    return callbacks


@pytest.fixture
def mock_agent():
    """Create a mock Agent instance."""
    agent = MagicMock(spec=Agent)
    agent.is_model_request_node = MagicMock()
    agent.is_call_tools_node = MagicMock()
    agent.iter = MagicMock()
    return agent


def create_mock_agent_iter(nodes: List, result_messages: List):
    """Helper to create a properly mocked agent iter context manager."""
    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)

    async def nodes_generator():
        for node in nodes:
            yield node

    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=result_messages)
    mock_result.ctx = MagicMock()

    mock_iter.result = mock_result

    return mock_iter


@pytest.mark.asyncio
async def test_workflow_initialization():
    """Test Workflow initialization."""
    workflow = Workflow()
    assert workflow.message_history is None


@pytest.mark.asyncio
async def test_workflow_process_agent_response_with_model_request(
    workflow, mock_agent, mock_callbacks
):
    """Test process_agent_response with a model request node."""
    final_result_event = MagicMock(spec=FinalResultEvent)

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())

    # stream_text returns an async generator directly
    async def stream_text_generator(*args, **kwargs):
        for text in ["Hello", " ", "World"]:
            yield text

    request_stream.stream_text = MagicMock(return_value=stream_text_generator())

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=True)
    mock_agent.is_call_tools_node = MagicMock(return_value=False)

    result_messages = [{"role": "assistant", "content": "Hello World"}]
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test input", mock_callbacks)

    # Verify callbacks were called
    mock_callbacks.on_streaming_start.assert_called_once()
    assert mock_callbacks.on_stream_append.call_count == 3
    mock_callbacks.on_stream_clear.assert_called_once()
    mock_callbacks.on_status_update.assert_called_once_with("ready")

    # Verify message history was updated
    assert workflow.message_history == result_messages


@pytest.mark.asyncio
async def test_workflow_process_agent_response_with_tool_call(
    workflow, mock_agent, mock_callbacks
):
    """Test process_agent_response when agent calls a tool."""
    tool_event = MagicMock(spec=FunctionToolCallEvent)
    tool_event.part = MagicMock()
    tool_event.part.args_as_dict = MagicMock(
        return_value={"command": "ls -la", "tool_name": "bash_tool"}
    )

    handle_stream = AsyncMock()
    handle_stream.__aenter__ = AsyncMock(return_value=handle_stream)
    handle_stream.__aexit__ = AsyncMock(return_value=None)

    async def tool_event_generator():
        yield tool_event

    handle_stream.__aiter__ = MagicMock(return_value=tool_event_generator())

    node = AsyncMock()
    node.stream = MagicMock(return_value=handle_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=False)
    mock_agent.is_call_tools_node = MagicMock(return_value=True)

    result_messages = [{"role": "assistant", "content": "Tool executed"}]
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "run ls", mock_callbacks)

    # Verify spinner callback was called with correct content
    mock_callbacks.on_spinner_add.assert_called_once()
    call_args = mock_callbacks.on_spinner_add.call_args[0][0]
    assert "ls -la" in call_args
    assert "Running..." in call_args


@pytest.mark.asyncio
async def test_workflow_process_agent_response_streams_text(
    workflow, mock_agent, mock_callbacks
):
    """Test that text output is properly streamed."""
    final_result_event = MagicMock(spec=FinalResultEvent)

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())

    async def text_stream():
        for text in ["AI", " ", "response", " ", "text"]:
            yield text

    request_stream.stream_text = MagicMock(return_value=text_stream())

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=True)
    mock_agent.is_call_tools_node = MagicMock(return_value=False)

    result_messages = []
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Verify all text chunks were appended
    assert mock_callbacks.on_stream_append.call_count == 5
    mock_callbacks.on_stream_append.assert_any_call("AI")
    mock_callbacks.on_stream_append.assert_any_call(" ")
    mock_callbacks.on_stream_append.assert_any_call("response")


@pytest.mark.asyncio
async def test_workflow_removes_spinner_after_final_result(
    workflow, mock_agent, mock_callbacks
):
    """Test that spinner is removed after final result is found."""
    final_result_event = MagicMock(spec=FinalResultEvent)

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter([]))

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=True)
    mock_agent.is_call_tools_node = MagicMock(return_value=False)

    result_messages = []
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Verify spinner was removed
    mock_callbacks.on_spinner_remove.assert_called_once()


@pytest.mark.asyncio
async def test_workflow_process_multiple_nodes(
    workflow, mock_agent, mock_callbacks
):
    """Test process_agent_response with multiple nodes (model and tool)."""
    # First node: model request
    final_result_event = MagicMock(spec=FinalResultEvent)

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter(["text"]))

    model_node = AsyncMock()
    model_node.stream = MagicMock(return_value=request_stream)

    # Second node: tool call
    tool_event = MagicMock(spec=FunctionToolCallEvent)
    tool_event.part = MagicMock()
    tool_event.part.args_as_dict = MagicMock(
        return_value={"command": "echo test", "tool_name": "bash"}
    )

    handle_stream = AsyncMock()
    handle_stream.__aenter__ = AsyncMock(return_value=handle_stream)
    handle_stream.__aexit__ = AsyncMock(return_value=None)

    async def tool_event_generator():
        yield tool_event

    handle_stream.__aiter__ = MagicMock(return_value=tool_event_generator())

    tool_node = AsyncMock()
    tool_node.stream = MagicMock(return_value=handle_stream)

    # Setup agent to handle both node types
    def is_model_node(node):
        return node == model_node

    def is_tool_node(node):
        return node == tool_node

    mock_agent.is_model_request_node = MagicMock(side_effect=is_model_node)
    mock_agent.is_call_tools_node = MagicMock(side_effect=is_tool_node)

    result_messages = [{"role": "assistant", "content": "Done"}]
    mock_agent.iter = MagicMock(
        return_value=create_mock_agent_iter([model_node, tool_node], result_messages)
    )

    await workflow.process_agent_response(mock_agent, "complex task", mock_callbacks)

    # Both node types should be processed
    assert mock_agent.is_model_request_node.call_count >= 1
    assert mock_agent.is_call_tools_node.call_count >= 1
    assert workflow.message_history == result_messages


@pytest.mark.asyncio
async def test_workflow_no_final_result_event(
    workflow, mock_agent, mock_callbacks
):
    """Test behavior when no final result event is found."""
    # Some other event type (not FinalResultEvent)
    other_event = MagicMock()

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield other_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter([]))

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=True)
    mock_agent.is_call_tools_node = MagicMock(return_value=False)

    result_messages = []
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Spinner should not be removed if final result was not found
    mock_callbacks.on_spinner_remove.assert_not_called()


@pytest.mark.asyncio
async def test_workflow_tool_call_with_generic_tool(
    workflow, mock_agent, mock_callbacks
):
    """Test tool call event with generic tool name when command is missing."""
    tool_event = MagicMock(spec=FunctionToolCallEvent)
    tool_event.part = MagicMock()
    # No command in args
    tool_event.part.args_as_dict = MagicMock(
        return_value={"tool_name": "generic_tool"}
    )

    handle_stream = AsyncMock()
    handle_stream.__aenter__ = AsyncMock(return_value=handle_stream)
    handle_stream.__aexit__ = AsyncMock(return_value=None)

    async def tool_event_generator():
        yield tool_event

    handle_stream.__aiter__ = MagicMock(return_value=tool_event_generator())

    node = AsyncMock()
    node.stream = MagicMock(return_value=handle_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=False)
    mock_agent.is_call_tools_node = MagicMock(return_value=True)

    result_messages = []
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Verify spinner was added with tool name as fallback
    mock_callbacks.on_spinner_add.assert_called_once()
    call_args = mock_callbacks.on_spinner_add.call_args[0][0]
    assert "generic_tool" in call_args


@pytest.mark.asyncio
async def test_workflow_error_handling(
    workflow, mock_agent, mock_callbacks
):
    """Test that exceptions are properly handled and reported."""
    test_error = Exception("Test error during processing")

    mock_agent.iter = MagicMock(side_effect=test_error)

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Verify error callback was called
    mock_callbacks.on_error.assert_called_once_with(test_error)
    # Verify status was not updated to ready on error
    mock_callbacks.on_status_update.assert_not_called()


@pytest.mark.asyncio
async def test_workflow_preserves_message_history(
    workflow, mock_agent, mock_callbacks
):
    """Test that message history is preserved across multiple calls."""
    # First call
    final_result_event = MagicMock(spec=FinalResultEvent)

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter([]))

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=True)
    mock_agent.is_call_tools_node = MagicMock(return_value=False)

    first_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"}
    ]
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], first_messages))

    await workflow.process_agent_response(mock_agent, "Hello", mock_callbacks)

    # Verify first message history
    assert workflow.message_history == first_messages

    # Setup for second call - reset individual callback mocks
    mock_callbacks.on_spinner_add.reset_mock()
    mock_callbacks.on_spinner_remove.reset_mock()
    mock_callbacks.on_streaming_start.reset_mock()
    mock_callbacks.on_stream_append.reset_mock()
    mock_callbacks.on_stream_clear.reset_mock()
    mock_callbacks.on_error.reset_mock()
    mock_callbacks.on_status_update.reset_mock()

    second_messages = first_messages + [
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm doing well"}
    ]

    request_stream2 = AsyncMock()
    request_stream2.__aenter__ = AsyncMock(return_value=request_stream2)
    request_stream2.__aexit__ = AsyncMock(return_value=None)

    async def event_generator2():
        yield final_result_event

    request_stream2.__aiter__ = MagicMock(return_value=event_generator2())
    request_stream2.stream_text = MagicMock(return_value=async_iter([]))

    node2 = AsyncMock()
    node2.stream = MagicMock(return_value=request_stream2)

    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node2], second_messages))

    await workflow.process_agent_response(mock_agent, "How are you?", mock_callbacks)

    # Verify message history was updated with all messages
    assert workflow.message_history == second_messages


@pytest.mark.asyncio
async def test_workflow_handles_missing_command_in_tool_args(
    workflow, mock_agent, mock_callbacks
):
    """Test tool call handling when args_as_dict returns missing fields."""
    tool_event = MagicMock(spec=FunctionToolCallEvent)
    tool_event.part = MagicMock()
    # Empty args
    tool_event.part.args_as_dict = MagicMock(return_value={})

    handle_stream = AsyncMock()
    handle_stream.__aenter__ = AsyncMock(return_value=handle_stream)
    handle_stream.__aexit__ = AsyncMock(return_value=None)

    async def tool_event_generator():
        yield tool_event

    handle_stream.__aiter__ = MagicMock(return_value=tool_event_generator())

    node = AsyncMock()
    node.stream = MagicMock(return_value=handle_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=False)
    mock_agent.is_call_tools_node = MagicMock(return_value=True)

    result_messages = []
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Verify spinner was added with default generic tool name
    mock_callbacks.on_spinner_add.assert_called_once()
    call_args = mock_callbacks.on_spinner_add.call_args[0][0]
    assert "[GENERIC TOOL]" in call_args


@pytest.mark.asyncio
async def test_workflow_callbacks_called_in_order(
    workflow, mock_agent, mock_callbacks
):
    """Test that workflow callbacks are called in the correct order."""
    final_result_event = MagicMock(spec=FinalResultEvent)

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter(["test"]))

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_agent.is_model_request_node = MagicMock(return_value=True)
    mock_agent.is_call_tools_node = MagicMock(return_value=False)

    result_messages = []
    mock_agent.iter = MagicMock(return_value=create_mock_agent_iter([node], result_messages))

    await workflow.process_agent_response(mock_agent, "test", mock_callbacks)

    # Verify callback order
    mock_callbacks.on_streaming_start.assert_called_once()
    mock_callbacks.on_stream_append.assert_called_once_with("test")
    mock_callbacks.on_spinner_remove.assert_called_once()
    mock_callbacks.on_stream_clear.assert_called_once()

    # Status update should be called last
    assert mock_callbacks.on_status_update.call_args[0][0] == "ready"
