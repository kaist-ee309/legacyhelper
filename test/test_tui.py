#!/usr/bin/env python3
"""Test script to verify TUI can be instantiated without errors."""

import sys
from legacyhelper.core.agent import Agent
from legacyhelper.ui.app import LegacyHelperApp


def test_tui_initialization():
    """Test that TUI can be initialized without errors."""
    print("Testing TUI initialization...")

    try:
        # Create a mock agent without API key
        class MockModel:
            def get_response(self, prompt: str) -> str:
                return f"Mock response for: {prompt}"

        class MockAgent:
            def __init__(self):
                self.model = MockModel()
                self.console = None
                self.conversation_history = []

        # Create the TUI app
        agent = MockAgent()
        app = LegacyHelperApp(agent=agent)

        print("✓ TUI app instantiated successfully")

        # Test that all components are initialized
        assert app.command_parser is not None, "Command parser not initialized"
        assert app.command_executor is not None, "Command executor not initialized"
        assert app.interactive_executor is not None, "Interactive executor not initialized"
        assert app.agent is not None, "Agent not set"

        print("✓ All components initialized correctly")

        # Test that methods exist
        assert hasattr(app, 'compose'), "compose method missing"
        assert hasattr(app, 'on_mount'), "on_mount method missing"
        assert hasattr(app, 'on_input_submitted'), "on_input_submitted method missing"
        assert hasattr(app, 'on_button_pressed'), "on_button_pressed method missing"

        print("✓ All required methods exist")

        print("\n✅ All TUI initialization tests passed!")
        print("\nNote: To run the actual TUI, use:")
        print("  export GEMINI_API_KEY='your-key'")
        print("  python main.py")
        return True

    except Exception as e:
        print(f"\n❌ TUI initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_tui_initialization()
    sys.exit(0 if success else 1)
