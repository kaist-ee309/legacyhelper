# LegacyHelper Quick Start Guide

Get started with LegacyHelper in 5 minutes!

## Prerequisites

- Python 3.11+
- `uv` package manager
- Google Gemini API key

## Setup (2 minutes)

```bash
# 1. Clone the repository (if not already done)
cd legacyhelper

# 2. Sync dependencies
uv sync

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Set your API key
export GEMINI_API_KEY='your-gemini-api-key-here'
```

## Quick Test (1 minute)

Verify everything works without using the full TUI:

```bash
# Test command parser and executor
python demo_parser.py

# Test TUI initialization
python test_tui.py

# Test async conversation handling (NEW!)
python test_conversation.py

# Run unit tests
pytest
```

You should see:
- ✓ Command parsing demo with examples
- ✓ Command execution examples
- ✓ Dangerous command detection
- ✓ Async operations working correctly
- ✓ 31 tests passing

## Run the TUI (30 seconds)

```bash
# Auto-detect which API key is set
python main.py

# Or choose a specific provider
python main.py --provider openai
python main.py --provider claude
python main.py --provider gemini

# See all options
python main.py --list-providers
```

You'll see a sophisticated terminal interface with:
- Message history panel
- Input field at the bottom
- Status bar at the very bottom
- Header with app title

## Try These Queries

Once the TUI is running, try asking:

1. **System Information**
   - "How do I check disk space?"
   - "Show me memory usage"
   - "What processes are running?"

2. **Troubleshooting**
   - "My system is slow, what should I check?"
   - "How do I view system logs?"
   - "Check if a service is running"

3. **File Operations**
   - "How do I find large files?"
   - "Show me recent log entries"
   - "List files modified today"

## What Happens Next

When the AI suggests a command:

1. **Command appears in a preview box** with:
   - Syntax-highlighted command
   - Description of what it does
   - Safety warnings (if applicable)

2. **You have three options**:
   - ✓ **Execute**: Run the command
   - ✗ **Reject**: Dismiss the suggestion
   - ✎ **Modify**: Edit before running

3. **Results are displayed** with:
   - Command output
   - Exit code
   - Error messages (if any)

## Keyboard Shortcuts

- `Enter` - Send message
- `Ctrl+C` or `Ctrl+D` - Quit
- `Ctrl+L` - Clear conversation
- `Tab` - Navigate between elements

## Safety Features

LegacyHelper protects you from dangerous commands:

- ⚠️ **Detects**: `rm -rf /`, `dd`, `mkfs`, etc.
- 💡 **Warns about**: `sudo`, `chmod`, `rm`
- 🛡️ **Requires confirmation** for dangerous operations
- ⏱️ **30-second timeout** prevents hanging

## Tips

1. **Be specific** in your questions
   - Good: "How do I check disk space on /home?"
   - Bad: "disk"

2. **Review commands** before executing
   - Always check what the command does
   - Look for warnings

3. **Use the modify button** to:
   - Change paths
   - Adjust options
   - Make safer versions

4. **Test safely**:
   ```bash
   # Commands that are always safe to try:
   df -h           # Disk space
   free -h         # Memory usage
   uptime          # System uptime
   date            # Current date/time
   ```

## Troubleshooting

### "Please set the GEMINI_API_KEY environment variable"

```bash
export GEMINI_API_KEY='your-key-here'
# Verify it's set
echo $GEMINI_API_KEY
```

### TUI not starting

```bash
# Re-sync dependencies
uv sync

# Test initialization
python test_tui.py
```

### Command not executing

- Check if the command exists on your system
- Some commands may require elevated privileges
- Review safety warnings

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CHANGELOG.md](CHANGELOG.md) for technical details
- Run `pytest -v` to see all tests
- Explore the code in `legacyhelper/` directory

## Getting Help

If you encounter issues:
1. Run `python test_tui.py` to verify setup
2. Check the Troubleshooting section in README.md
3. Review error messages carefully
4. Ensure all dependencies are installed: `uv sync`

---

**Ready to troubleshoot?** Run `python main.py` and start chatting with your AI assistant!
