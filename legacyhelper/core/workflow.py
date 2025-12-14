"""Workflow module for managing agent interaction and message processing."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from pydantic_ai import Agent, FinalResultEvent, FunctionToolCallEvent

if TYPE_CHECKING:
    from legacyhelper.ui.widgets import StreamingMessageWidget


@dataclass
class WorkflowCallbacks:
    """Callbacks for UI updates during workflow processing."""
    on_spinner_add: Callable[[str], Awaitable[None]]
    on_spinner_remove: Callable[[], Awaitable[None]]
    on_streaming_start: Callable[[], Awaitable[Optional["StreamingMessageWidget"]]]
    on_stream_append: Callable[[str], Awaitable[None]]
    on_stream_clear: Callable[[], Awaitable[None]]
    on_error: Callable[[Exception], Awaitable[None]]
    on_status_update: Callable[[str], None]


class Workflow:
    """Manages agent interaction and message processing."""

    def __init__(self) -> None:
        """Initialize the workflow."""
        self.message_history = None

    async def process_agent_response(
        self,
        agent: Agent,
        user_input: str,
        callbacks: WorkflowCallbacks,
    ) -> None:
        """Process the agent response with proper synchronization.

        Args:
            agent: The Pydantic AI agent instance
            user_input: The user's input text
            callbacks: UI callbacks for workflow events
        """
        try:
            # Use agent.iter() to iterate over event graph
            async with agent.iter(
                user_input, message_history=self.message_history
            ) as result:
                # Process each node in the agent graph
                async for node in result:
                    await self._process_node(agent, node, result, callbacks)

            self.message_history = result.result.all_messages()

            # Clear streaming message reference
            await callbacks.on_stream_clear()

            # Update status
            callbacks.on_status_update("ready")

        except Exception as exc:  # pylint: disable=broad-except
            await callbacks.on_error(exc)

    async def _process_node(
        self, agent: Agent, node, result, callbacks: WorkflowCallbacks
    ) -> None:
        """Process a single agent graph node.

        Args:
            agent: The Pydantic AI agent instance
            node: The agent graph node
            result: The agent result context
            callbacks: UI callbacks for workflow events
        """
        # Check if this is a model request node with streaming text
        if agent.is_model_request_node(node):
            async with node.stream(result.ctx) as request_stream:
                final_result_found = False
                async for event in request_stream:
                    if isinstance(event, FinalResultEvent):
                        # Create streaming message widget (thread-safe via callback)
                        await callbacks.on_streaming_start()
                        final_result_found = True
                        break

                if final_result_found:
                    # Stop spinner (thread-safe via callback)
                    await callbacks.on_spinner_remove()
                    # Stream text to display
                    async for output in request_stream.stream_text(
                        delta=True, debounce_by=0.01
                    ):
                        await callbacks.on_stream_append(output)

        elif agent.is_call_tools_node(node):
            async with node.stream(result.ctx) as handle_stream:
                async for event in handle_stream:
                    if isinstance(event, FunctionToolCallEvent):
                        # Get tool info
                        args = event.part.args_as_dict()
                        command = args.get("command")
                        tool_name = args.get("tool_name", "[GENERIC TOOL]")
                        entity = command if command is not None else tool_name
                        # Add spinner for tool execution (thread-safe via callback)
                        await callbacks.on_spinner_add(f"Running... {entity}")
