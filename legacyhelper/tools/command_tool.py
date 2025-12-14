"""Command tool for running bash commands and retrieving system logs."""
import os
import re
import subprocess
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_ai import RunContext, Tool
from pydantic_ai import FunctionToolset

MAX_OUTPUT_CHARS = 50_000

class BashResult(BaseModel):
    """Contains the result of a bash command execution."""
    stdout: str
    stderr: str
    returncode: int

    # if response is way too long, command agent to invoke another alternative.
    @field_validator("stdout", "stderr")
    @classmethod
    def limit_output(cls, v: str) -> str:
        """if command output is observed to be too long, it rejects it."""
        if len(v) > MAX_OUTPUT_CHARS:
            return (
                "⚠️ Context too long. "
                "Command output exceeds limit. "
                "Use a different method (e.g. filtering, paging, or summary)."
            )
        return v

def bash_tool(command: str) -> BashResult:
    """
    Run a bash command on the local machine.

    Parameters
    ----------
    command:
        The shell command to execute (read-only commands only).
    """
    # simple safety guard example (extend this a lot in real code!)
    forbidden = ["rm -rf", "shutdown", "reboot", ":(){:|:&};:"]
    if any(f in command for f in forbidden):
        return BashResult(
            stdout="",
            stderr="Blocked dangerous command",
            returncode=1,
        )

    if command.startswith("sudo"):
        return BashResult(
            stdout="",
            stderr="The command requires superuser privalige. Abort.",
            returncode=1,
        )

    print(f"[TOOL CALL]: command={command}")
    with subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        out, err = proc.communicate()
        return BashResult(stdout=out, stderr=err, returncode=proc.returncode)


system_log_toolset = FunctionToolset(tools=[])


@system_log_toolset.tool
def get_current_system_log() -> str:
    """
    Get the system log for the current boot.
    Call when "error" level system log is needed.
    """
    command = ["journalctl", "-p", "3", "-xb", "--no-pager"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as exc:  # pylint: disable=broad-except
        return str(exc)


@system_log_toolset.tool
def get_previous_system_log() -> str:
    """
    Get the system log for the previous boot.
    Call when system log for previous boot is required or booting related problem.
    """
    command = ["journalctl", "-p", "3", "-xb", "-1", "--no-pager"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as exc:  # pylint: disable=broad-except
        return str(exc)


@system_log_toolset.tool
def get_filtered_shell_history(ctx: RunContext[None], n: int = 10) -> str:
    """
    Reads the last n lines of the current shell history i.e. command line history
    Call when shell history or command history need to be known for trouble shooting

    n is a positive integer (default: 10)
    """
    # Suppress unused argument warning - ctx is required by pydantic_ai interface
    _ = ctx

    # 1. Locate History File
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    history_path = None

    # Prioritize shell specific history, fall back to existence check
    candidates = []
    if "zsh" in shell:
        candidates.append(home / ".zsh_history")
    elif "bash" in shell:
        candidates.append(home / ".bash_history")
    candidates.extend([home / ".zsh_history", home / ".bash_history"])

    for path in candidates:
        if path.exists():
            history_path = path
            break

    if not history_path:
        return ""

    # 2. Define Redaction Logic
    def redact_line(text: str) -> str:
        # Keywords to look for (case-insensitive)
        sensitive_keys = (
            r'(api[_-]?key|password|secret|token|credential|'
            r'auth|passwd|pwd|private[_-]?key|bearer|authorization)'
        )

        # A. Environment Variables (export VAR=value, VAR=value)
        # Matches: KEYWORD=value, KEYWORD="value"
        text = re.sub(
            rf'(export\s+)?((?:\w*?{sensitive_keys}\w*?))(\s*=\s*)(["\']?)([^"\'\s]+)(\4)',
            r'\1\2\3\4***REDACTED***\6',
            text, flags=re.IGNORECASE
        )

        # B. CLI Arguments (--key=value, --key value)
        # Matches: --key=value
        text = re.sub(
            rf'(--{sensitive_keys})\s*=\s*(["\']?)([^"\'\s]+)(\2)',
            r'\1=***REDACTED***',
            text, flags=re.IGNORECASE
        )
        # Matches: --key value
        text = re.sub(
            rf'(--{sensitive_keys})\s+(["\']?)([^"\'\s]+)(\2)',
            r'\1 ***REDACTED***',
            text, flags=re.IGNORECASE
        )

        # C. URLs with credentials (http://user:pass@host)
        text = re.sub(
            r'(https?://)([^:/\s]+):([^@/\s]+)@',
            r'\1***REDACTED***@',
            text
        )

        # D. High Entropy/Long Tokens (32+ alphanumeric chars, conservative match)
        # Excludes paths (/) or URLs (://)
        def replace_token(match):
            token = match.group(1)
            context = text[max(0, match.start()-20):min(len(text), match.end()+20)]
            if '/' in context or '://' in context or '@' in context:
                return token
            return '***REDACTED***'

        text = re.sub(r'\b([a-zA-Z0-9]{32,})\b', replace_token, text)

        return text

    # 3. Read and Process File
    filtered_lines = []
    try:
        # Use errors='ignore' to handle potential binary garbage in history files
        with open(history_path, "r", encoding="utf-8", errors="ignore") as f:
            # Efficiently read last n lines without loading whole file if possible,
            # but standard readlines() is safer for variable line lengths.
            all_lines = f.readlines()
            recent_lines = all_lines[-n:] if n < len(all_lines) else all_lines

        for line in recent_lines:
            line = line.strip()
            if not line:
                continue

            # Zsh Extended History format: ": timestamp:0;command"
            if line.startswith(":") and ";" in line:
                parts = line.split(";", 1)
                if len(parts) > 1:
                    line = parts[1]

            filtered_lines.append(redact_line(line))

    except (OSError, PermissionError):
        return "Error reading history file."

    # Return most recent last
    return "\n".join(filtered_lines)


SYSTEM_LOG_TOOLSET = system_log_toolset

bash_tool = Tool(
    bash_tool,
    name="bash",
    description=("Run safe bash commands in the configured working directory."
                 "The tool rejects command response beyond given max_length."
                 "Devise a command efficiently so no redundant retries as possible."),
    takes_ctx=False,
)
