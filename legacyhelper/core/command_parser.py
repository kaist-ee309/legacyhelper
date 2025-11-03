"""Command parsing and extraction utilities."""
import re
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    """Represents a parsed command with metadata."""

    command: str
    description: str
    confidence: float  # 0.0 to 1.0
    is_safe: bool
    warnings: List[str]


class CommandParser:
    """Parser for extracting and analyzing commands from AI responses."""

    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\s+/',  # Recursive delete from root
        r'\bdd\s+if=/dev/',  # Direct disk operations
        r'\b:\(\)\{\s*:\|:&\s*\};:',  # Fork bomb
        r'\bmkfs\.',  # Format filesystem
        r'\bshred\b',  # Secure delete
        r'>\s*/dev/sd[a-z]',  # Write to block device
        r'\bcurl\s+.*\|\s*bash',  # Pipe to bash
        r'\bwget\s+.*\|\s*sh',  # Pipe to shell
    ]

    # Patterns for extracting commands
    CODE_BLOCK_PATTERN = r'```(?:bash|sh|shell)?\n(.*?)```'
    INLINE_CODE_PATTERN = r'`([^`]+)`'
    COMMAND_PREFIX_PATTERN = r'^\s*[$#]\s*(.+)$'

    def __init__(self) -> None:
        """Initialize the command parser."""
        self.dangerous_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]

    def extract_commands(self, text: str) -> List[ParsedCommand]:
        """Extract all potential commands from text.

        Args:
            text: The text to parse

        Returns:
            List of parsed commands with metadata
        """
        commands = []

        # Extract from code blocks (highest confidence)
        code_blocks = re.findall(self.CODE_BLOCK_PATTERN, text, re.DOTALL)
        for block in code_blocks:
            for line in block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    parsed = self._parse_command(line, confidence=0.9)
                    if parsed:
                        commands.append(parsed)

        # Extract from inline code (medium confidence)
        inline_codes = re.findall(self.INLINE_CODE_PATTERN, text)
        for code in inline_codes:
            code = code.strip()
            if self._looks_like_command(code):
                parsed = self._parse_command(code, confidence=0.7)
                if parsed:
                    commands.append(parsed)

        # Extract command-like patterns (lower confidence)
        for line in text.split('\n'):
            match = re.match(self.COMMAND_PREFIX_PATTERN, line)
            if match:
                cmd = match.group(1).strip()
                if cmd not in [c.command for c in commands]:  # Avoid duplicates
                    parsed = self._parse_command(cmd, confidence=0.6)
                    if parsed:
                        commands.append(parsed)

        return commands

    def _parse_command(self, command: str, confidence: float) -> Optional[ParsedCommand]:
        """Parse a single command string.

        Args:
            command: The command string
            confidence: Initial confidence score

        Returns:
            ParsedCommand or None if invalid
        """
        command = command.strip()
        original_command = command

        # Check for sudo before removing it
        has_sudo = command.startswith('sudo ')

        # Remove common prefixes
        for prefix in ['$', '#']:
            if command.startswith(prefix):
                command = command[len(prefix):].strip()
                break

        # Remove sudo prefix
        if command.startswith('sudo'):
            command = command[4:].strip()

        if not command or len(command) < 2:
            return None

        # Check safety
        is_safe = True
        warnings = []

        for pattern in self.dangerous_regex:
            if pattern.search(command):
                is_safe = False
                warnings.append("⚠️  Potentially dangerous command detected")
                confidence *= 0.5  # Reduce confidence for dangerous commands
                break

        # Additional safety checks
        if 'rm' in command:
            warnings.append("💡 This command deletes files - review carefully")
        if 'chmod' in command or 'chown' in command:
            warnings.append("💡 This command modifies permissions")
        if has_sudo:
            warnings.append("💡 This command requires elevated privileges")

        # Generate description
        description = self._generate_description(command)

        return ParsedCommand(
            command=command,
            description=description,
            confidence=confidence,
            is_safe=is_safe,
            warnings=warnings
        )

    def _looks_like_command(self, text: str) -> bool:
        """Check if text looks like a shell command.

        Args:
            text: The text to check

        Returns:
            True if it looks like a command
        """
        # Strip common prefixes for checking
        cleaned_text = text.lstrip('$# ').strip()

        # Common command patterns
        command_indicators = [
            text.startswith('$ '),  # Shell prompt
            text.startswith('# '),  # Root prompt
            cleaned_text.startswith('sudo '),
            cleaned_text.startswith('cd '),
            cleaned_text.startswith('ls '),
            cleaned_text.startswith('cat '),
            cleaned_text.startswith('grep '),
            cleaned_text.startswith('find '),
            cleaned_text.startswith('ps '),
            cleaned_text.startswith('df '),
            cleaned_text.startswith('du '),
            cleaned_text.startswith('top'),
            cleaned_text.startswith('htop'),
            cleaned_text.startswith('systemctl '),
            cleaned_text.startswith('journalctl '),
            ' | ' in text,  # Piped commands
            ' && ' in text,  # Chained commands
            re.search(r'^[a-z_]+\s+', cleaned_text) is not None,  # Starts with command name
        ]

        return any(command_indicators) and len(text) < 500

    def _generate_description(self, command: str) -> str:
        """Generate a human-readable description of what the command does.

        Args:
            command: The command string

        Returns:
            Description string
        """
        # Simple heuristic-based descriptions
        descriptions = {
            r'^df\b': "Check disk space usage",
            r'^du\b': "Check directory space usage",
            r'^ls\b': "List directory contents",
            r'^cat\b': "Display file contents",
            r'^grep\b': "Search for text patterns",
            r'^find\b': "Search for files",
            r'^ps\b': "List running processes",
            r'^top\b': "Monitor system processes",
            r'^free\b': "Check memory usage",
            r'^systemctl\s+status': "Check service status",
            r'^journalctl\b': "View system logs",
            r'^tail\b': "Display end of file",
            r'^head\b': "Display beginning of file",
            r'^chmod\b': "Change file permissions",
            r'^chown\b': "Change file ownership",
            r'^mkdir\b': "Create directory",
            r'^rm\b': "Remove files or directories",
            r'^cp\b': "Copy files",
            r'^mv\b': "Move/rename files",
        }

        for pattern, description in descriptions.items():
            if re.search(pattern, command):
                return description

        return "Execute shell command"

    def get_best_command(self, text: str) -> Optional[ParsedCommand]:
        """Extract the most likely command from text.

        Args:
            text: The text to parse

        Returns:
            The best parsed command or None
        """
        commands = self.extract_commands(text)
        if not commands:
            return None

        # Sort by confidence and safety
        commands.sort(key=lambda c: (c.is_safe, c.confidence), reverse=True)
        return commands[0]
