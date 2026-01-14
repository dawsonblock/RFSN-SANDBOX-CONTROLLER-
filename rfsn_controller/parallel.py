"""Parallel patch evaluation for the RFSN controller.

This module provides utilities for evaluating multiple candidate patches
in parallel using concurrent.futures, significantly reducing the time spent
testing patches from different temperature samples.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import List, Tuple, Optional

from .sandbox import Sandbox, make_worktree, drop_worktree, apply_patch_in_dir, run_cmd


@dataclass
class PatchResult:
    """Result of evaluating a single patch."""

    diff: str
    diff_hash: str
    ok: bool
    info: str
    temperature: float


def _evaluate_single_patch(
    sb: Sandbox,
    diff: str,
    diff_hash: str,
    focus_cmd: str,
    full_cmd: str,
    temperature: float,
) -> PatchResult:
    """Evaluate a single patch in an isolated worktree.

    Args:
        sb: The sandbox containing the repository.
        diff: The unified diff to apply.
        diff_hash: Hash of the diff for deduplication.
        focus_cmd: Focused test command for quick feedback.
        full_cmd: Full test command for verification.
        temperature: Temperature used to generate this patch.

    Returns:
        A PatchResult with evaluation outcome.
    """
    wt = None
    try:
        wt = make_worktree(sb, suffix=diff_hash[:10])
        ap = apply_patch_in_dir(wt, diff)
        if not ap.get("ok"):
            return PatchResult(
                diff=diff,
                diff_hash=diff_hash,
                ok=False,
                info=f"apply_failed: {ap.get('stderr','')}{ap.get('stdout','')}",
                temperature=temperature,
            )
        r1 = run_cmd(Sandbox(sb.root, wt), focus_cmd, timeout_sec=90)
        if not r1.get("ok"):
            return PatchResult(
                diff=diff,
                diff_hash=diff_hash,
                ok=False,
                info="focus_failed:\n" + (r1.get("stdout", "") + r1.get("stderr", "")),
                temperature=temperature,
            )
        r2 = run_cmd(Sandbox(sb.root, wt), full_cmd, timeout_sec=180)
        if r2.get("ok"):
            return PatchResult(
                diff=diff,
                diff_hash=diff_hash,
                ok=True,
                info="PASS",
                temperature=temperature,
            )
        return PatchResult(
            diff=diff,
            diff_hash=diff_hash,
            ok=False,
            info="full_failed:\n" + (r2.get("stdout", "") + r2.get("stderr", "")),
            temperature=temperature,
        )
    except Exception as e:
        return PatchResult(
            diff=diff,
            diff_hash=diff_hash,
            ok=False,
            info=f"exception: {type(e).__name__}: {str(e)}",
            temperature=temperature,
        )
    finally:
        if wt:
            try:
                drop_worktree(sb, wt)
            except Exception:
                pass


def evaluate_patches_parallel(
    sb: Sandbox,
    patches: List[Tuple[str, float]],  # List of (diff, temperature)
    focus_cmd: str,
    full_cmd: str,
    max_workers: int = 3,
) -> List[PatchResult]:
    """Evaluate multiple patches in parallel using thread pool.

    Args:
        sb: The sandbox containing the repository.
        patches: List of (diff, temperature) tuples to evaluate.
        focus_cmd: Focused test command for quick feedback.
        full_cmd: Full test command for verification.
        max_workers: Maximum number of parallel evaluations.

    Returns:
        List of PatchResult objects in the same order as input patches.
    """
    import hashlib

    # Pre-compute hashes and create index mapping
    indexed_patches = []
    for idx, (diff, temp) in enumerate(patches):
        diff_hash = hashlib.sha256(
            (diff or "").encode("utf-8", errors="ignore")
        ).hexdigest()
        indexed_patches.append((idx, diff, temp, diff_hash))

    results: List[Optional[PatchResult]] = [None] * len(patches)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all patch evaluations
        future_to_index = {}
        for idx, diff, temp, diff_hash in indexed_patches:
            future = executor.submit(
                _evaluate_single_patch,
                sb,
                diff,
                diff_hash,
                focus_cmd,
                full_cmd,
                temp,
            )
            future_to_index[future] = idx

        # Collect results as they complete, preserving order
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                result = future.result()
                results[idx] = result
            except Exception as e:
                # If evaluation itself fails, create a failure result
                _, diff, temp, diff_hash = indexed_patches[idx]
                results[idx] = PatchResult(
                    diff=diff,
                    diff_hash=diff_hash,
                    ok=False,
                    info=f"evaluation_exception: {type(e).__name__}: {str(e)}",
                    temperature=temp,
                )

    return [r for r in results if r is not None]


def find_first_successful_patch(results: List[PatchResult]) -> Optional[PatchResult]:
    """Find the first successful patch from evaluation results.

    Args:
        results: List of PatchResult objects.

    Returns:
        The first PatchResult with ok=True, or None if none succeeded.
    """
    for result in results:
        if result.ok:
            return result
    return None
