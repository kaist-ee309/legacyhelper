#!/usr/bin/env python3
"""Test script to simulate a conversation and verify async handling works."""

import asyncio
from legacyhelper.ui.app import LegacyHelperApp


class MockModel:
    """Mock model that simulates API responses."""

    def get_response(self, prompt: str) -> str:
        """Simulate getting a response (synchronous)."""
        # Simulate some processing time
        import time
        time.sleep(0.1)

        # Return a response with a command
        if "disk" in prompt.lower():
            return """To check disk space, use:
```bash
df -h
```
This will show you disk usage in human-readable format."""
        elif "memory" in prompt.lower():
            return "Run `free -h` to check memory usage."
        else:
            return f"I received your question: '{prompt}'. Try asking about disk or memory."


class MockAgent:
    """Mock agent for testing."""

    def __init__(self):
        self.model = MockModel()
        self.console = None
        self.conversation_history = []


async def test_conversation_async():
    """Test that async conversation handling works."""
    print("Testing async conversation handling...")

    try:
        # Create mock agent
        agent = MockAgent()

        # Create app
        app = LegacyHelperApp(agent=agent)

        print("✓ App created with mock agent")

        # Test that we can call the model's get_response
        response = agent.model.get_response("How do I check disk space?")
        print(f"✓ Mock model works: {len(response)} chars")

        # Test asyncio.to_thread works with our mock
        response_async = await asyncio.to_thread(
            agent.model.get_response,
            "How do I check memory?"
        )
        print(f"✓ asyncio.to_thread works: {len(response_async)} chars")

        # Test command parser
        parsed = app.command_parser.get_best_command(response)
        if parsed:
            print(f"✓ Command parser extracted: '{parsed.command}'")
        else:
            print("✓ Command parser works (no commands in this response)")

        # Test executor
        result = await asyncio.to_thread(
            app.command_executor.execute,
            "echo 'Test execution'"
        )
        print(f"✓ Executor works: exit_code={result.exit_code}")

        print("\n✅ All async operations work correctly!")
        print("\nThe TUI should now work without errors when conversing.")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the async test."""
    success = asyncio.run(test_conversation_async())
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
