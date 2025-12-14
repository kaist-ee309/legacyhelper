from pydantic_ai import FinalResultEvent, FunctionToolCallEvent
from typing import Optional
from textual.app import App
from legacyhelper.ui.widgets import StreamingMessageWidget

async def agent_graph_traversal(self: App, 
                                user_input: str, 
                                streaming_message: Optional[StreamingMessageWidget]):
    '''
    Agent object construct graph for its state management and transition,
    and this can be explicitly traversed.
    With this approach, application can see if the agent is calling tools, or
    making final response.
    
    :param self: Description
    :param user_input: Description
    :param streaming_message: Description
    '''
    # Use agent.iter() to iterate over event graph (model requests, tool calls, etc.)
    async with self.agent.iter(
        user_input, message_history=self.message_history
    ) as result:
        # Process each node in the agent graph
        async for node in result:
            # Check if this is a model request node with streaming text
            if self.agent.is_model_request_node(node):
                async with node.stream(result.ctx) as request_stream:
                    final_result_found = False
                    async for event in request_stream:
                        if isinstance(event, FinalResultEvent):
                            # Response is finalized.
                            if self.conversation_panel:
                                streaming_message = self.conversation_panel.add_streaming_message()
                            final_result_found = True
                            break

                    if final_result_found:
                        # Stop spinner.
                        if self.current_spinner:
                            await self.current_spinner.remove()
                            self.current_spinner = None
                        # Once final response is observed, this can be streamed out
                        # to display.
                        async for output in request_stream.stream_text(delta=True,
                                                                        debounce_by=0.01):
                            if streaming_message:
                                streaming_message.append_text(output)

            elif self.agent.is_call_tools_node(node):
                async with node.stream(result.ctx) as handle_stream:
                    async for event in handle_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            if self.conversation_panel and not self.current_spinner:
                                # Show command executing with spinner.
                                command = event.part.args_as_dict().pop("command", None)
                                tool_name = event.part.args_as_dict().pop("tool_name", "[GENERIC TOOL]")
                                entity = command if command is not None else tool_name
                                self.current_spinner = self.conversation_panel.add_spinner(f"Running... {entity}")

    # Update message history
    self.message_history = result.result.all_messages()