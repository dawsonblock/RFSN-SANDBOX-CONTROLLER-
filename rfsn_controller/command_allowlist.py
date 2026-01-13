"""Command allowlist for sandbox security.

Only approved commands can be executed in the sandbox.
This prevents malicious or dangerous operations.
"""

from typing import Set, List, Optional

# Approved commands that can be executed in the sandbox
ALLOWED_COMMANDS: Set[str] = {
    "git",
    "pytest",
    "python",
    "python3",
    "pip",
    "pip3",
    "bash",
    "sh",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "ls",
    "cd",
    "pwd",
    "echo",
    "mkdir",
    "rm",  # Only for cleanup within sandbox
    "cp",
    "mv",
    "touch",
    "chmod",
    "sed",
    "awk",
    "sort",
    "uniq",
    "wc",
    "diff",
    "patch",
}

# Commands that are explicitly blocked
BLOCKED_COMMANDS: Set[str] = {
    "curl",
    "wget",
    "ssh",
    "scp",
    "rsync",
    "nc",
    "netcat",
    "telnet",
    "ftp",
    "sftp",
    "sudo",
    "su",
    "docker",
    "kubectl",
    "systemctl",
    "service",
    "crontab",
    "at",
    "nohup",
    "screen",
    "tmux",
}

# Dangerous flags that should be blocked
BLOCKED_FLAGS: List[str] = [
    "--rm",  # rm -rf
    "-rf",   # rm -rf
    "rm -rf",
    "rm -r",
    "rm -f",
    "/dev/",
    "/proc/",
    "/sys/",
    "/etc/passwd",
    "/etc/shadow",
    "~/.ssh",
    "/.ssh",
    "id_rsa",
    "id_ed25519",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
]


def is_command_allowed(command: str) -> tuple[bool, Optional[str]]:
    """Check if a command is allowed to execute.

    Args:
        command: The command string to check.

    Returns:
        (is_allowed, reason) tuple where reason is None if allowed.
    """
    # Extract the base command (first word)
    parts = command.strip().split()
    if not parts:
        return False, "Empty command"

    base_cmd = parts[0]

    # Check if command is explicitly blocked
    if base_cmd in BLOCKED_COMMANDS:
        return False, f"Command '{base_cmd}' is blocked"

    # Check if command is in allowlist
    if base_cmd not in ALLOWED_COMMANDS:
        return False, f"Command '{base_cmd}' is not in allowlist"

    # Check for dangerous flags
    command_lower = command.lower()
    for flag in BLOCKED_FLAGS:
        if flag.lower() in command_lower:
            return False, f"Dangerous flag detected: {flag}"

    # Check for suspicious patterns
    if "curl" in command_lower or "wget" in command_lower:
        return False, "Network access blocked"

    if "ssh" in command_lower or "scp" in command_lower:
        return False, "SSH access blocked"

    if "sudo" in command_lower or "su " in command_lower:
        return False, "Privilege escalation blocked"

    # Check for API key exposure attempts
    if any(key in command for key in ["API_KEY", "SECRET", "TOKEN", "PASSWORD"]):
        if "echo" in command_lower or "cat" in command_lower or "print" in command_lower:
            return False, "Potential credential exposure blocked"

    return True, None


def get_allowed_commands() -> Set[str]:
    """Get the set of allowed commands."""
    return ALLOWED_COMMANDS.copy()


def get_blocked_commands() -> Set[str]:
    """Get the set of blocked commands."""
    return BLOCKED_COMMANDS.copy()
