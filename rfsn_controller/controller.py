"""The RFSN controller core loop.

This module implements the controller loop for the RFSN coding agent.
It manages a disposable sandbox, clones a public GitHub repository,
runs test commands to measure progress, consults the Gemini model for
tool requests or candidate patches, executes requested tools, validates
candidate patches in isolated worktrees, and applies winners to the
main repository only if they pass focused and full verification.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .sandbox import (
    Sandbox,
    create_sandbox,
    clone_public_github,
    checkout,
    list_tree,
    read_file,
    grep,
    run_cmd,
    apply_patch,
    reset_hard,
    git_status,
    make_worktree,
    drop_worktree,
    apply_patch_in_dir,
    pip_install,
    pip_install_requirements,
    pip_install_progressive,
    create_venv,
    find_local_module,
    set_pythonpath,
    docker_install,
    docker_test,
)
from .url_validation import validate_github_url
from .patch_hygiene import validate_patch_hygiene, PatchHygieneConfig
from .tool_manager import ToolRequestManager, ToolRequestConfig
from .verifier import run_tests, VerifyResult
from .policy import choose_policy
from .prompt import build_model_input
from .llm_gemini import call_model as call_gemini
from .llm_deepseek import call_model as call_deepseek
from .parsers import normalize_test_path, parse_trace_files
from .log import write_jsonl
from .parallel import evaluate_patches_parallel, find_first_successful_patch
from .phases import Phase, PhaseTransition
from .project_detection import detect_project_type, get_setup_commands, get_default_test_command
from .stall_detector import StallState
from .evidence_pack import EvidencePackExporter, EvidencePackConfig
from .model_validator import ModelOutputValidator
from .winner_selection import score_patch
from .project_detector import ProjectDetector, ProjectType
from .language_templates import Language, get_buildpack_image
from .apt_whitelist import AptWhitelist, AptTier
from .sysdeps_installer import SysdepsInstaller
from .setup_report import SetupReport, create_setup_report
from .test_detector import TestDetector


def get_model_client(model_name: str):
    """Get the appropriate model client based on model name."""
    if model_name.startswith("deepseek"):
        return call_deepseek
    else:
        return call_gemini
from .buildpacks import (
    get_all_buildpacks,
    BuildpackContext,
)


FORBIDDEN_PREFIXES = [".git/", "node_modules/", ".venv/", "venv/", "__pycache__/"]


def _diff_hash(d: str) -> str:
    """Compute a hash of a diff string for deduplication."""
    return hashlib.sha256((d or "").encode("utf-8", errors="ignore")).hexdigest()


def _safe_path(p: str) -> bool:
    """Return True if the relative path is outside forbidden prefixes."""
    p = p.replace("\\", "/").lstrip("./")
    return not any(p.startswith(pref) for pref in FORBIDDEN_PREFIXES)


def _files_block(files: List[Dict[str, Any]]) -> str:
    """Create a files block for the model input from a list of read_file results."""
    blocks = []
    for f in files:
        if f.get("ok") and f.get("path") and isinstance(f.get("text"), str):
            blocks.append(f"[path: {f['path']}]\n{f['text']}\n")
    return "\n".join(blocks)


def _constraints_text() -> str:
    """Return a static constraints description for the model."""
    return "\n".join([
        "- Return either tool_request or patch JSON only.",
        "- Patch diff must apply with git apply from repo root.",
        "- Minimal edits. No refactors. No reformatting.",
        "- Public GitHub only. No tokens.",
        "- Do not touch forbidden paths: " + ", ".join(FORBIDDEN_PREFIXES),
    ])


def _execute_tool(sb: Sandbox, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a sandbox tool by name with the provided arguments.

    Note: sandbox.run is intentionally NOT exposed to the model.
    The controller handles test execution directly for security.
    """
    if not isinstance(args, dict):
        args = {}
    if tool == "sandbox.clone_repo":
        return clone_public_github(sb, args.get("github_url", ""))
    if tool == "sandbox.checkout":
        return checkout(sb, args.get("ref", ""))
    # sandbox.run intentionally removed - controller-only for security
    if tool == "sandbox.read_file":
        try:
            max_bytes = int(args.get("max_bytes", 120000))
        except (ValueError, TypeError):
            max_bytes = 120000
        return read_file(sb, args.get("path", ""), max_bytes=max_bytes)
    if tool == "sandbox.grep":
        try:
            max_matches = int(args.get("max_matches", 200))
        except (ValueError, TypeError):
            max_matches = 200
        return grep(sb, args.get("query", ""), max_matches=max_matches)
    if tool == "sandbox.list_tree":
        try:
            max_files = int(args.get("max_files", 400))
        except (ValueError, TypeError):
            max_files = 400
        return list_tree(sb, max_files=max_files)
    if tool == "sandbox.apply_patch":
        return apply_patch(sb, args.get("diff", ""))
    if tool == "sandbox.git_status":
        return git_status(sb)
    if tool == "sandbox.reset_hard":
        return reset_hard(sb)
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
    if tool == "sandbox.pip_install_progressive":
        try:
            timeout = int(args.get("timeout_sec", 300))
        except (ValueError, TypeError):
            timeout = 300
        return pip_install_progressive(sb, args.get("packages", ""), timeout_sec=timeout)
    if tool == "sandbox.find_local_module":
        return find_local_module(sb, args.get("module_name", ""))
    if tool == "sandbox.set_pythonpath":
        return set_pythonpath(sb, args.get("path", ""))
    return {"ok": False, "error": f"Unknown tool: {tool}"}


def _collect_relevant_files(sb: Sandbox, v: VerifyResult, repo_tree: str) -> List[Dict[str, Any]]:
    """Collect a small set of files likely related to the failure.

    The selection includes the first failing test file and any Python files
    mentioned in tracebacks. File paths are normalized and filtered via
    _safe_path to avoid sending forbidden files to the model.
    """
    out: List[Dict[str, Any]] = []
    # failing test file
    if v.failing_tests:
        tp = normalize_test_path(v.failing_tests[0])
        if _safe_path(tp):
            out.append(read_file(sb, tp, max_bytes=120000))
    # traceback referenced files
    combined = (v.stdout or "") + "\n" + (v.stderr or "")
    for p in parse_trace_files(combined, limit=6):
        # trace files may be absolute; ignore abs outside
        p2 = p.replace("\\", "/")
        if p2.startswith(sb.repo_dir.replace("\\", "/")):
            p2 = p2[len(sb.repo_dir):].lstrip("/")
        if p2.endswith(".py") and _safe_path(p2):
            out.append(read_file(sb, p2, max_bytes=120000))
    return out


def _collect_relevant_files_quixbugs(sb: Sandbox, v: VerifyResult, repo_tree: str) -> List[Dict[str, Any]]:
    """Collect files for QuixBugs repositories with specific heuristics.

    QuixBugs structure:
    - python_testcases/test_<program>.py (test files)
    - python_programs/<program>.py (implementation files)

    Strategy:
    1. Always include the first failing test file (highest priority)
    2. Map test file to corresponding program file
    3. Include any traceback-referenced files
    4. Add common helper files if referenced
    """
    out: List[Dict[str, Any]] = []

    if not v.failing_tests:
        return out

    # Get the first failing test file (highest priority)
    test_path = normalize_test_path(v.failing_tests[0])
    if not _safe_path(test_path):
        return out

    # 1. Include the failing test file (highest priority)
    test_content = read_file(sb, test_path, max_bytes=120000)
    if test_content.get("ok"):
        out.append(test_content)

    # 2. Map test file to program file
    # python_testcases/test_quicksort.py -> python_programs/quicksort.py
    if "python_testcases/" in test_path:
        test_filename = test_path.split("/")[-1]  # test_quicksort.py
        if test_filename.startswith("test_") and test_filename.endswith(".py"):
            program_name = test_filename[5:-3]  # quicksort
            program_path = f"python_programs/{program_name}.py"
            if _safe_path(program_path):
                program_content = read_file(sb, program_path, max_bytes=120000)
                if program_content.get("ok"):
                    out.append(program_content)

    # 3. Include traceback-referenced files
    combined = (v.stdout or "") + "\n" + (v.stderr or "")
    for p in parse_trace_files(combined, limit=6):
        p2 = p.replace("\\", "/")
        if p2.startswith(sb.repo_dir.replace("\\", "/")):
            p2 = p2[len(sb.repo_dir):].lstrip("/")
        if p2.endswith(".py") and _safe_path(p2):
            # Avoid duplicates
            if not any(f.get("path") == p2 for f in out):
                file_content = read_file(sb, p2, max_bytes=120000)
                if file_content.get("ok"):
                    out.append(file_content)

    return out


def _evaluate_patch_in_worktree(sb: Sandbox, diff: str, focus_cmd: str, full_cmd: str) -> Tuple[bool, str]:
    """Test a candidate patch in a detached worktree before applying to main repo."""
    wt = make_worktree(sb)
    try:
        ap = apply_patch_in_dir(wt, diff)
        if not ap.get("ok"):
            return False, f"apply_failed: {ap.get('stderr','')}{ap.get('stdout','')}"
        r1 = run_cmd(Sandbox(sb.root, wt), focus_cmd, timeout_sec=90)
        if not r1.get("ok"):
            return False, "focus_failed:\n" + (r1.get("stdout", "") + r1.get("stderr", ""))
        r2 = run_cmd(Sandbox(sb.root, wt), full_cmd, timeout_sec=180)
        if r2.get("ok"):
            return True, "PASS"
        return False, "full_failed:\n" + (r2.get("stdout", "") + r2.get("stderr", ""))
    except Exception as e:
        return False, f"exception: {type(e).__name__}: {str(e)}"
    finally:
        try:
            drop_worktree(sb, wt)
        except Exception:
            pass


@dataclass
class ControllerConfig:
    """Configuration for a controller run."""

    github_url: str
    test_cmd: str = "pytest -q"
    ref: Optional[str] = None
    max_steps: int = 12
    temps: List[float] = field(default_factory=lambda: [0.0, 0.2, 0.4])
    fix_all: bool = False
    max_steps_without_progress: int = 10
    collect_finetuning_data: bool = False
    model: str = "deepseek-r1"
    max_minutes: int = 30
    install_timeout: int = 300
    focus_timeout: int = 120
    full_timeout: int = 300
    max_tool_calls: int = 40
    docker_image: str = "python:3.11-slim"
    unsafe_host_exec: bool = False
    cpu: float = 2.0
    mem_mb: int = 4096
    pids: int = 256
    docker_readonly: bool = False
    lint_cmd: Optional[str] = None
    typecheck_cmd: Optional[str] = None
    repro_cmd: Optional[str] = None
    dry_run: bool = False
    project_type: str = "auto"
    buildpack: str = "auto"
    enable_sysdeps: bool = False
    sysdeps_tier: int = 4
    sysdeps_max_packages: int = 10
    build_cmd: Optional[str] = None


def run_controller(cfg: ControllerConfig) -> Dict[str, Any]:
    """Run the controller loop until the goal is reached or max_steps exhausted.

    Args:
        cfg: The controller configuration.

    Returns:
        A dictionary indicating success, or error details, and where the
        sandbox directory can be inspected.
    """
    sb = create_sandbox()
    log_dir = sb.root  # write logs next to sandbox for inspection
    bad_hashes: set[str] = set()
    observations: str = ""  # buffer for tool results to feed back to model
    sig_history: list[str] = []  # track error signatures for stall detection
    patch_attempts: int = 0  # count patch attempts to detect lack of progress
    steps_without_progress: int = 0  # track steps without reducing failing tests
    min_failing_tests: int = 999999  # track minimum failing tests seen
    distinct_sigs: set[str] = set()  # track distinct error signatures for multi-bug detection

    # Initialize vNext components
    current_phase = Phase.INGEST
    tool_manager = ToolRequestManager(ToolRequestConfig(max_total_requests_per_run=cfg.max_tool_calls))
    stall_state = StallState()
    evidence_exporter = EvidencePackExporter(EvidencePackConfig())
    command_log: List[Dict[str, Any]] = []

    # Track baseline for evidence pack
    baseline_output = ""
    final_output = ""
    winner_diff = None

    try:
        write_jsonl(log_dir, {"phase": "init", "cfg": cfg.__dict__})

        # === PHASE: INGEST ===
        write_jsonl(log_dir, PhaseTransition(None, Phase.INGEST).to_dict())

        # Validate GitHub URL
        is_valid, normalized_url, url_error = validate_github_url(cfg.github_url)
        if not is_valid:
            return {"ok": False, "error": f"Invalid GitHub URL: {url_error}"}

        github_url = normalized_url
        write_jsonl(log_dir, {"phase": "url_validation", "normalized_url": github_url})

        # Clone repository
        r = clone_public_github(sb, github_url)
        write_jsonl(log_dir, {"phase": "clone", "result": r})
        if not r.get("ok"):
            return {"ok": False, "error": r.get("error") or r.get("stderr")}

        # Checkout ref if specified
        if cfg.ref:
            co = checkout(sb, cfg.ref)
            write_jsonl(log_dir, {"phase": "checkout", "result": co})
            if not co.get("ok"):
                return {"ok": False, "error": co.get("stderr")}

        reset_hard(sb)
        tree = list_tree(sb, max_files=2000)
        repo_tree = tree.get("files", []) if tree.get("ok") else []
        repo_tree_text = "\n".join(repo_tree)

        # === PHASE: DETECT ===
        current_phase = Phase.DETECT
        write_jsonl(log_dir, PhaseTransition(Phase.INGEST, Phase.DETECT).to_dict())

        # === PHASE: V3 BUILDPACK DETECTION ===
        selected_buildpack = None
        selected_buildpack_instance = None

        try:
            # Create buildpack context
            buildpack_ctx = BuildpackContext(
                repo_dir=sb.repo_dir,
                repo_tree=repo_tree,
                files={},
            )

            # Read relevant files for buildpack detection
            buildpack_files = [
                "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg",
                "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                "go.mod", "go.sum",
                "Cargo.toml", "Cargo.lock",
                "pom.xml", "build.gradle", "build.gradle.kts", "gradlew",
                "*.sln", "*.csproj", "global.json",
            ]

            for filename in buildpack_files:
                if "*" in filename:
                    # Handle wildcards
                    try:
                        result = grep(sb, filename)
                        if result and result.stdout:
                            files = result.stdout.strip().split("\n")
                            for f in files:
                                try:
                                    content = read_file(sb, f)
                                    if content:
                                        buildpack_ctx.files[f] = content
                                except Exception:
                                    pass
                    except Exception:
                        pass
                else:
                    try:
                        content = read_file(sb, filename)
                        if content:
                            buildpack_ctx.files[filename] = content
                    except Exception:
                        pass

            # Detect buildpack
            all_buildpacks = get_all_buildpacks()
            best_result = None
            best_buildpack = None

            for buildpack in all_buildpacks:
                result = buildpack.detect(buildpack_ctx)
                if result and result.confidence > 0.5:
                    if best_result is None or result.confidence > best_result.confidence:
                        best_result = result
                        best_buildpack = buildpack

            if best_buildpack and best_result:
                selected_buildpack_instance = best_buildpack
                selected_buildpack = best_buildpack.image()

                write_jsonl(log_dir, {
                    "phase": "buildpack_detect",
                    "buildpack_type": best_result.buildpack_type.value,
                    "confidence": best_result.confidence,
                    "workspace": best_result.workspace,
                    "image": selected_buildpack,
                    "metadata": best_result.metadata,
                })
            else:
                # Fallback to docker_image
                selected_buildpack = cfg.docker_image
                write_jsonl(log_dir, {
                    "phase": "buildpack_detect",
                    "error": "No buildpack detected",
                    "fallback_image": selected_buildpack,
                })
        except Exception as e:
            # Fallback to docker_image if buildpack detection fails
            selected_buildpack = cfg.docker_image
            write_jsonl(log_dir, {"phase": "buildpack_detect", "error": str(e)})

        # Legacy detection for backward compatibility
        project_type = detect_project_type(sb.repo_dir)
        setup_commands = get_setup_commands(sb.repo_dir)
        detected_test_cmd = get_default_test_command(sb.repo_dir)

        # Use detected test command if not overridden
        effective_test_cmd = cfg.test_cmd if cfg.test_cmd != "pytest -q" else (detected_test_cmd or "pytest -q")

        write_jsonl(log_dir, {
            "phase": "detect",
            "project_type": project_type.name if project_type else None,
            "setup_commands": setup_commands,
            "detected_test_cmd": detected_test_cmd,
            "effective_test_cmd": effective_test_cmd,
        })

        # Detect QuixBugs repository structure
        is_quixbugs = "python_testcases/" in repo_tree_text and "python_programs/" in repo_tree_text

        # === PHASE: SETUP ===
        current_phase = Phase.SETUP
        write_jsonl(log_dir, PhaseTransition(Phase.DETECT, Phase.SETUP).to_dict())

        # Track setup results for validation
        setup_results = {}
        lockfile_path = None

        # Use buildpack install plan if available
        if selected_buildpack_instance:
            print(f"[SETUP] Using buildpack: {selected_buildpack_instance.buildpack_type.value}")
            install_steps = selected_buildpack_instance.install_plan(buildpack_ctx)

            for step in install_steps:
                print(f"[SETUP] Running: {step.description}")
                cmd_str = " ".join(step.argv)
                result = docker_install(sb, cmd_str, timeout_sec=step.timeout_sec, docker_image=selected_buildpack)

                # Store result by step description
                setup_results[step.description] = result

                command_log.append({
                    "phase": "setup",
                    "command": cmd_str,
                    "exit_code": result.exit_code,
                    "ok": result.ok,
                    "stdout": result.stdout[:1000],
                    "stderr": result.stderr[:1000],
                })
                write_jsonl(log_dir, {
                    "phase": "setup",
                    "command": cmd_str,
                    "result": {"ok": result.ok, "exit_code": result.exit_code},
                })
                if not result.ok:
                    print(f"[SETUP] Failed: {result.stderr[:200]}")
        else:
            # Legacy setup
            if setup_commands and not cfg.unsafe_host_exec:
                for setup_cmd in setup_commands:
                    print(f"[SETUP] Running: {setup_cmd}")
                    result = docker_install(sb, setup_cmd, timeout_sec=cfg.install_timeout, docker_image=selected_buildpack)

                    # Store result by command type
                    cmd_lower = setup_cmd.lower()
                    if "pip install" in cmd_lower or "python -m pip" in cmd_lower:
                        setup_results["pip"] = result
                    elif "npm install" in cmd_lower or "npm ci" in cmd_lower:
                        setup_results["node"] = result
                    elif "go mod" in cmd_lower:
                        setup_results["go"] = result
                    elif "cargo" in cmd_lower:
                        setup_results["rust"] = result
                    elif "mvn" in cmd_lower or "gradle" in cmd_lower:
                        setup_results["java"] = result
                    elif "dotnet restore" in cmd_lower:
                        setup_results["dotnet"] = result

                    command_log.append({
                        "phase": "setup",
                        "command": setup_cmd,
                        "exit_code": result.exit_code,
                        "ok": result.ok,
                        "stdout": result.stdout[:1000],
                        "stderr": result.stderr[:1000],
                    })
                    write_jsonl(log_dir, {
                        "phase": "setup",
                        "command": setup_cmd,
                        "result": {"ok": result.ok, "exit_code": result.exit_code},
                    })
                    if not result.ok:
                        print(f"[SETUP] Failed: {result.stderr[:200]}")

        # Detect lockfile
        if selected_buildpack_instance:
            # Lockfile detection is handled by buildpack metadata
            if best_result and best_result.metadata:
                lockfile_path = best_result.metadata.get("lockfile")

        # === PHASE: SYSDEPS (V3) ===
        sysdeps_installed = []
        sysdeps_blocked = []

        if cfg.enable_sysdeps and selected_buildpack_instance:
            current_phase = Phase.SETUP
            write_jsonl(log_dir, {"phase": "sysdeps", "enabled": True})

            # Use buildpack's sysdeps whitelist
            sysdeps_whitelist = selected_buildpack_instance.sysdeps_whitelist()

            tier_map = {
                0: AptTier.TIER_0,
                1: AptTier.TIER_1,
                2: AptTier.TIER_2,
                3: AptTier.TIER_3,
                4: AptTier.TIER_4,
                5: AptTier.TIER_5,
                6: AptTier.TIER_6,
                7: AptTier.TIER_7,
            }

            whitelist = AptWhitelist(
                max_packages=cfg.sysdeps_max_packages,
                max_tier=tier_map.get(cfg.sysdeps_tier, AptTier.TIER_4),
                allow_wildcards=False,
                custom_packages=sysdeps_whitelist,
            )

            installer = SysdepsInstaller(
                whitelist=whitelist,
                dry_run=False,
            )

            print("[SYSDEPS] Installing system dependencies...")
            sysdeps_result = installer.install(
                packages=[],
                hints=[],
            )

            sysdeps_installed = sysdeps_result.installed_packages
            sysdeps_blocked = sysdeps_result.blocked_packages

            write_jsonl(log_dir, {
                "phase": "sysdeps",
                "result": {
                    "success": sysdeps_result.success,
                    "installed": sysdeps_installed,
                    "blocked": sysdeps_blocked,
                    "error": sysdeps_result.error_message,
                },
            })

            if sysdeps_result.success:
                print(f"[SYSDEPS] Installed: {sysdeps_installed}")
            else:
                print(f"[SYSDEPS] Failed: {sysdeps_result.error_message}")
                if sysdeps_blocked:
                    print(f"[SYSDEPS] Blocked packages: {sysdeps_blocked}")

        # === PHASE: SETUP VALIDATION ===
        # Create setup report and check if we should bail out
        setup_report = create_setup_report(
            pip_result=setup_results.get("pip"),
            node_result=setup_results.get("node"),
            go_result=setup_results.get("go"),
            rust_result=setup_results.get("rust"),
            java_result=setup_results.get("java"),
            dotnet_result=setup_results.get("dotnet"),
            lockfile_path=lockfile_path,
            sysdeps_installed=sysdeps_installed,
            sysdeps_failed=[],
            sysdeps_blocked=sysdeps_blocked,
        )

        write_jsonl(log_dir, {
            "phase": "setup_validation",
            "report": setup_report.to_dict(),
        })

        # Hard bailout if setup failed
        if setup_report.should_bailout():
            bailout_reason = setup_report.get_bailout_message()
            print(f"\n[BAILOUT] {bailout_reason}")
            write_jsonl(log_dir, {
                "phase": "bailout",
                "reason": bailout_reason,
                "setup_report": setup_report.to_dict(),
            })

            return {
                "ok": False,
                "error": bailout_reason,
                "sandbox": sb.root,
                "repo_dir": sb.repo_dir,
                "phase": "setup_failed",
            }

        print("\n[SETUP_VALIDATION] Setup passed")
        if setup_report.has_lockfile:
            print(f"  Lockfile found: {setup_report.lockfile_path}")
        if setup_report.sysdeps_installed:
            print(f"  System deps installed: {setup_report.sysdeps_installed}")

        # === PHASE: BASELINE ===
        current_phase = Phase.BASELINE
        write_jsonl(log_dir, PhaseTransition(Phase.SETUP, Phase.BASELINE).to_dict())

        # Use buildpack test plan if available
        if selected_buildpack_instance:
            test_plan = selected_buildpack_instance.test_plan(buildpack_ctx)
            effective_test_cmd = " ".join(test_plan.argv)
        else:
            # Use detected test command
            effective_test_cmd = cfg.test_cmd if cfg.test_cmd != "pytest -q" else (detected_test_cmd or "pytest -q")

        # Run baseline tests
        print(f"\n[BASELINE] Running: {effective_test_cmd}")
        v = _run_tests_in_sandbox(sb, effective_test_cmd, cfg, command_log, selected_buildpack)
        baseline_output = (v.stdout or "") + "\n" + (v.stderr or "")

        write_jsonl(log_dir, {
            "phase": "baseline",
            "tests_ok": v.ok,
            "exit_code": v.exit_code,
            "failing_tests": v.failing_tests,
            "sig": v.sig,
        })

        # Handle pytest exit code 2 (no tests found)
        if v.exit_code == 2 and not v.ok:
            print(f"\n[BASELINE] Exit code 2 detected - no tests found")
            # Try alternative test commands based on buildpack
            if selected_buildpack_instance:
                # Buildpack-specific fallbacks
                if selected_buildpack_instance.buildpack_type.value == "python":
                    suggestions = [
                        "python -m pytest -q --collect-only",
                        "python -m pytest -q tests/",
                        "python -m unittest discover -q",
                    ]
                elif selected_buildpack_instance.buildpack_type.value == "node":
                    suggestions = [
                        "npm test -- --listTests",
                        "npm test -- tests/",
                    ]
                else:
                    suggestions = []

                if suggestions:
                    suggested_cmd = suggestions[0]
                    print(f"\n[BASELINE] Retrying with: {suggested_cmd}")
                    v = _run_tests_in_sandbox(sb, suggested_cmd, cfg, command_log, selected_buildpack)
                    baseline_output = (v.stdout or "") + "\n" + (v.stderr or "")

                    write_jsonl(log_dir, {
                        "phase": "baseline_retry",
                        "tests_ok": v.ok,
                        "exit_code": v.exit_code,
                        "failing_tests": v.failing_tests,
                        "sig": v.sig,
                    })

                    if v.ok or v.exit_code != 2:
                        effective_test_cmd = suggested_cmd
                        print(f"  Using new test command: {effective_test_cmd}")

        if v.ok:
            print(f"\n[BASELINE] SUCCESS! All tests passing at baseline.")
            return {
                "ok": True,
                "sandbox": sb.root,
                "repo_dir": sb.repo_dir,
                "steps_taken": 0,
                "phase": "baseline_pass",
            }

        # === PHASE: REPAIR_LOOP ===
        current_phase = Phase.REPAIR_LOOP
        write_jsonl(log_dir, PhaseTransition(Phase.BASELINE, Phase.REPAIR_LOOP).to_dict())

        # If fix_all mode, use unlimited steps
        max_iterations = float('inf') if cfg.fix_all else cfg.max_steps
        step = 0

        while step < max_iterations:
            # Progress reporting
            print(f"\n[Step {step}] Running tests...")
            v = _run_tests_in_sandbox(sb, effective_test_cmd, cfg, command_log, selected_buildpack)
            final_output = (v.stdout or "") + "\n" + (v.stderr or "")

            print(f"[Step {step}] Tests: {'PASS' if v.ok else 'FAIL'} | Failing: {len(v.failing_tests)} tests")
            write_jsonl(log_dir, {
                "phase": "measure",
                "step": step,
                "tests_ok": v.ok,
                "exit_code": v.exit_code,
                "failing_tests": v.failing_tests,
                "sig": v.sig,
            })

            # Update stall detector
            top_test_id = v.failing_tests[0] if v.failing_tests else None
            is_stalled = stall_state.update(len(v.failing_tests), top_test_id, v.sig)

            if v.ok:
                print(f"\n✅ SUCCESS! All tests passing after {step} steps.")
                current_phase = Phase.FINAL_VERIFY
                break

            # Track progress for early termination
            current_failing = len(v.failing_tests)
            if current_failing < min_failing_tests:
                min_failing_tests = current_failing
                steps_without_progress = 0
            else:
                steps_without_progress += 1

            # Early termination: no progress after N steps
            if steps_without_progress >= cfg.max_steps_without_progress:
                print(f"\n❌ Early termination: No progress for {steps_without_progress} steps")
                current_phase = Phase.BAILOUT
                break

            # Track distinct signatures for multi-bug detection
            distinct_sigs.add(v.sig)
            if len(distinct_sigs) > 1:
                print(f"[Step {step}] 🐛 Multi-bug detected: {len(distinct_sigs)} distinct error signatures")

            # If stalled, force evidence gathering
            if is_stalled:
                write_jsonl(log_dir, {"phase": "stall_detected", "step": step, "sig": v.sig, "iterations_without_improvement": stall_state.iterations_without_improvement})
                print(f"[Step {step}] ⚠️  Stall detected - switching to evidence gathering")

            # controller policy
            pd = choose_policy(effective_test_cmd, v)
            if is_stalled:
                pd.intent = "gather_evidence"
                pd.subgoal = "Collect more context: list_tree, grep for error symbols, read new files"

            print(f"[Step {step}] Intent: {pd.intent} | Subgoal: {pd.subgoal[:60]}...")

            # gather high-signal files
            if is_quixbugs:
                files = _collect_relevant_files_quixbugs(sb, v, repo_tree_text)
            else:
                files = _collect_relevant_files(sb, v, repo_tree_text)
            files_block = _files_block(files)

            # model state = facts
            state = {
                "goal": "Make test command succeed (exit code 0).",
                "intent": pd.intent,
                "subgoal": pd.subgoal,
                "test_cmd": effective_test_cmd,
                "focus_test_cmd": pd.focus_test_cmd,
                "failure_output": (v.stdout or "") + "\n" + (v.stderr or ""),
                "repo_tree": repo_tree_text,
                "constraints": _constraints_text(),
                "files_block": files_block,
                "observations": observations,
            }
            model_input = build_model_input(state)

            # ask model (try multiple temps for diversity)
            winner: Optional[str] = None
            patches_to_evaluate = []
            call_model = get_model_client(cfg.model)
            for t in cfg.temps:
                resp = call_model(model_input, temperature=t)
                write_jsonl(log_dir, {"phase": "model", "step": step, "temp": t, "resp": resp})

                mode = resp.get("mode")
                if mode == "tool_request":
                    # execute requested tools; then continue to next iteration
                    tool_results = []
                    obs_additions = []
                    requests = resp.get("requests", [])[:6]

                    # Filter requests through tool manager
                    allowed_requests, blocked_reasons = tool_manager.filter_requests(requests)

                    for req in allowed_requests:
                        tool = req.get("tool", "")
                        args = req.get("args", {}) if isinstance(req.get("args"), dict) else {}
                        tr = _execute_tool(sb, tool, args)
                        tool_results.append({"tool": tool, "args": args, "result": tr})

                        # Summarize for observations
                        summary = f"Tool: {tool}\n"
                        summary += f"Args: {args}\n"
                        summary += f"Exit: {tr.get('exit_code', 'N/A')}\n"
                        stdout = tr.get("stdout", "")[:500]
                        stderr = tr.get("stderr", "")[:500]
                        if stdout:
                            summary += f"Stdout: {stdout}\n"
                        if stderr:
                            summary += f"Stderr: {stderr}\n"
                        if tool == "sandbox.read_file" and tr.get("ok"):
                            summary += "[File content read successfully]\n"
                        if tool == "sandbox.grep" and tr.get("ok"):
                            matches = tr.get("matches", [])
                            if matches:
                                summary += f"Found {len(matches)} matches\n"
                        if tool == "sandbox.list_tree" and tr.get("ok"):
                            files = tr.get("files", [])
                            summary += f"Listed {len(files)} files\n"
                        obs_additions.append(summary)

                    write_jsonl(log_dir, {
                        "phase": "tool_execution",
                        "step": step,
                        "temp": t,
                        "results": tool_results,
                        "blocked": blocked_reasons,
                    })

                    # Append to observations buffer
                    if obs_additions:
                        observations += "\n" + "\n".join(obs_additions)

                    # If we got tool requests, continue to next iteration
                    if allowed_requests:
                        break

                elif mode == "patch":
                    diff = resp.get("diff", "")
                    if diff:
                        dh = _diff_hash(diff)
                        if dh in bad_hashes:
                            print(f"[Step {step}] Skipping duplicate patch hash")
                            continue
                        bad_hashes.add(dh)
                        patches_to_evaluate.append(diff)

            # Evaluate patches
            if patches_to_evaluate:
                patch_attempts += 1
                print(f"[Step {step}] Evaluating {len(patches_to_evaluate)} patch(es)...")

                # Validate patch hygiene
                valid_patches = []
                for diff in patches_to_evaluate:
                    hygiene_result = validate_patch_hygiene(diff, PatchHygieneConfig())
                    if hygiene_result.is_valid:
                        valid_patches.append(diff)
                    else:
                        print(f"[Step {step}] Patch rejected by hygiene gates: {hygiene_result.violations}")
                        write_jsonl(log_dir, {
                            "phase": "patch_rejected",
                            "step": step,
                            "reasons": hygiene_result.violations,
                        })

                if valid_patches:
                    # Evaluate in parallel worktrees
                    results = evaluate_patches_parallel(
                        sb, valid_patches, effective_test_cmd,
                        temps=cfg.temps, timeout_sec=cfg.focus_timeout,
                        use_docker=not cfg.unsafe_host_exec,
                        docker_image=selected_buildpack,
                    )

                    winner = find_first_successful_patch(results)
                    if winner:
                        print(f"[Step {step}] ✅ Found winning patch!")
                        write_jsonl(log_dir, {"phase": "winner_found", "step": step, "winner_hash": _diff_hash(winner)})
                        # Apply winner to main repo
                        apply_patch(sb, winner)
                        winner_diff = winner
                        break
                    else:
                        print(f"[Step {step}] No patch passed verification")
                        write_jsonl(log_dir, {"phase": "no_winner", "step": step, "attempted": len(valid_patches)})

            step += 1

        # === PHASE: FINAL_VERIFY ===
        if current_phase == Phase.FINAL_VERIFY:
            write_jsonl(log_dir, PhaseTransition(Phase.REPAIR_LOOP, Phase.FINAL_VERIFY).to_dict())

            print(f"\n[FINAL_VERIFY] Running full test suite...")
            v = _run_tests_in_sandbox(sb, effective_test_cmd, cfg, command_log, selected_buildpack)
            final_output = (v.stdout or "") + "\n" + (v.stderr or "")

            if v.ok:
                print(f"\n✅ FINAL SUCCESS! All tests passing.")
            else:
                print(f"\n⚠️  Final verify failed: {len(v.failing_tests)} failing tests")
                current_phase = Phase.BAILOUT

        # === PHASE: EVIDENCE_PACK ===
        current_phase = Phase.EVIDENCE_PACK
        write_jsonl(log_dir, PhaseTransition(Phase.FINAL_VERIFY, Phase.EVIDENCE_PACK).to_dict())

        # Export evidence pack
        state_dict = {
            "config": cfg.__dict__,
            "project_type": project_type.name if project_type else None,
            "setup_commands": setup_commands,
            "effective_test_cmd": effective_test_cmd,
            "steps_taken": step,
            "patch_attempts": patch_attempts,
            "min_failing_tests": min_failing_tests,
            "final_failing_tests": len(v.failing_tests) if not v.ok else 0,
            "final_ok": v.ok,
        }

        pack_dir = evidence_exporter.export(
            sandbox_root=sb.root,
            log_dir=log_dir,
            baseline_output=baseline_output,
            final_output=final_output,
            winner_diff=winner_diff,
            state=state_dict,
            command_log=command_log,
        )

        print(f"\n[EVIDENCE_PACK] Exported to: {pack_dir}")

        return {
            "ok": v.ok,
            "sandbox": sb.root,
            "repo_dir": sb.repo_dir,
            "steps_taken": step,
            "evidence_pack": pack_dir,
            "winner_diff": winner_diff,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Exception: {e}",
            "sandbox": sb.root,
            "repo_dir": sb.repo_dir,
        }


def _run_tests_in_sandbox(
    sb: Sandbox,
    test_cmd: str,
    cfg: ControllerConfig,
    command_log: List[Dict[str, Any]],
    docker_image: str,
) -> VerifyResult:
    """Run tests in Docker or on host based on configuration.

    Args:
        sb: The sandbox.
        test_cmd: Test command to run.
        cfg: Controller configuration.
        command_log: Command execution log.
        docker_image: Docker image to use for execution.

    Returns:
        VerifyResult with test results.
    """
    if cfg.unsafe_host_exec:
        # Run on host (unsafe)
        return run_tests(sb, test_cmd, timeout_sec=cfg.focus_timeout)
    else:
        # Run in Docker with network OFF
        result = docker_test(sb, test_cmd, timeout_sec=cfg.focus_timeout, docker_image=docker_image)

        command_log.append({
            "phase": "test",
            "command": test_cmd,
            "exit_code": result.exit_code,
            "ok": result.ok,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "timed_out": result.timed_out,
        })

        # Convert DockerResult to VerifyResult
        from .parsers import parse_pytest_failures, error_signature
        failing_tests = parse_pytest_failures(result.stdout + result.stderr)
        sig = error_signature(result.stdout, result.stderr)
        return VerifyResult(
            ok=result.ok,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            failing_tests=failing_tests,
            sig=sig,
        )