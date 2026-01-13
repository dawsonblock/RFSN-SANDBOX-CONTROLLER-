"""Project type detection for automatic setup and testing.

Detects project type from repository structure and provides
appropriate setup and test commands.
"""

import os
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class ProjectType:
    """Detected project type with setup and test commands."""
    
    name: str
    setup_commands: List[str]
    test_commands: List[str]
    language: str


def detect_project_type(repo_dir: str) -> Optional[ProjectType]:
    """Detect the project type from repository structure.

    Args:
        repo_dir: Path to the repository.

    Returns:
        ProjectType if detected, None otherwise.
    """
    # Check for Python projects
    python_type = _detect_python_project(repo_dir)
    if python_type:
        return python_type
    
    # Check for Node.js projects
    node_type = _detect_node_project(repo_dir)
    if node_type:
        return node_type
    
    # Check for Rust projects
    rust_type = _detect_rust_project(repo_dir)
    if rust_type:
        return rust_type
    
    # Check for Go projects
    go_type = _detect_go_project(repo_dir)
    if go_type:
        return go_type
    
    return None


def _detect_python_project(repo_dir: str) -> Optional[ProjectType]:
    """Detect Python project type."""
    has_pyproject = os.path.exists(os.path.join(repo_dir, "pyproject.toml"))
    has_setup_py = os.path.exists(os.path.join(repo_dir, "setup.py"))
    has_requirements = os.path.exists(os.path.join(repo_dir, "requirements.txt"))
    has_pipfile = os.path.exists(os.path.join(repo_dir, "Pipfile"))
    has_poetry = os.path.exists(os.path.join(repo_dir, "poetry.lock"))
    
    if not (has_pyproject or has_setup_py or has_requirements or has_pipfile or has_poetry):
        return None
    
    setup_commands = []
    
    # Determine setup command
    if has_pyproject:
        setup_commands.append("pip install -e .")
    elif has_setup_py:
        setup_commands.append("pip install -e .")
    
    if has_requirements:
        setup_commands.append("pip install -r requirements.txt")
    elif has_pipfile:
        setup_commands.append("pipenv install")
    elif has_poetry:
        setup_commands.append("poetry install")
    
    # Determine test command
    test_commands = []
    
    # Check for pytest
    if os.path.exists(os.path.join(repo_dir, "pytest.ini")) or \
       os.path.exists(os.path.join(repo_dir, "pyproject.toml")) or \
       os.path.exists(os.path.join(repo_dir, "setup.cfg")):
        test_commands.append("pytest -q")
    else:
        # Default to pytest
        test_commands.append("pytest -q")
    
    return ProjectType(
        name="python",
        setup_commands=setup_commands,
        test_commands=test_commands,
        language="python"
    )


def _detect_node_project(repo_dir: str) -> Optional[ProjectType]:
    """Detect Node.js project type."""
    has_package_json = os.path.exists(os.path.join(repo_dir, "package.json"))
    
    if not has_package_json:
        return None
    
    setup_commands = ["npm install"]
    test_commands = ["npm test"]
    
    # Check for yarn
    if os.path.exists(os.path.join(repo_dir, "yarn.lock")):
        setup_commands = ["yarn install"]
        test_commands = ["yarn test"]
    
    # Check for pnpm
    if os.path.exists(os.path.join(repo_dir, "pnpm-lock.yaml")):
        setup_commands = ["pnpm install"]
        test_commands = ["pnpm test"]
    
    return ProjectType(
        name="node",
        setup_commands=setup_commands,
        test_commands=test_commands,
        language="javascript"
    )


def _detect_rust_project(repo_dir: str) -> Optional[ProjectType]:
    """Detect Rust project type."""
    has_cargo_toml = os.path.exists(os.path.join(repo_dir, "Cargo.toml"))
    
    if not has_cargo_toml:
        return None
    
    setup_commands = ["cargo build"]
    test_commands = ["cargo test"]
    
    return ProjectType(
        name="rust",
        setup_commands=setup_commands,
        test_commands=test_commands,
        language="rust"
    )


def _detect_go_project(repo_dir: str) -> Optional[ProjectType]:
    """Detect Go project type."""
    has_go_mod = os.path.exists(os.path.join(repo_dir, "go.mod"))
    
    if not has_go_mod:
        return None
    
    setup_commands = ["go mod download"]
    test_commands = ["go test ./..."]
    
    return ProjectType(
        name="go",
        setup_commands=setup_commands,
        test_commands=test_commands,
        language="go"
    )


def get_default_test_command(repo_dir: str) -> Optional[str]:
    """Get a default test command for the repository.

    Args:
        repo_dir: Path to the repository.

    Returns:
        Test command string or None if unable to determine.
    """
    project_type = detect_project_type(repo_dir)
    if project_type and project_type.test_commands:
        return project_type.test_commands[0]
    return None


def get_setup_commands(repo_dir: str) -> List[str]:
    """Get setup commands for the repository.

    Args:
        repo_dir: Path to the repository.

    Returns:
        List of setup command strings.
    """
    project_type = detect_project_type(repo_dir)
    if project_type:
        return project_type.setup_commands
    return []
