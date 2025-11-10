"""Utility module for reading shell history."""
import os
import re
from pathlib import Path
from typing import List, Optional


def get_shell_history_path() -> Optional[Path]:
    """Get the path to the shell history file based on the current shell.

    Returns:
        Path to history file or None if not found
    """
    shell = os.environ.get("SHELL", "")
    home = Path.home()

    # Check for zsh
    if "zsh" in shell:
        history_path = home / ".zsh_history"
        if history_path.exists():
            return history_path

    # Check for bash
    if "bash" in shell:
        history_path = home / ".bash_history"
        if history_path.exists():
            return history_path

    # Fallback: try common history locations
    for hist_path in [home / ".zsh_history", home / ".bash_history"]:
        if hist_path.exists():
            return hist_path

    return None


def filter_sensitive_data(entry: str) -> str:
    """Filter out sensitive information from a history entry.

    Removes:
    - API keys, tokens, passwords in environment variables
    - Command-line arguments with sensitive values
    - URLs with embedded credentials
    - Long alphanumeric strings that might be secrets

    Args:
        entry: The history entry to filter

    Returns:
        Filtered history entry with sensitive data replaced
    """
    if not entry:
        return entry

    filtered = entry

    # List of sensitive keywords (case-insensitive)
    # Use patterns that match common variations
    sensitive_patterns = [
        r'api[_-]?key', r'password', r'secret', r'token', r'credential',
        r'auth', r'apikey', r'passwd', r'pwd', r'private[_-]?key',
        r'access[_-]?token', r'refresh[_-]?token', r'session[_-]?id',
        r'bearer', r'authorization'
    ]

    # Pattern for environment variable assignments: VAR=value or export VAR=value
    # Handles: export VAR=value, VAR=value, VAR="value", VAR='value'
    # Also handles compound names like API_KEY, SECRET_KEY, etc.
    def replace_env_var(match):
        prefix = match.group(1) or ''
        var_name = match.group(2)
        return f'{prefix}{var_name}=***REDACTED***'

    # Build a pattern that matches environment variables with the sensitive keywords
    # This handles: API_KEY, SECRET_KEY, OPENAI_API_KEY, etc.
    for pattern in sensitive_patterns:
        # Match environment variable - allow underscores and uppercase letters after the keyword
        # Pattern: (export )?KEYWORD(_[A-Z_]+)? = value
        env_pattern = rf'(export\s+)?({pattern}(?:_[A-Z_]+)?)\s*=\s*["\']?([^"\'\s]+)["\']?'
        filtered = re.sub(env_pattern, replace_env_var, filtered, flags=re.IGNORECASE)

    # Pattern for command-line arguments: --key=value, --key value
    def replace_arg_eq(match):
        arg_name = match.group(1)
        return f'--{arg_name}=***REDACTED***'

    def replace_arg_space(match):
        arg_name = match.group(1)
        return f'--{arg_name} ***REDACTED***'

    for pattern in sensitive_patterns:
        # Match: --keyword=value or --keyword="value"
        arg_pattern = rf'--({pattern})\s*=\s*["\']?([^"\'\s]+)["\']?'
        filtered = re.sub(arg_pattern, replace_arg_eq, filtered, flags=re.IGNORECASE)

        # Match: --keyword value or --keyword "value"
        arg_pattern = rf'--({pattern})\s+["\']?([^"\'\s]+)["\']?'
        filtered = re.sub(arg_pattern, replace_arg_space, filtered, flags=re.IGNORECASE)

    # Pattern for HTTP headers: Authorization: Bearer token, X-API-Key: value, etc.
    # Only replace the value part, keep the header name
    header_patterns = [
        (r'authorization\s*:\s*', r'bearer\s+[a-zA-Z0-9\-_\.]+'),
        (r'x-api-key\s*:\s*', r'[^"\'\s]+'),
        (r'x-auth-token\s*:\s*', r'[^"\'\s]+'),
    ]
    for header_name, header_value in header_patterns:
        # Match header name and value, replace only the value
        pattern = rf'({header_name})({header_value})'
        filtered = re.sub(pattern, r'\1***REDACTED***', filtered, flags=re.IGNORECASE)

    # Pattern for URLs with credentials: http://user:pass@host or https://user:pass@host
    url_pattern = r'(https?://)([^:/\s]+):([^@/\s]+)@'
    filtered = re.sub(url_pattern, r'\1***REDACTED***@', filtered)

    # Pattern for long alphanumeric strings that might be API keys/tokens
    # Look for strings of 32+ alphanumeric characters that aren't file paths or URLs
    # This is conservative - only match standalone tokens
    def replace_long_token(match):
        token = match.group(1)
        start = max(0, match.start() - 20)
        end = min(len(filtered), match.end() + 20)
        context = filtered[start:end]

        # Don't replace if it looks like:
        # - Part of a file path (contains /)
        # - Part of a URL (contains :// or @)
        # - Part of a hash in a path
        if '/' in context or '://' in context or '@' in context:
            return token
        return '***REDACTED***'

    # Match 32+ alphanumeric characters, but be conservative
    long_token_pattern = r'\b([a-zA-Z0-9]{32,})\b'
    filtered = re.sub(long_token_pattern, replace_long_token, filtered)

    return filtered


def read_recent_history(count: int = 10) -> List[str]:
    """Read recent shell history entries.

    Args:
        count: Number of recent history entries to read (default: 10)

    Returns:
        List of history entries (most recent first)
    """
    history_path = get_shell_history_path()
    if history_path is None:
        return []

    try:
        with open(history_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Get the last 'count' lines (most recent)
        recent_lines = lines[-count:] if len(lines) > count else lines

        # Clean up zsh history format (remove timestamps)
        cleaned_history = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue

            # Zsh history format: ": timestamp:0;command"
            if line.startswith(":") and ":" in line[1:]:
                # Extract command after the second colon and semicolon
                parts = line.split(";", 1)
                if len(parts) > 1:
                    line = parts[1]

            # Skip empty lines after cleaning
            if line:
                # Filter sensitive data before adding to history
                filtered_line = filter_sensitive_data(line)
                cleaned_history.append(filtered_line)

        # Return in reverse order (most recent first)
        return list(reversed(cleaned_history[-count:]))

    except (IOError, OSError, PermissionError):
        return []


def format_history_context(history: List[str]) -> str:
    """Format history entries as a context string for the LLM.

    Args:
        history: List of history entries

    Returns:
        Formatted context string
    """
    if not history:
        return ""

    lines = ["Recent shell history (most recent first):"]
    for i, entry in enumerate(history, 1):
        lines.append(f"{i}. {entry}")

    return "\n".join(lines)
