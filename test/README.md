# Test Suite for LegacyHelper

This directory contains the comprehensive test suite for the LegacyHelper project, built with pytest.

## Project Structure

```
test/
├── conftest.py                  # Shared pytest fixtures and configuration
├── test_bash_tool.py           # Tests for bash command execution
├── test_system_logs.py         # Tests for system log retrieval and filtering
├── test_model_factory_new.py   # Tests for LLM model factory
└── README.md                    # This file
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest test/test_bash_tool.py
```

### Run specific test class
```bash
pytest test/test_bash_tool.py::TestBashTool
```

### Run specific test
```bash
pytest test/test_bash_tool.py::TestBashTool::test_bash_tool_success
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage report
```bash
pytest --cov=legacyhelper --cov-report=html
```

### Run with detailed output and print statements
```bash
pytest -vv -s
```

## Test Categories

### test_bash_tool.py
Tests for the bash command execution tool:
- Successful command execution
- Error handling
- Dangerous command blocking (rm -rf, shutdown, reboot, fork bomb)
- Safe command allowance
- Model validation

### test_system_logs.py
Tests for system log retrieval and shell history filtering:
- Current system log retrieval via journalctl
- Previous system log retrieval
- Shell history retrieval (bash and zsh)
- Security redaction of sensitive data:
  - API keys
  - Passwords
  - Tokens (32+ character strings)
  - URL credentials
  - Environment variable secrets
- Path preservation (not redacting file paths)
- Output limiting with n parameter

### test_model_factory_new.py
Tests for the LLM model factory:
- Creating models for different providers (Gemini, OpenAI, Claude)
- Custom model name support
- Provider validation
- Case-insensitive provider names
- Default model selection
- Creating from environment variables with priority handling
- Utility methods (list_providers, get_default_model)

## Fixtures

### conftest.py
Provides reusable fixtures:
- `mock_env`: Mock environment variables
- `mock_subprocess`: Mock subprocess.run calls
- `mock_popen`: Mock subprocess.Popen calls
- `temp_home`: Create temporary home directory for testing

## Development Guidelines

### Adding New Tests
1. Create test files with `test_` prefix
2. Use descriptive test names that explain what is being tested
3. Use fixtures from conftest.py for common setup
4. Follow the arrange-act-assert pattern
5. Add docstrings explaining the test purpose

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<Feature>`
- Test methods: `test_<what_is_being_tested>`

Example:
```python
class TestBashTool:
    def test_bash_tool_blocks_dangerous_commands(self):
        """Test that dangerous commands are properly blocked."""
        # arrange
        dangerous_command = "rm -rf /"

        # act
        result = bash_tool(dangerous_command)

        # assert
        assert result.returncode == 1
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines. Recommended configuration:

```yaml
# Example GitHub Actions
- name: Run tests
  run: pytest --cov=legacyhelper
```

## Test Coverage Goals

Target areas for testing:
- [ ] All tool functions in legacyhelper/tools/
- [ ] All model factory methods
- [ ] Command parsing and validation
- [ ] Security features (redaction, dangerous command blocking)
- [ ] Error handling and exceptions

## Known Limitations

- Tests that depend on actual system logs require mocking
- Shell history tests use temporary directories
- API calls are mocked to avoid external dependencies
- Some edge cases may require additional testing

## Future Improvements

- Add integration tests for full workflow
- Add performance tests for large command outputs
- Add more edge case tests
- Add stress tests for concurrent operations
