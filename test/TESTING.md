# LegacyHelper Testing Guide

## Quick Start

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest test/test_bash_tool.py -v
```

## Test Suite Overview

The test suite consists of 42 comprehensive tests organized into three main modules:

### 1. test_bash_tool.py (6 tests)
Tests for the bash command execution tool.

**Test Coverage:**
- Dangerous command blocking (rm -rf, shutdown, reboot, fork bomb)
- Safe command validation
- BashResult and ExecDeps model validation
- Command return codes and error handling

**Key Features Tested:**
- Security: Blocks dangerous commands at the tool level
- Safety: Allows safe commands to pass through
- Models: Validates Pydantic models for command results

### 2. test_system_logs.py (14 tests)
Tests for system log retrieval and shell history filtering.

**Test Coverage:**

**System Logs:**
- Current system log retrieval via journalctl
- Previous system log retrieval
- Exception handling for missing/unavailable logs

**Shell History:**
- Bash and Zsh history file parsing
- Security redaction of sensitive data:
  - Long tokens (32+ characters)
  - URL embedded credentials
  - High-entropy strings
- Path preservation (not redacting file paths)
- Output limiting with n parameter
- Empty line filtering

**Key Features Tested:**
- Security: Comprehensive redaction of secrets
- Usability: Proper history retrieval and filtering
- Safety: Preserves legitimate file paths

### 3. test_model_factory_new.py (22 tests)
Tests for the LLM model factory supporting multiple providers.

**Test Coverage:**

**Model Factory Creation:**
- Provider validation (gemini, openai, claude)
- Case-insensitive provider names
- Unsupported provider error handling
- Default model selection

**Environment-based Creation:**
- OPENAI_API_KEY priority (highest)
- ANTHROPIC_API_KEY priority (second)
- GEMINI_API_KEY priority (third)
- Missing API key error handling
- Custom parameter passing

**Utilities:**
- Provider listing
- Default model retrieval for each provider
- Case-insensitive lookups
- Class attribute consistency

**Key Features Tested:**
- Flexibility: Multiple provider support
- Robustness: Proper error handling and validation
- Usability: Sensible defaults and easy API

## Running Specific Test Groups

### Run only bash tool tests:
```bash
pytest test/test_bash_tool.py
```

### Run only system log tests:
```bash
pytest test/test_system_logs.py
```

### Run only model factory tests:
```bash
pytest test/test_model_factory_new.py
```

### Run a specific test class:
```bash
pytest test/test_system_logs.py::TestShellHistory -v
```

### Run a specific test:
```bash
pytest test/test_system_logs.py::TestShellHistory::test_get_filtered_shell_history_zsh -v
```

## Test Statistics

```
Total Tests: 42
All Passing: ✓
Execution Time: ~1.1 seconds

Test Distribution:
- Bash Tool: 6 tests (14%)
- System Logs: 14 tests (33%)
- Model Factory: 22 tests (53%)
```

## Pytest Configuration

Configuration is in `pytest.ini`:
- Test discovery patterns for Python files and classes
- Verbose output by default
- Short traceback format
- Warning disabling for cleaner output
- Test markers for categorization (unit, integration, slow, security)

## Fixtures

The test suite uses fixtures from `conftest.py`:
- `mock_env`: Mock environment variables
- `mock_subprocess`: Mock subprocess.run calls
- `mock_popen`: Mock subprocess.Popen calls
- `temp_home`: Create temporary home directory for testing
- `bash_tool_func`: Fixture providing bash tool function for testing

## Test Categories

Tests are organized by functionality:

### Security Tests
- Dangerous command blocking
- Sensitive data redaction
- Provider validation

### Functional Tests
- Command execution
- Log retrieval
- Model creation
- Parameter validation

### Edge Case Tests
- Empty inputs
- Missing files
- Invalid parameters
- Case sensitivity

## Adding New Tests

1. Create test file with `test_` prefix
2. Use descriptive class and method names
3. Follow the arrange-act-assert pattern
4. Use existing fixtures from conftest.py
5. Add docstrings explaining test purpose

Example:
```python
def test_feature_works_correctly(self):
    """Test that feature correctly processes input."""
    # Arrange
    input_data = "test"

    # Act
    result = function(input_data)

    # Assert
    assert result == "expected_output"
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run tests
  run: pytest test/ -v
```

## Troubleshooting

### Tests failing due to missing environment variables:
Some tests mock environment variables. If tests fail, ensure:
- No real API keys are being read
- Pytest is running in isolation
- conftest.py fixtures are being used correctly

### Tests failing due to file permissions:
Some tests use temporary directories. Ensure:
- Write permissions in /tmp
- Home directory is accessible
- pytest has proper permissions

### Mock-related failures:
If mock tests fail:
- Check that patches are applied to the correct module paths
- Verify mock assertions are using the correct call patterns
- Use `call_args` instead of string matching for complex assertions

## Performance

The test suite runs efficiently:
- Full suite: ~1.1 seconds
- Individual test file: < 0.5 seconds
- Suitable for fast feedback loops during development

## Best Practices

1. **Isolation**: Each test is independent
2. **Clarity**: Test names clearly describe what is being tested
3. **Maintainability**: Fixtures reduce code duplication
4. **Speed**: Tests run quickly for fast feedback
5. **Comprehensiveness**: Cover happy paths and edge cases

## Future Improvements

- [ ] Add pytest-cov for coverage reports
- [ ] Add performance benchmarks
- [ ] Add integration tests for full workflows
- [ ] Add stress tests for concurrent operations
- [ ] Add property-based tests with hypothesis
