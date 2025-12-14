"""Unit tests for workflow.py module."""
import pytest
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock, patch, call
from typing import Optional, AsyncIterator, List, TypeVar

from pydantic_ai import FinalResultEvent, FunctionToolCallEvent

# Mock the circular imports before importing the actual module
sys.modules['legacyhelper.ui.widgets'] = MagicMock()
sys.modules['textual'] = MagicMock()
sys.modules['textual.app'] = MagicMock()

from legacyhelper.core.workflow import agent_graph_traversal


# Helper to create async iterables
async def async_iter(items: List):
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item


@pytest.fixture
def mock_app():
    """Create a mock Textual App with agent and message history."""
    app = MagicMock()
    app.agent = MagicMock()
    # Use configure_mock to set message_history as a regular list, not an AsyncMock
    app.configure_mock(message_history=[])
    app.conversation_panel = MagicMock()
    app.current_spinner = None
    return app


@pytest.fixture
def mock_streaming_message():
    """Create a mock StreamingMessageWidget."""
    widget = MagicMock()
    widget.append_text = MagicMock()
    return widget


@pytest.mark.asyncio
async def test_agent_graph_traversal_with_final_result(mock_app, mock_streaming_message):
    """Test agent_graph_traversal with a final result event."""
    # Setup mock events
    final_result_event = MagicMock(spec=FinalResultEvent)

    # Mock the result object
    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[{"role": "user", "content": "test"}])

    # Mock the request stream
    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    # Create async generators for events
    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter(["Hello", " ", "World"]))

    # Mock node
    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    # Mock agent methods
    mock_app.agent.is_model_request_node = MagicMock(return_value=True)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=False)

    # Mock the agent iter
    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)
    mock_app.conversation_panel.add_streaming_message = MagicMock(
        return_value=mock_streaming_message
    )

    # Execute
    await agent_graph_traversal(
        mock_app,
        "test input",
        streaming_message=None
    )

    # Assertions
    mock_app.agent.iter.assert_called_once_with(
        "test input",
        message_history=[]
    )
    mock_app.agent.is_model_request_node.assert_called_once_with(node)
    # Check that the message history was updated with the result
    assert mock_app.message_history == [{"role": "user", "content": "test"}]


@pytest.mark.asyncio
async def test_agent_graph_traversal_with_function_tool_call(mock_app):
    """Test agent_graph_traversal when agent calls tools."""
    # Setup tool call event
    tool_event = MagicMock(spec=FunctionToolCallEvent)
    tool_event.part = MagicMock()
    tool_event.part.args_as_dict = MagicMock(
        return_value={"command": "ls -la", "tool_name": "bash_tool"}
    )

    # Mock result
    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[{"role": "assistant", "content": "Running command"}])

    # Mock the handle stream for tool calls
    handle_stream = AsyncMock()
    handle_stream.__aenter__ = AsyncMock(return_value=handle_stream)
    handle_stream.__aexit__ = AsyncMock(return_value=None)

    async def tool_event_generator():
        yield tool_event

    handle_stream.__aiter__ = MagicMock(return_value=tool_event_generator())

    # Mock node
    node = AsyncMock()
    node.stream = MagicMock(return_value=handle_stream)

    # Mock spinner widget
    mock_spinner = MagicMock()
    mock_app.conversation_panel.add_spinner = MagicMock(return_value=mock_spinner)

    # Mock agent methods
    mock_app.agent.is_model_request_node = MagicMock(return_value=False)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=True)

    # Mock the agent iter
    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)

    # Execute
    await agent_graph_traversal(
        mock_app,
        "run ls",
        streaming_message=None
    )

    # Assertions
    mock_app.conversation_panel.add_spinner.assert_called_once()
    call_args = mock_app.conversation_panel.add_spinner.call_args[0][0]
    assert "ls -la" in call_args
    assert "Running" in call_args
    assert mock_app.message_history == [{"role": "assistant", "content": "Running command"}]


@pytest.mark.asyncio
async def test_agent_graph_traversal_streams_text_output(mock_app, mock_streaming_message):
    """Test that text output is streamed to the message widget."""
    final_result_event = MagicMock(spec=FinalResultEvent)

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[])

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())

    async def text_stream():
        for text in ["Hello", " ", "from", " ", "AI"]:
            yield text

    request_stream.stream_text = MagicMock(return_value=text_stream())

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_app.agent.is_model_request_node = MagicMock(return_value=True)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=False)

    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)
    mock_app.conversation_panel.add_streaming_message = MagicMock(
        return_value=mock_streaming_message
    )

    await agent_graph_traversal(mock_app, "test", streaming_message=None)

    # Verify text was streamed
    assert mock_streaming_message.append_text.call_count == 5
    mock_streaming_message.append_text.assert_any_call("Hello")
    mock_streaming_message.append_text.assert_any_call(" ")
    mock_streaming_message.append_text.assert_any_call("from")


@pytest.mark.asyncio
async def test_agent_graph_traversal_removes_spinner(mock_app, mock_streaming_message):
    """Test that spinner is removed after final result is found."""
    final_result_event = MagicMock(spec=FinalResultEvent)

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[])

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter([]))

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    # Set up a current spinner that should be removed
    mock_spinner = MagicMock()
    mock_spinner.remove = AsyncMock()
    mock_app.current_spinner = mock_spinner

    mock_app.agent.is_model_request_node = MagicMock(return_value=True)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=False)

    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)
    mock_app.conversation_panel.add_streaming_message = MagicMock(
        return_value=mock_streaming_message
    )

    await agent_graph_traversal(mock_app, "test", streaming_message=None)

    # Verify spinner was removed
    mock_spinner.remove.assert_called_once()
    assert mock_app.current_spinner is None


@pytest.mark.asyncio
async def test_agent_graph_traversal_with_provided_streaming_message(mock_app):
    """Test agent_graph_traversal when conversation panel is disabled."""
    streaming_message = MagicMock()
    streaming_message.append_text = MagicMock()

    final_result_event = MagicMock(spec=FinalResultEvent)

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[])

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield final_result_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())

    async def text_stream():
        yield "Response"

    request_stream.stream_text = MagicMock(return_value=text_stream())

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_app.agent.is_model_request_node = MagicMock(return_value=True)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=False)

    # Set conversation_panel to None so the provided streaming message is used
    mock_app.conversation_panel = None

    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)

    await agent_graph_traversal(mock_app, "test", streaming_message=streaming_message)

    # Verify the provided widget was used when conversation_panel is disabled
    streaming_message.append_text.assert_called_with("Response")


@pytest.mark.asyncio
async def test_agent_graph_traversal_multiple_nodes(mock_app):
    """Test agent_graph_traversal with multiple nodes (both model and tool calls)."""
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

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[])

    # Setup agent to handle both node types
    def is_model_node(node):
        return node == model_node

    def is_tool_node(node):
        return node == tool_node

    mock_app.agent.is_model_request_node = MagicMock(side_effect=is_model_node)
    mock_app.agent.is_call_tools_node = MagicMock(side_effect=is_tool_node)

    async def nodes_generator():
        yield model_node
        yield tool_node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)

    mock_spinner = MagicMock()
    mock_spinner.remove = AsyncMock()

    streaming_msg = MagicMock()
    streaming_msg.append_text = MagicMock()

    mock_app.conversation_panel.add_streaming_message = MagicMock(return_value=streaming_msg)
    mock_app.conversation_panel.add_spinner = MagicMock(return_value=mock_spinner)

    await agent_graph_traversal(mock_app, "complex task", streaming_message=None)

    # Both node types should be checked
    assert mock_app.agent.is_model_request_node.call_count >= 1
    assert mock_app.agent.is_call_tools_node.call_count >= 1


@pytest.mark.asyncio
async def test_agent_graph_traversal_no_final_result_event(mock_app):
    """Test behavior when no final result event is found."""
    # Some other event type
    other_event = MagicMock()  # Not a FinalResultEvent

    request_stream = AsyncMock()
    request_stream.__aenter__ = AsyncMock(return_value=request_stream)
    request_stream.__aexit__ = AsyncMock(return_value=None)

    async def event_generator():
        yield other_event

    request_stream.__aiter__ = MagicMock(return_value=event_generator())
    request_stream.stream_text = MagicMock(return_value=async_iter([]))

    node = AsyncMock()
    node.stream = MagicMock(return_value=request_stream)

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[])

    mock_app.agent.is_model_request_node = MagicMock(return_value=True)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=False)

    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)
    mock_app.conversation_panel.add_streaming_message = MagicMock()

    # Should not raise an error
    await agent_graph_traversal(mock_app, "test", streaming_message=None)

    # Spinner should remain as it was
    assert mock_app.current_spinner is None


@pytest.mark.asyncio
async def test_agent_graph_traversal_tool_call_without_spinner(mock_app):
    """Test tool call event when no spinner exists or is disabled."""
    tool_event = MagicMock(spec=FunctionToolCallEvent)
    tool_event.part = MagicMock()
    tool_event.part.args_as_dict = MagicMock(
        return_value={"command": "pwd", "tool_name": "bash"}
    )

    handle_stream = AsyncMock()
    handle_stream.__aenter__ = AsyncMock(return_value=handle_stream)
    handle_stream.__aexit__ = AsyncMock(return_value=None)

    async def tool_event_generator():
        yield tool_event

    handle_stream.__aiter__ = MagicMock(return_value=tool_event_generator())

    node = AsyncMock()
    node.stream = MagicMock(return_value=handle_stream)

    mock_result = MagicMock()
    mock_result.all_messages = MagicMock(return_value=[])

    mock_app.agent.is_model_request_node = MagicMock(return_value=False)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=True)

    # No conversation panel - spinner should not be created
    mock_app.conversation_panel = None

    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)

    # Should handle gracefully without conversation panel
    await agent_graph_traversal(mock_app, "test", streaming_message=None)

    assert mock_app.message_history == []


@pytest.mark.asyncio
async def test_agent_graph_traversal_empty_message_history(mock_app):
    """Test that message history is properly updated after traversal."""
    mock_result = MagicMock()
    test_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    mock_result.all_messages = MagicMock(return_value=test_messages)

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

    mock_app.agent.is_model_request_node = MagicMock(return_value=True)
    mock_app.agent.is_call_tools_node = MagicMock(return_value=False)

    async def nodes_generator():
        yield node

    mock_iter = AsyncMock()
    mock_iter.__aenter__ = AsyncMock(return_value=mock_iter)
    mock_iter.__aexit__ = AsyncMock(return_value=None)
    mock_iter.__aiter__ = MagicMock(return_value=nodes_generator())
    mock_iter.result = mock_result
    mock_iter.ctx = MagicMock()

    mock_app.agent.iter = MagicMock(return_value=mock_iter)
    mock_app.conversation_panel.add_streaming_message = MagicMock()

    assert mock_app.message_history == []

    await agent_graph_traversal(mock_app, "test", streaming_message=None)

    # Message history should be updated
    assert mock_app.message_history == test_messages
