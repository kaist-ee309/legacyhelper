# Changelog

All notable changes to LegacyHelper will be documented in this file.

## [Unreleased]

### Added
- **Multi-LLM Support**: OpenAI (GPT-4), Anthropic (Claude), and Google (Gemini)
  - `ModelFactory` for easy model creation and switching
  - Auto-detection of API keys from environment
  - Support for custom models and temperatures
  - Command-line options: `--provider`, `--model`, `--temperature`
  - 13 comprehensive tests for model factory
- Sophisticated terminal UI powered by Textual framework
- Smart command parser with confidence scoring and safety analysis
- Command execution with timeout protection and output capture
- Interactive command preview with Execute/Reject/Modify options
- Status bar with live status updates (ready/thinking/error)
- Command output widgets with syntax highlighting
- Dangerous command detection (rm -rf, dd, mkfs, etc.)
- Comprehensive unit tests (44 tests covering parser, executor, agent, models)
- Demo script for testing without API key (`demo_parser.py`)
- Type hints throughout the codebase
- Detailed multi-model guide (`MULTI_MODEL_GUIDE.md`)

### Fixed
- AttributeError: 'LegacyHelperApp' object has no attribute 'run_in_thread'
  - **Root cause**: Textual doesn't have a `run_in_thread()` method
  - **Solution**: Use Python's `asyncio.to_thread()` to run synchronous functions in thread pool
  - **Affects**: `agent.model.get_response()` and `interactive_executor.execute_with_confirmation()`
  - **Files changed**: `legacyhelper/ui/app.py` (lines 2, 190, 295)

### Technical Details

#### Command Parser
- Extracts commands from markdown code blocks, inline code, and text patterns
- Confidence scoring: code blocks (90%), inline (70%), patterns (60%)
- Safety analysis with pattern matching for dangerous operations
- Contextual warnings for rm, chmod, sudo, etc.
- Auto-generated descriptions for common commands

#### Command Executor
- Configurable timeout (default: 30 seconds)
- Process group management for clean termination
- Dry-run mode for safe testing
- Command validation before execution
- Interactive confirmation for dangerous operations

#### UI Components
- `MessageWidget`: Role-based styled messages (user/assistant/system/error)
- `CommandPreviewWidget`: Interactive command review with actions
- `CommandOutputWidget`: Execution results with syntax highlighting
- `StatusBarWidget`: Live status with model info and shortcuts
- `ConversationPanel`: Scrollable message history

## [0.1.0] - Initial Setup

### Added
- Basic project structure
- Gemini model integration
- Simple CLI interface
- Agent class for handling conversations
