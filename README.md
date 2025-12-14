# LegacyHelper

An AI-powered troubleshooting agent for legacy Linux/UNIX systems. LegacyHelper diagnoses system issues, retrieves relevant troubleshooting information from external sources, and presents command options for user approval before execution.

## Features

- **Intelligent System Diagnosis** – Analyzes system logs and configuration
- **External Resource Integration** – Searches StackOverflow, ArchWiki, and other resources for solutions
- **Human-in-the-Loop Execution** – Presents command options for user review and approval
- **Multi-Model Support** – Works with OpenAI, Claude, and Google Gemini
- **Interactive TUI** – Rich terminal user interface with streaming output

## Prerequisites

- Python 3.11+
- API key for at least one of: OpenAI, Claude (Anthropic), or Google Gemini

## Setup

### 1. Install Dependencies

```bash
uv venv
uv sync
```

### 2. Configure API Key

Set one of the following environment variables:

```bash
# For OpenAI (GPT-4, GPT-3.5-turbo, etc.)
export OPENAI_API_KEY="your-api-key-here"

# OR for Claude (Anthropic)
export ANTHROPIC_API_KEY="your-api-key-here"

# OR for Google Gemini
export GEMINI_API_KEY="your-api-key-here"
```

## Running

### Default Mode (Auto-detect Model)
Automatically detects which API key is set and uses the appropriate provider:

```bash
python main.py
```

### Specify Provider
```bash
# Use OpenAI
python main.py --provider openai

# Use Claude
python main.py --provider claude

# Use Gemini
python main.py --provider gemini
```

### Specify Model
```bash
python main.py --provider openai --model gpt-4-turbo
python main.py --provider claude --model claude-3-opus-20240229
```

### Additional Options
```bash
# List available providers and their API key status
python main.py --list-providers

# Adjust sampling temperature (0.0-2.0, default: 0.7)
python main.py --temperature 0.5

```

## Project Structure

```
legacyhelper/
├── tools/        # System tools and bash execution tool
├── core/         # AI agent core logic and workflows
├── model/        # Model abstractions and factory
├── ui/           # Terminal UI components (TUI)
└── __init__.py
```

## Development

### Run Tests
```bash
pytest
```

### Code Quality
```bash
pylint legacyhelper --disable=all --enable=C,W,E 2>&1
```

## Tech Stack

- **Framework:** Pydantic AI
- **Language:** Python 3.11+
- **UI:** Textual + Rich
- **Testing:** Pytest
- **Package Manager:** uv
- **LLM Providers:** OpenAI, Anthropic, Google Generative AI
