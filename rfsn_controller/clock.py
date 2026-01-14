import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Protocol


class Clock(Protocol):
    def now_utc(self) -> datetime:
        ...

    def time(self) -> float:
        ...

    def perf_counter(self) -> float:
        ...

    def monotonic_steps(self) -> int:
        ...

    def tick(self, steps: int = 1) -> None:
        ...


@dataclass
class FrozenClock:
    start_time_utc: datetime
    step_seconds: float = 0.0
    _steps: int = 0

    def now_utc(self) -> datetime:
        return self.start_time_utc + timedelta(seconds=float(self.step_seconds) * int(self._steps))

    def time(self) -> float:
        return float(self.now_utc().timestamp())

    def perf_counter(self) -> float:
        return float(self._steps)

    def monotonic_steps(self) -> int:
        return int(self._steps)

    def tick(self, steps: int = 1) -> None:
        self._steps += int(steps)


@dataclass
class SystemClock:
    _steps: int = 0

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def time(self) -> float:
        return float(time.time())

    def perf_counter(self) -> float:
        return float(time.perf_counter())

    def monotonic_steps(self) -> int:
        return int(self._steps)

    def tick(self, steps: int = 1) -> None:
        self._steps += int(steps)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_run_id(
    *,
    clock: Clock,
    seed_material: Dict[str, Any],
) -> str:
    dt = clock.now_utc()
    ts = dt.strftime("%Y%m%d_%H%M%S")
    h = hashlib.sha256(_stable_json(seed_material).encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"run_{ts}_{h}"


def parse_utc_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
