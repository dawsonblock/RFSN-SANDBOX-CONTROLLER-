"""Simple JSONL logger for the RFSN controller."""

import json
import os
from typing import Any, Dict, Optional

from .clock import Clock


def ensure_dir(path: str) -> None:
    """Ensure that a directory exists."""
    os.makedirs(path, exist_ok=True)


def write_jsonl(
    log_dir: str,
    record: Dict[str, Any],
    *,
    clock: Optional[Clock] = None,
    ts: Optional[float] = None,
) -> None:
    """Append a record to a JSONL file in the given log directory.

    Args:
        log_dir: Directory where logs should be written.
        record: Arbitrary JSON-serializable dictionary to write.
    """
    ensure_dir(log_dir)
    entry = dict(record)
    if ts is not None:
        entry["ts"] = float(ts)
    elif clock is not None:
        entry["ts"] = float(clock.time())
    else:
        raise ValueError("write_jsonl requires either ts or clock")
    path = os.path.join(log_dir, "run.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
