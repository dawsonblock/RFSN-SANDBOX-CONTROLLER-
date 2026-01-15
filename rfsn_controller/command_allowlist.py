"""Command allowlist for sandbox security.

Only approved commands can be executed in the sandbox.
This prevents malicious or dangerous operations.
"""

from typing import Set, List, Optional

# Approved commands that can be executed in the sandbox
ALLOWED_COMMANDS: Set[str] = {
    # Version control
    "git",
    
    # Python
    "pytest",
    "python",
    "python3",
    "pip",
    "pip3",
    "pipenv",
    "poetry",
    "ruff",  # Linter
    "mypy",  # Type checker
    "black",  # Formatter
    "flake8",  # Linter
    "pylint",  # Linter
    
    # Node.js / JavaScript / TypeScript
    "node",
    "npm",
    "yarn",
    "pnpm",
    "npx",
    "bun",
    "tsc",  # TypeScript compiler
    "jest",  # Test framework
    "mocha",  # Test framework
    "eslint",  # Linter
    "prettier",  # Formatter
    
    # Rust
    "cargo",
    "rustc",
    "rustup",
    "rustfmt",  # Formatter
    "clippy",  # Linter
    
    # Go
    "go",
    "gofmt",  # Formatter
    "golint",  # Linter
    
    # Java
    "mvn",
    "gradle",
    "javac",
    "java",
    
    # .NET / C#
    "dotnet",
    
    # Ruby
    "ruby",
    "gem",
    "bundle",
    "rake",
    "rspec",
    
    # Unix utilities (no cd - commands run from repo root)
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "ls",
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
    "tar",  # Archive extraction
    "unzip",  # Archive extraction
    "make",  # Build automation
}

# Commands that are explicitly blocked
BLOCKED_COMMANDS: Set[str] = {
    "cd",  # Commands run from repo root; cd is not needed and causes confusion
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

# Shell metacharacters that enable command chaining or injection
BLOCKED_METACHARACTERS: List[str] = [
    ";",  # Command separator
    "|",  # Pipe
    "&",  # Background
    ">",  # Output redirect
    "<",  # Input redirect
    "$(",  # Command substitution
    "`",  # Backtick command substitution
    "\n",  # Newline for command chaining
    "\\",  # Escape character
    "&&",  # AND operator
    "||",  # OR operator
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

    # Check for cd command anywhere
    if "cd" in parts:
        return False, "cd command is blocked - commands run from repo root"

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

    # Check for shell metacharacters
    for meta in BLOCKED_METACHARACTERS:
        if meta in command:
            return False, f"Shell metacharacter blocked: {repr(meta)}"

    # Check for API key exposure attempts
    sensitive_keys = ["API_KEY", "SECRET", "TOKEN", "PASSWORD"]
    if any(key in command for key in sensitive_keys):
        if "echo" in command_lower or "cat" in command_lower or "print" in command_lower:
            return False, "Potential credential exposure blocked"

    return True, None


def get_allowed_commands() -> Set[str]:
    """Get the set of allowed commands."""
    return ALLOWED_COMMANDS.copy()


def get_blocked_commands() -> Set[str]:
    """Get the set of blocked commands."""
    return BLOCKED_COMMANDS.copy()
