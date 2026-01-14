"""Evidence pack export for successful bug fixes.

Exports winning diffs and evidence packs for:
- Team sharing
- Model fine-tuning
- Audit trails
"""

import json
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .clock import Clock, SystemClock, make_run_id


@dataclass
class WinnerMetadata:
    """Metadata for a winning patch."""
    
    run_id: str
    timestamp: str
    repo_url: str
    diff_hash: str
    files_changed: List[str]
    lines_added: int
    lines_removed: int
    failing_tests_before: int
    passing_tests_after: int
    steps_taken: int
    model_used: str


@dataclass
class EvidencePack:
    """Complete evidence pack for a winning patch."""
    
    metadata: WinnerMetadata
    winner_diff: str
    failing_output_before: str
    passing_output_after: str
    command_log: List[str]
    tool_requests: List[Dict[str, Any]]


def generate_run_id(
    *,
    clock: Optional[Clock] = None,
    seed_material: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a unique run ID."""
    if clock is None:
        clock = SystemClock()
    return make_run_id(clock=clock, seed_material=seed_material or {})


def compute_diff_hash(diff: str) -> str:
    """Compute a hash of the diff for deduplication."""
    return hashlib.sha256(diff.encode()).hexdigest()


def export_winner_diff(
    results_dir: str,
    run_id: str,
    diff: str,
    metadata: WinnerMetadata,
) -> str:
    """Export the winning diff to a file.

    Args:
        results_dir: Base results directory.
        run_id: Unique run identifier.
        diff: The winning diff.
        metadata: Winner metadata.

    Returns:
        Path to the exported diff file.
    """
    run_dir = os.path.join(results_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    diff_path = os.path.join(run_dir, "winner.diff")
    with open(diff_path, "w") as f:
        f.write(diff)
    
    return diff_path


def export_evidence_pack(
    results_dir: str,
    run_id: str,
    evidence_pack: EvidencePack,
) -> str:
    """Export the complete evidence pack.

    Args:
        results_dir: Base results directory.
        run_id: Unique run identifier.
        evidence_pack: The evidence pack to export.

    Returns:
        Path to the exported evidence pack file.
    """
    run_dir = os.path.join(results_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    pack_path = os.path.join(run_dir, "evidence_pack.json")
    with open(pack_path, "w") as f:
        json.dump(asdict(evidence_pack), f, indent=2)
    
    return pack_path


def export_metadata(
    results_dir: str,
    run_id: str,
    metadata: WinnerMetadata,
) -> str:
    """Export winner metadata to a file.

    Args:
        results_dir: Base results directory.
        run_id: Unique run identifier.
        metadata: Winner metadata.

    Returns:
        Path to the exported metadata file.
    """
    run_dir = os.path.join(results_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    metadata_path = os.path.join(run_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(asdict(metadata), f, indent=2)
    
    return metadata_path


def create_evidence_pack(
    run_id: str,
    repo_url: str,
    diff: str,
    failing_output: str,
    passing_output: str,
    command_log: List[str],
    tool_requests: List[Dict[str, Any]],
    files_changed: List[str],
    lines_added: int,
    lines_removed: int,
    failing_tests_before: int,
    passing_tests_after: int,
    steps_taken: int,
    model_used: str,
    clock: Optional[Clock] = None,
) -> EvidencePack:
    """Create a complete evidence pack.

    Args:
        run_id: Unique run identifier.
        repo_url: Repository URL.
        diff: The winning diff.
        failing_output: Test output before fix.
        passing_output: Test output after fix.
        command_log: List of commands executed.
        tool_requests: List of tool requests made.
        files_changed: List of files changed by the patch.
        lines_added: Number of lines added.
        lines_removed: Number of lines removed.
        failing_tests_before: Number of failing tests before fix.
        passing_tests_after: Number of passing tests after fix.
        steps_taken: Number of steps taken to fix.
        model_used: Model used for generation.

    Returns:
        Complete EvidencePack.
    """
    if clock is None:
        clock = SystemClock()
    metadata = WinnerMetadata(
        run_id=run_id,
        timestamp=clock.now_utc().isoformat(),
        repo_url=repo_url,
        diff_hash=compute_diff_hash(diff),
        files_changed=files_changed,
        lines_added=lines_added,
        lines_removed=lines_removed,
        failing_tests_before=failing_tests_before,
        passing_tests_after=passing_tests_after,
        steps_taken=steps_taken,
        model_used=model_used,
    )
    
    return EvidencePack(
        metadata=metadata,
        winner_diff=diff,
        failing_output_before=failing_output,
        passing_output_after=passing_output,
        command_log=command_log,
        tool_requests=tool_requests,
    )


def export_all(
    results_dir: str,
    evidence_pack: EvidencePack,
) -> Dict[str, str]:
    """Export all evidence pack components.

    Args:
        results_dir: Base results directory.
        evidence_pack: The evidence pack to export.

    Returns:
        Dictionary mapping component names to file paths.
    """
    run_id = evidence_pack.metadata.run_id
    
    diff_path = export_winner_diff(
        results_dir, run_id, evidence_pack.winner_diff, evidence_pack.metadata
    )
    
    pack_path = export_evidence_pack(results_dir, run_id, evidence_pack)
    
    metadata_path = export_metadata(
        results_dir, run_id, evidence_pack.metadata
    )
    
    return {
        "diff": diff_path,
        "evidence_pack": pack_path,
        "metadata": metadata_path,
        "run_dir": os.path.join(results_dir, run_id),
    }
