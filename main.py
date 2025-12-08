"""Main entry point for LegacyHelper application."""
import os
import sys
import argparse
from pydantic_ai import Agent, models
from legacyhelper.ui.app import LegacyHelperApp
from legacyhelper.model.factory import ModelFactory
from legacyhelper.tools.command_tool import bash_tool, ExecDeps, SYSTEM_LOG_TOOLSET

def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="LegacyHelper - AI troubleshooting assistant for legacy systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use auto-detected model (checks for API keys in order: OpenAI, Claude, Gemini)
  python main.py

  # Use specific provider
  python main.py --provider openai
  python main.py --provider claude
  python main.py --provider gemini

  # Use specific model
  python main.py --provider openai --model gpt-4-turbo
  python main.py --provider claude --model claude-3-opus-20240229

  # Legacy CLI mode
  python main.py --cli

Environment Variables:
  OPENAI_API_KEY      - For OpenAI (GPT-4, GPT-3.5, etc.)
  ANTHROPIC_API_KEY   - For Anthropic Claude
  GEMINI_API_KEY      - For Google Gemini
        """
    )

    parser.add_argument(
        "--provider",
        choices=ModelFactory.list_providers(),
        help="LLM provider to use (default: auto-detect from environment)"
    )

    parser.add_argument(
        "--model",
        help="Specific model to use (default: provider's default model)"
    )

    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in legacy CLI mode instead of TUI"
    )

    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available providers and exit"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (0.0 to 2.0, default: 0.7)"
    )

    return parser.parse_args()


def main() -> None:
    """Launch the LegacyHelper TUI application."""
    args = parse_args()

    # Handle --list-providers
    if args.list_providers:
        print("Available LLM providers:")
        for provider in ModelFactory.list_providers():
            default_model = ModelFactory.get_default_model(provider)
            api_key_var = ModelFactory.API_KEY_ENV_VARS[provider]
            has_key = "✓" if os.environ.get(api_key_var) else "✗"
            print(f"  {has_key} {provider:10} (default: {default_model}, env: {api_key_var})")
        sys.exit(0)

    # Create model
    try:
        if args.provider:
            # User specified a provider
            model_kwargs = {"temperature": args.temperature}
            if args.model:
                model_kwargs["model_name"] = args.model

            model = ModelFactory.create(args.provider, **model_kwargs)
            provider_name = args.provider

        else:
            # Auto-detect from environment
            model_kwargs = {"temperature": args.temperature}
            if args.model:
                model_kwargs["model_name"] = args.model

            model = ModelFactory.create_from_env(**model_kwargs)

            # Determine which provider was used
            if isinstance(model, ModelFactory.MODELS["openai"]):
                provider_name = "openai"
            elif isinstance(model, ModelFactory.MODELS["claude"]):
                provider_name = "claude"
            else:
                provider_name = "gemini"

        print(f"✓ Using {provider_name} model")

    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nAvailable providers:")
        for provider in ModelFactory.list_providers():
            api_key_var = ModelFactory.API_KEY_ENV_VARS[provider]
            print(f"  • {provider}: Set {api_key_var}")
        print("\nRun with --list-providers to see which API keys are set")
        sys.exit(1)

    # Initialize agent with the model
    agent = Agent(model=model, tools=[bash_tool], toolsets=[SYSTEM_LOG_TOOLSET])
    app = LegacyHelperApp(agent=agent)
    app.run()


if __name__ == "__main__":
    main()