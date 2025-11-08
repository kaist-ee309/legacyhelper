"""Utility module for reading shell history."""
import os
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
                cleaned_history.append(line)
        
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

