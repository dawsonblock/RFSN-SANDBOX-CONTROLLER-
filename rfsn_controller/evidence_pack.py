"""Evidence pack export for money lane output.

Exports comprehensive artifacts from controller runs including:
- winner.diff (if any)
- before.txt (baseline failing output)
- after.txt (final output)
- state.json (config, chosen commands, detected project type)
- run.jsonl (full log copy)
- files_changed.txt
"""

import json
import os
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .clock import Clock, SystemClock, make_run_id


@dataclass
class EvidencePackConfig:
    """Configuration for evidence pack export."""

    output_dir: str = "results"
    include_run_jsonl: bool = True
    include_command_log: bool = True


class EvidencePackExporter:
    """Exports evidence packs from controller runs."""

    def __init__(self, config: Optional[EvidencePackConfig] = None):
        self.config = config or EvidencePackConfig()

    def create_run_id(
        self,
        *,
        clock: Optional[Clock] = None,
        seed_material: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a unique run ID based on timestamp."""
        if clock is None:
            clock = SystemClock()
        return make_run_id(clock=clock, seed_material=seed_material or {})

    def export(
        self,
        sandbox_root: str,
        log_dir: str,
        baseline_output: str,
        final_output: str,
        winner_diff: Optional[str],
        state: Dict[str, Any],
        command_log: Optional[List[Dict[str, Any]]] = None,
        run_id: Optional[str] = None,
    ) -> str:
        """Export an evidence pack.

        Args:
            sandbox_root: Path to the sandbox root directory.
            log_dir: Path to the log directory.
            baseline_output: Baseline test output (before fix).
            final_output: Final test output (after fix).
            winner_diff: Winning patch diff (if any).
            state: State dictionary with config and metadata.
            command_log: Optional command execution log.
            run_id: Optional deterministic run id to use for output directory.

        Returns:
            Path to the evidence pack directory.
        """
        if run_id is None:
            run_id = self.create_run_id()
        pack_dir = os.path.join(self.config.output_dir, run_id)
        os.makedirs(pack_dir, exist_ok=True)

        # Export winner.diff
        if winner_diff:
            diff_path = os.path.join(pack_dir, "winner.diff")
            with open(diff_path, "w") as f:
                f.write(winner_diff)

        # Export before.txt
        before_path = os.path.join(pack_dir, "before.txt")
        with open(before_path, "w") as f:
            f.write(baseline_output)

        # Export after.txt
        after_path = os.path.join(pack_dir, "after.txt")
        with open(after_path, "w") as f:
            f.write(final_output)

        # Export state.json
        state_path = os.path.join(pack_dir, "state.json")
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

        # Export run.jsonl
        if self.config.include_run_jsonl:
            log_file = os.path.join(log_dir, "run.jsonl")
            if os.path.exists(log_file):
                shutil.copy(log_file, os.path.join(pack_dir, "run.jsonl"))

        # Export command log
        if self.config.include_command_log and command_log:
            cmd_log_path = os.path.join(pack_dir, "command_log.json")
            with open(cmd_log_path, "w") as f:
                json.dump(command_log, f, indent=2, default=str)

        # Export files_changed.txt
        if winner_diff:
            files_changed = self._extract_files_changed(winner_diff)
            files_path = os.path.join(pack_dir, "files_changed.txt")
            with open(files_path, "w") as f:
                f.write("\n".join(files_changed))

        return pack_dir

    def _extract_files_changed(self, diff: str) -> List[str]:
        """Extract list of changed files from a diff.

        Args:
            diff: The git diff string.

        Returns:
            List of changed file paths.
        """
        files = set()
        for line in diff.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                # Extract file path
                parts = line.split("/")
                if len(parts) > 2:
                    filepath = "/".join(parts[2:])
                    files.add(filepath)
        return sorted(files)

    def export_metadata(
        self,
        pack_dir: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Export additional metadata to the evidence pack.

        Args:
            pack_dir: Path to the evidence pack directory.
            metadata: Additional metadata dictionary.
        """
        metadata_path = os.path.join(pack_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
