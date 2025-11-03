# Multi-Model Support Guide

LegacyHelper now supports multiple LLM providers! You can use OpenAI (GPT-4), Anthropic Claude, or Google Gemini.

## Quick Start

### 1. Set Your API Key

Choose one or more providers and set the corresponding API key:

```bash
# For OpenAI (GPT-4, GPT-3.5-turbo, etc.)
export OPENAI_API_KEY='your-openai-api-key'

# For Anthropic Claude
export ANTHROPIC_API_KEY='your-anthropic-api-key'

# For Google Gemini
export GEMINI_API_KEY='your-gemini-api-key'
```

### 2. Run LegacyHelper

```bash
# Auto-detect which API key is set (checks: OpenAI → Claude → Gemini)
python main.py

# Or specify which provider to use
python main.py --provider openai
python main.py --provider claude
python main.py --provider gemini
```

## Available Providers

| Provider | Default Model | API Key Variable | Get API Key |
|----------|--------------|------------------|-------------|
| **OpenAI** | gpt-4o | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| **Claude** | claude-3-5-sonnet-20241022 | `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| **Gemini** | gemini-2.0-flash-exp | `GEMINI_API_KEY` | https://makersuite.google.com/app/apikey |

## Usage Examples

### Check Available Providers

```bash
python main.py --list-providers
```

Output:
```
Available LLM providers:
  ✓ gemini     (default: gemini-2.0-flash-exp, env: GEMINI_API_KEY)
  ✓ openai     (default: gpt-4o, env: OPENAI_API_KEY)
  ✗ claude     (default: claude-3-5-sonnet-20241022, env: ANTHROPIC_API_KEY)
```

The ✓ indicates which API keys are currently set.

### Use Specific Model

```bash
# Use GPT-4 Turbo instead of default gpt-4o
python main.py --provider openai --model gpt-4-turbo

# Use Claude Opus instead of default Sonnet
python main.py --provider claude --model claude-3-opus-20240229

# Use older Gemini model
python main.py --provider gemini --model gemini-pro
```

### Adjust Temperature

```bash
# More creative responses (higher temperature)
python main.py --temperature 1.0

# More deterministic responses (lower temperature)
python main.py --temperature 0.3
```

### Combine Options

```bash
# Use GPT-4 Turbo with higher temperature
python main.py --provider openai --model gpt-4-turbo --temperature 1.0

# Use Claude Opus with lower temperature
python main.py --provider claude --model claude-3-opus-20240229 --temperature 0.5
```

## Programmatic Usage

You can also use the models programmatically in your own scripts:

```python
from legacyhelper.model.factory import ModelFactory
from legacyhelper.core.agent import Agent

# Create a model using the factory
model = ModelFactory.create('openai', model='gpt-4', temperature=0.7)

# Or auto-detect from environment
model = ModelFactory.create_from_env()

# Create an agent with the model
agent = Agent(model=model)

# Get a response
response = agent.run("How do I check disk space?")
print(response)
```

### Direct Model Instantiation

```python
from legacyhelper.model import OpenAIModel, ClaudeModel, GeminiModel

# OpenAI
openai_model = OpenAIModel(
    api_key='your-key',
    model='gpt-4',
    temperature=0.7
)

# Claude
claude_model = ClaudeModel(
    api_key='your-key',
    model='claude-3-5-sonnet-20241022',
    temperature=0.7
)

# Gemini
gemini_model = GeminiModel(
    api_key='your-key'
)

# Get responses
response = openai_model.get_response("Suggest a command")
```

## Model Recommendations

### For Best Quality
- **GPT-4o** (OpenAI) - Excellent reasoning, good at system administration
- **Claude 3.5 Sonnet** (Anthropic) - Strong at technical explanations

### For Speed
- **GPT-3.5-turbo** (OpenAI) - Fast and cost-effective
- **Gemini 2.0 Flash** (Google) - Very fast, good quality

### For Long Context
- **Claude 3.5 Sonnet** - 200k context window
- **GPT-4-turbo** - 128k context window

## Common Model Names

### OpenAI
- `gpt-4o` - Latest GPT-4 (default)
- `gpt-4-turbo` - GPT-4 with 128k context
- `gpt-4` - Standard GPT-4
- `gpt-3.5-turbo` - Fast and economical

### Anthropic Claude
- `claude-3-5-sonnet-20241022` - Latest Claude 3.5 (default)
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fastest

### Google Gemini
- `gemini-2.0-flash-exp` - Latest experimental (default)
- `gemini-pro-latest` - Latest stable
- `gemini-pro` - Standard model

## Environment Configuration

### Using .env File

Create a `.env` file in the project root:

```bash
# Choose one or more:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

Then load it before running:

```bash
source .env  # or use python-dotenv
python main.py
```

### Multiple API Keys

You can set multiple API keys and switch between them:

```bash
# Set all API keys
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
export GEMINI_API_KEY='AIza...'

# Then choose which to use
python main.py --provider openai
python main.py --provider claude
python main.py --provider gemini
```

## Troubleshooting

### "No API key found" Error

Make sure you've set the appropriate environment variable:

```bash
# Check which keys are set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
echo $GEMINI_API_KEY

# Or use the built-in checker
python main.py --list-providers
```

### Model Not Found

Make sure you're using a valid model name for the provider:

```bash
# Valid
python main.py --provider openai --model gpt-4

# Invalid
python main.py --provider openai --model claude-3-5-sonnet
```

### Import Errors

Ensure dependencies are installed:

```bash
uv sync
```

## Cost Considerations

Different providers have different pricing. As of late 2024:

### OpenAI (per 1M tokens)
- GPT-4o: $5 input / $15 output
- GPT-4-turbo: $10 input / $30 output
- GPT-3.5-turbo: $0.50 input / $1.50 output

### Anthropic
- Claude 3.5 Sonnet: $3 input / $15 output
- Claude 3 Opus: $15 input / $75 output
- Claude 3 Haiku: $0.25 input / $1.25 output

### Google Gemini
- Gemini 2.0 Flash: Free tier available
- Gemini Pro: $0.50 input / $1.50 output

Check providers' pricing pages for current rates.

## Performance Comparison

Based on our testing for system administration tasks:

| Provider | Speed | Quality | Context | Best For |
|----------|-------|---------|---------|----------|
| GPT-4o | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 128k | Complex debugging |
| Claude 3.5 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 200k | Technical docs |
| Gemini Flash | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 32k | Quick commands |
| GPT-3.5 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 16k | Simple queries |

## Architecture

All models implement the `BaseModel` interface:

```python
class BaseModel(ABC):
    @abstractmethod
    def get_response(self, prompt: str) -> str:
        pass
```

This makes it easy to:
- Switch between providers without changing code
- Add new providers in the future
- Test with mock models

## Adding More Providers

Want to add support for another provider? Check `legacyhelper/model/` for examples. The basic steps:

1. Create a new file (e.g., `mistral.py`)
2. Implement `BaseModel` interface
3. Add to `ModelFactory.MODELS`
4. Update documentation

See `CONTRIBUTING.md` for details.
