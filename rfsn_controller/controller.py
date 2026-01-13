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
)
from .verifier import run_tests, VerifyResult
from .policy import choose_policy
from .prompt import build_model_input
from .llm_gemini import call_model
from .parsers import normalize_test_path, parse_trace_files
from .log import write_jsonl
from .parallel import evaluate_patches_parallel, find_first_successful_patch


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
    """Execute a sandbox tool by name with the provided arguments."""
    if not isinstance(args, dict):
        args = {}
    if tool == "sandbox.clone_repo":
        return clone_public_github(sb, args.get("github_url", ""))
    if tool == "sandbox.checkout":
        return checkout(sb, args.get("ref", ""))
    if tool == "sandbox.run":
        try:
            timeout = int(args.get("timeout_sec", 120))
        except (ValueError, TypeError):
            timeout = 120
        return run_cmd(sb, args.get("cmd", ""), timeout_sec=timeout)
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
    return {"ok": False, "error": f"Tool not allowed: {tool}"}


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
    fix_all: bool = False  # Continue until all tests pass
    max_steps_without_progress: int = 10  # Early termination if no progress
    collect_finetuning_data: bool = False  # Collect successful patches for fine-tuning


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

    try:
        write_jsonl(log_dir, {"phase": "init", "cfg": cfg.__dict__})

        # ingest repo
        r = clone_public_github(sb, cfg.github_url)
        write_jsonl(log_dir, {"phase": "clone", "result": r})
        if not r.get("ok"):
            return {"ok": False, "error": r.get("error") or r.get("stderr")}

        if cfg.ref:
            co = checkout(sb, cfg.ref)
            write_jsonl(log_dir, {"phase": "checkout", "result": co})
            if not co.get("ok"):
                return {"ok": False, "error": co.get("stderr")}

        reset_hard(sb)
        tree = list_tree(sb, max_files=2000)
        repo_tree_text = "\n".join(tree.get("files", [])) if tree.get("ok") else ""

        # Detect QuixBugs repository structure
        is_quixbugs = "python_testcases/" in repo_tree_text and "python_programs/" in repo_tree_text

        # If fix_all mode, use unlimited steps
        max_iterations = float('inf') if cfg.fix_all else cfg.max_steps
        step = 0

        while step < max_iterations:
            # Progress reporting
            print(f"\n[Step {step}] Running tests...")
            # measure
            v = run_tests(sb, cfg.test_cmd, timeout_sec=180)
            print(f"[Step {step}] Tests: {'PASS' if v.ok else 'FAIL'} | Failing: {len(v.failing_tests)} tests")
            write_jsonl(log_dir, {
                "phase": "measure",
                "step": step,
                "tests_ok": v.ok,
                "exit_code": v.exit_code,
                "failing_tests": v.failing_tests,
                "sig": v.sig,
            })
            if v.ok:
                print(f"\n✅ SUCCESS! All tests passing after {step} steps.")
                return {
                    "ok": True,
                    "sandbox": sb.root,
                    "repo_dir": sb.repo_dir,
                    "steps_taken": step,
                    "fix_all": cfg.fix_all,
                }

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
                print(f"   Minimum failing tests: {min_failing_tests}, Current: {current_failing}")
                return {
                    "ok": False,
                    "error": "no_progress",
                    "sandbox": sb.root,
                    "repo_dir": sb.repo_dir,
                    "steps_taken": step,
                    "min_failing_tests": min_failing_tests,
                    "current_failing_tests": current_failing,
                }

            # Track signature for stall detection
            sig_history.append(v.sig)
            if len(sig_history) > 5:
                sig_history.pop(0)

            # Track distinct signatures for multi-bug detection
            distinct_sigs.add(v.sig)
            if len(distinct_sigs) > 1:
                print(f"[Step {step}] 🐛 Multi-bug detected: {len(distinct_sigs)} distinct error signatures")

            # Detect stall: same sig repeats 3 times OR no progress after 3 patches
            is_stalled = (
                sig_history.count(v.sig) >= 3 or
                (patch_attempts >= 3 and len(v.failing_tests) > 0)
            )

            # controller policy
            pd = choose_policy(cfg.test_cmd, v)
            print(f"[Step {step}] Intent: {pd.intent} | Subgoal: {pd.subgoal[:60]}...")

            # If stalled, force evidence gathering
            if is_stalled:
                pd.intent = "gather_evidence"
                pd.subgoal = "Collect more context: list_tree, grep for error symbols, read new files"
                write_jsonl(log_dir, {"phase": "stall_detected", "step": step, "sig": v.sig, "patch_attempts": patch_attempts})
                print(f"[Step {step}] ⚠️  Stall detected - switching to evidence gathering")

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
                "test_cmd": cfg.test_cmd,
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
            for t in cfg.temps:
                resp = call_model(model_input, temperature=t)
                write_jsonl(log_dir, {"phase": "model", "step": step, "temp": t, "resp": resp})

                mode = resp.get("mode")
                if mode == "tool_request":
                    # execute requested tools; then continue to next iteration
                    tool_results = []
                    obs_additions = []
                    for req in (resp.get("requests") or [])[:6]:
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
                            if files:
                                summary += f"Listed {len(files)} files\n"
                        obs_additions.append(summary)
                    
                    # Append to observations buffer with sliding window
                    if obs_additions:
                        new_obs = "\n".join(obs_additions) + "\n"
                        # Sliding window: keep only last 50,000 characters of observations
                        # This prioritizes recent tool results over older context
                        if len(observations) + len(new_obs) > 50000:
                            # Keep the most recent 50,000 characters
                            combined = observations + new_obs
                            observations = combined[-50000:]
                        else:
                            observations += new_obs
                    
                    write_jsonl(log_dir, {"phase": "tools_executed", "step": step, "tool_results": tool_results})
                    # after tool requests we do not patch; re-measure on next loop
                    step += 1
                    break

                if mode == "patch":
                    diff = resp.get("diff") or ""
                    h = _diff_hash(diff)
                    if not diff.strip() or h in bad_hashes:
                        continue
                    patches_to_evaluate.append((diff, t))

            if patches_to_evaluate:
                # Evaluate all patches in parallel
                results = evaluate_patches_parallel(
                    sb, patches_to_evaluate, pd.focus_test_cmd, cfg.test_cmd, max_workers=3
                )
                # Increment patch attempts counter
                patch_attempts += len(patches_to_evaluate)
                # Log all results
                for res in results:
                    write_jsonl(log_dir, {
                        "phase": "candidate_eval",
                        "step": step,
                        "temp": res.temperature,
                        "hash": res.diff_hash,
                        "ok": res.ok,
                        "info": res.info[:15000],
                    })
                    if not res.ok:
                        bad_hashes.add(res.diff_hash)
                # Find first successful patch
                winner_result = find_first_successful_patch(results)
                if winner_result:
                    winner = winner_result.diff

            if not winner:
                write_jsonl(log_dir, {"phase": "no_winner", "step": step})
                continue

            # apply winner to main repo
            ap = apply_patch(sb, winner)
            write_jsonl(log_dir, {"phase": "apply_winner", "step": step, "hash": _diff_hash(winner), "result": ap})
            if not ap.get("ok"):
                bad_hashes.add(_diff_hash(winner))
                reset_hard(sb)
                continue
            
            # Collect fine-tuning data if enabled
            if cfg.collect_finetuning_data:
                finetuning_entry = {
                    "phase": "finetuning_data",
                    "step": step,
                    "github_url": cfg.github_url,
                    "test_cmd": cfg.test_cmd,
                    "failure_output": (v.stdout or "") + "\n" + (v.stderr or ""),
                    "failing_tests": v.failing_tests,
                    "error_signature": v.sig,
                    "intent": pd.intent,
                    "subgoal": pd.subgoal,
                    "successful_patch": winner,
                    "patch_hash": _diff_hash(winner),
                    "files_used": [f.get("path") for f in files if f.get("ok")],
                }
                write_jsonl(log_dir, finetuning_entry)
            
            # after applying, loop continues; controller will re-measure

            # Increment step counter
            step += 1

        return {
            "ok": False,
            "error": "max_steps_reached",
            "sandbox": sb.root,
            "repo_dir": sb.repo_dir,
            "steps_taken": step,
            "fix_all": cfg.fix_all,
        }
    finally:
        # Note: sandbox is not destroyed automatically for inspection. Uncomment to auto-clean.
        # destroy_sandbox(sb)
        pass