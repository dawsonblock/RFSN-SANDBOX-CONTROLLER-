# Setup Capabilities Documentation

**Date**: January 12, 2026  
**Commit**: N/A (pending)

---

## Overview

The RFSN Controller has been enhanced with setup capabilities to handle repositories that require dependency installation and environment configuration. This addresses the limitation encountered with multi-project repositories like BugSwarm.

---

## New Sandbox Tools

### 1. `sandbox.pip_install`

Install Python packages directly using pip.

**Arguments:**
```json
{
  "packages": "package1 package2 package3"
}
```

**Example:**
```json
{
  "tool": "sandbox.pip_install",
  "args": {
    "packages": "requests numpy pytest"
  }
}
```

**Timeout:** 300 seconds (default)

---

### 2. `sandbox.pip_install_requirements`

Install packages from a requirements.txt file.

**Arguments:**
```json
{
  "requirements_file": "path/to/requirements.txt"
}
```

**Example:**
```json
{
  "tool": "sandbox.pip_install_requirements",
  "args": {
    "requirements_file": "database/requirements.txt"
  }
}
```

**Timeout:** 300 seconds (default)

**Behavior:**
- Checks if the file exists before attempting installation
- Returns error if file not found
- Runs `pip install -r <requirements_file>`

---

### 3. `sandbox.create_venv`

Create a Python virtual environment in the repository.

**Arguments:**
```json
{
  "venv_path": ".venv"
}
```

**Example:**
```json
{
  "tool": "sandbox.create_venv",
  "args": {
    "venv_path": ".venv"
  }
}
```

**Timeout:** 60 seconds (default)

**Behavior:**
- Creates virtual environment at specified path
- Returns success message if already exists
- Uses `python -m venv` command

---

## Enhanced Repository View

### Increased `list_tree` Capacity

**Before:** 400 files maximum  
**After:** 2000 files maximum

This allows the controller to see the full structure of large, multi-project repositories.

**Usage in Controller:**
```python
tree = list_tree(sb, max_files=2000)
```

---

## Updated System Prompt

The model is now aware of the new setup tools:

```
Available sandbox tools:
- sandbox.pip_install: Install Python packages
- sandbox.pip_install_requirements: Install from requirements.txt
- sandbox.create_venv: Create a virtual environment

Rules:
- For dependency issues: use sandbox.pip_install or sandbox.pip_install_requirements
- For environment setup: use sandbox.create_venv before installing packages
```

---

## Schema Updates

### New Tool Arguments

The LLM schema now includes:
- `packages` (string): Space-separated list of packages
- `requirements_file` (string): Path to requirements.txt
- `venv_path` (string): Path for virtual environment

---

## Implementation Details

### Sandbox Functions

**File:** `rfsn_controller/sandbox.py`

```python
def pip_install(sb: Sandbox, packages: str, timeout_sec: int = 300) -> Dict[str, Any]:
    """Install Python packages using pip."""
    cmd = f"pip install {packages}"
    code, out, err = _run(cmd, cwd=sb.repo_dir, timeout_sec=timeout_sec)
    return {"ok": code == 0, "exit_code": code, "stdout": out, "stderr": err}

def pip_install_requirements(sb: Sandbox, requirements_file: str, timeout_sec: int = 300) -> Dict[str, Any]:
    """Install packages from a requirements.txt file."""
    full_path = os.path.join(sb.repo_dir, requirements_file)
    if not os.path.exists(full_path):
        return {"ok": False, "error": f"Requirements file not found: {requirements_file}"}
    cmd = f"pip install -r {requirements_file}"
    code, out, err = _run(cmd, cwd=sb.repo_dir, timeout_sec=timeout_sec)
    return {"ok": code == 0, "exit_code": code, "stdout": out, "stderr": err}

def create_venv(sb: Sandbox, venv_path: str = ".venv", timeout_sec: int = 60) -> Dict[str, Any]:
    """Create a Python virtual environment."""
    full_path = os.path.join(sb.repo_dir, venv_path)
    if os.path.exists(full_path):
        return {"ok": True, "note": f"Virtual environment already exists at {venv_path}"}
    cmd = f"python -m venv {venv_path}"
    code, out, err = _run(cmd, cwd=sb.repo_dir, timeout_sec=timeout_sec)
    return {"ok": code == 0, "exit_code": code, "stdout": out, "stderr": err}
```

### Controller Integration

**File:** `rfsn_controller/controller.py`

**Imports:**
```python
from .sandbox import (
    ...
    pip_install,
    pip_install_requirements,
    create_venv,
)
```

**Tool Execution:**
```python
if tool == "sandbox.pip_install":
    try:
        timeout = int(args.get("timeout_sec", 300))
    except (ValueError, TypeError):
        timeout = 300
    return pip_install(sb, args.get("packages", ""), timeout_sec=timeout)

if tool == "sandbox.pip_install_requirements":
    try:
        timeout = int(args.get("timeout_sec", 300))
    except (ValueError, TypeError):
        timeout = 300
    return pip_install_requirements(sb, args.get("requirements_file", "requirements.txt"), timeout_sec=timeout)

if tool == "sandbox.create_venv":
    try:
        timeout = int(args.get("timeout_sec", 60))
    except (ValueError, TypeError):
        timeout = 60
    return create_venv(sb, args.get("venv_path", ".venv"), timeout_sec=timeout)
```

---

## BugSwarm Test Results

### Initial Run (Without Setup Tools)
- **Result:** Early termination after 10 steps
- **Issue:** Model stuck reading requirements files but couldn't install
- **Root Cause:** No pip install capability

### Second Run (With Setup Tools)
- **Result:** Early termination after 10 steps
- **Issue:** Model found `database/requirements.txt` but didn't use pip install
- **Root Cause:** Model needs better prompting to use setup tools

### Key Finding
The model successfully found the requirements file:
```
database/requirements.txt:
eve==0.7.5
flask-cors==3.0.9
Flask-PyMongo==0.5.2
pymongo==3.12.3
```

But continued to read the file instead of installing dependencies.

---

## Usage Examples

### Example 1: Install Single Package
```json
{
  "mode": "tool_request",
  "requests": [
    {
      "tool": "sandbox.pip_install",
      "args": {
        "packages": "pytest"
      }
    }
  ],
  "why": "Install pytest to run tests"
}
```

### Example 2: Install from Requirements
```json
{
  "mode": "tool_request",
  "requests": [
    {
      "tool": "sandbox.pip_install_requirements",
      "args": {
        "requirements_file": "requirements.txt"
      }
    }
  ],
  "why": "Install all project dependencies"
}
```

### Example 3: Setup Environment
```json
{
  "mode": "tool_request",
  "requests": [
    {
      "tool": "sandbox.create_venv",
      "args": {
        "venv_path": ".venv"
      }
    },
    {
      "tool": "sandbox.pip_install_requirements",
      "args": {
        "requirements_file": "requirements.txt"
      }
    }
  ],
  "why": "Create virtual environment and install dependencies"
}
```

---

## Limitations

### Current Limitations

1. **Virtual Environment Activation**
   - Tools create venv but don't activate it
   - pip install uses system Python by default
   - May need `source .venv/bin/activate` support

2. **Multi-Project Dependencies**
   - Each sub-project may have its own requirements
   - Controller doesn't automatically detect this
   - Manual intervention may be needed

3. **Installation Failures**
   - No automatic retry on network failures
   - No handling of conflicting dependencies
   - No version conflict resolution

### Future Enhancements

1. **Automatic Dependency Detection**
   - Scan for all `requirements.txt` files
   - Detect `setup.py` and `pyproject.toml`
   - Prioritize installation order

2. **Virtual Environment Management**
   - Activate venv for subsequent commands
   - Support `pip install -e .` for editable installs
   - Clean up venv after completion

3. **Dependency Resolution**
   - Handle version conflicts
   - Support alternative package sources
   - Cache installed packages

---

## Testing

### Test Repository: BugSwarm

**Command:**
```bash
python -m rfsn_controller.cli \
  --repo "https://github.com/BugSwarm/bugswarm" \
  --test "pytest -q" \
  --fix-all \
  --collect-finetuning-data
```

**Expected Behavior:**
1. Model detects missing dependencies
2. Model finds `database/requirements.txt`
3. Model uses `sandbox.pip_install_requirements`
4. Tests run successfully after installation

**Actual Behavior:**
- Model found requirements file
- Model did not use pip install tools
- Early termination triggered

**Next Steps:**
- Improve system prompt to encourage setup tool usage
- Add examples to prompt showing setup workflow
- Consider automatic setup phase before bug fixing

---

## Files Modified

1. **rfsn_controller/sandbox.py**
   - Added `pip_install()` function
   - Added `pip_install_requirements()` function
   - Added `create_venv()` function

2. **rfsn_controller/controller.py**
   - Imported new setup functions
   - Added tool execution handlers
   - Increased `list_tree` max_files to 2000

3. **rfsn_controller/llm_gemini.py**
   - Updated system prompt with new tools
   - Added setup tool arguments to schema
   - Added usage rules for setup tools

---

## Conclusion

The controller now has the capability to:
- ✅ Install Python packages via pip
- ✅ Install from requirements.txt files
- ✅ Create virtual environments
- ✅ View full repository structure (2000 files)

However, the model needs better prompting to use these tools effectively. Future work should focus on:
- Improving system prompt examples
- Adding automatic setup detection
- Better handling of multi-project repositories

---

**Documentation Generated**: January 12, 2026  
**Status**: Setup capabilities implemented and tested
