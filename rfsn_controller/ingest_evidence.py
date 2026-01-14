import argparse
import json
import os
from typing import Any, Dict, Iterator, Optional, Tuple

from .action_outcome_memory import (
    ActionOutcomeStore,
    make_action_json_for_patch,
    make_action_key_for_patch,
    make_action_key_for_tool,
    make_context_signature,
    score_action,
)
from .parsers import error_signature, normalize_test_path, parse_pytest_failures
from .policy import choose_policy
from .verifier import VerifyResult


def _ensure_ingest_table(store: ActionOutcomeStore) -> None:
    store.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ingest_offsets (
            pack_id TEXT PRIMARY KEY,
            base_ts INTEGER NOT NULL
        );
        """
    )
    store.conn.commit()


def _get_or_assign_pack_base_ts(store: ActionOutcomeStore, pack_id: str) -> int:
    _ensure_ingest_table(store)
    cur = store.conn.cursor()
    cur.execute(
        "SELECT base_ts FROM ingest_offsets WHERE pack_id = ?",
        (pack_id,),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0])

    cur.execute("SELECT COALESCE(MAX(created_ts), 0) FROM action_outcomes")
    newest = cur.fetchone()[0]
    base_ts = int(newest) + 1

    store.conn.execute(
        "INSERT OR REPLACE INTO ingest_offsets (pack_id, base_ts) VALUES (?, ?)",
        (pack_id, int(base_ts)),
    )
    store.conn.commit()
    return int(base_ts)


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _iter_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        return


def _env_from_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "docker_image": cfg.get("docker_image"),
        "unsafe_host_exec": bool(cfg.get("unsafe_host_exec")),
        "focus_timeout": int(cfg.get("focus_timeout") or 0),
        "full_timeout": int(cfg.get("full_timeout") or 0),
        "enable_sysdeps": bool(cfg.get("enable_sysdeps")),
    }


def _build_context(
    *,
    state: Dict[str, Any],
    before_output: str,
) -> Tuple[Any, str]:
    cfg = state.get("config") if isinstance(state.get("config"), dict) else {}
    project_type = state.get("project_type") or cfg.get("project_type") or "unknown"
    test_cmd = state.get("effective_test_cmd") or cfg.get("test_cmd") or "pytest -q"

    failing_tests = parse_pytest_failures(before_output)
    failing_test_file = (
        normalize_test_path(failing_tests[0]) if failing_tests else None
    )

    sig = error_signature(before_output, "")
    v = VerifyResult(
        ok=False,
        exit_code=1,
        stdout=before_output,
        stderr="",
        failing_tests=failing_tests,
        sig=sig,
    )
    pd = choose_policy(str(test_cmd), v)

    ctx = make_context_signature(
        failure_class=pd.intent,
        repo_type=str(project_type),
        language=str(project_type),
        env=_env_from_cfg(cfg),
        attempt_count=0,
        failing_test_file=failing_test_file,
        sig=sig,
        stalled=False,
    )
    return ctx, str(test_cmd)


def ingest_evidence_pack(
    *,
    store: ActionOutcomeStore,
    pack_dir: str,
) -> Dict[str, int]:
    counts = {
        "tool_records": 0,
        "patch_records": 0,
        "packs": 1,
    }

    state = _read_json(os.path.join(pack_dir, "state.json"))
    if not state:
        return {"tool_records": 0, "patch_records": 0, "packs": 0}

    before_output = _read_text(os.path.join(pack_dir, "before.txt"))
    ctx, _ = _build_context(state=state, before_output=before_output)

    run_jsonl = os.path.join(pack_dir, "run.jsonl")
    pack_id = os.path.basename(pack_dir.rstrip("/"))
    base_ts = _get_or_assign_pack_base_ts(store, pack_id)
    local_ts = 0

    for rec in _iter_jsonl(run_jsonl):
        if rec.get("phase") != "tool_execution":
            continue
        step = rec.get("step", 0)
        results = rec.get("results", [])
        if not isinstance(results, list):
            continue
        for i, r in enumerate(results):
            if not isinstance(r, dict):
                continue
            tool = r.get("tool", "")
            args = r.get("args", {})
            tr = r.get("result", {})
            if not isinstance(args, dict) or not isinstance(tr, dict):
                continue
            outcome = "success" if tr.get("ok") else "fail"
            s = score_action(
                outcome=outcome,
                exec_time_ms=0,
                command_count=1,
                diff_lines=0,
                regressions=0,
            )
            store.record(
                source_run_id=f"ingest:{pack_id}:step{step}:tool{i}",
                context=ctx,
                action_type="tool_request",
                action_key=make_action_key_for_tool(str(tool), args),
                action_json={"tool": tool, "args": args},
                outcome=outcome,
                score=s,
                confidence_weight=1.0,
                exec_time_ms=0,
                command_count=1,
                diff_lines=0,
                regressions=0,
                created_ts=int(base_ts + local_ts),
            )
            local_ts += 1
            counts["tool_records"] += 1

    winner_path = os.path.join(pack_dir, "winner.diff")
    if os.path.exists(winner_path):
        diff = _read_text(winner_path)
        if diff.strip():
            action_json = make_action_json_for_patch(diff)
            diff_lines = int(action_json.get("diff_lines", 0))
            s = score_action(
                outcome="success",
                exec_time_ms=0,
                command_count=2,
                diff_lines=diff_lines,
                regressions=0,
            )
            store.record(
                source_run_id=f"ingest:{pack_id}:winner",
                context=ctx,
                action_type="patch",
                action_key=make_action_key_for_patch(diff),
                action_json=action_json,
                outcome="success",
                score=s,
                confidence_weight=1.0,
                exec_time_ms=0,
                command_count=2,
                diff_lines=diff_lines,
                regressions=0,
                created_ts=int(base_ts + local_ts),
            )
            local_ts += 1
            counts["patch_records"] += 1

    return counts


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--learning-db", required=True)
    p.add_argument("--results-dir", default="results")
    p.add_argument("--learning-half-life-days", type=int, default=14)
    p.add_argument("--learning-max-age-days", type=int, default=90)
    p.add_argument("--learning-max-rows", type=int, default=20000)
    args = p.parse_args()

    db_path = os.path.expanduser(args.learning_db)
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    results_dir = os.path.expanduser(args.results_dir)
    if not os.path.isabs(results_dir):
        results_dir = os.path.abspath(results_dir)

    store = ActionOutcomeStore(
        db_path,
        half_life_days=int(args.learning_half_life_days),
        max_age_days=int(args.learning_max_age_days),
        max_rows=int(args.learning_max_rows),
    )

    total_tools = 0
    total_patches = 0
    total_packs = 0

    try:
        if os.path.isdir(results_dir):
            for name in sorted(os.listdir(results_dir)):
                pack_dir = os.path.join(results_dir, name)
                if not os.path.isdir(pack_dir):
                    continue
                if not name.startswith("run_"):
                    continue
                counts = ingest_evidence_pack(store=store, pack_dir=pack_dir)
                total_tools += counts.get("tool_records", 0)
                total_patches += counts.get("patch_records", 0)
                total_packs += counts.get("packs", 0)
    finally:
        store.close()

    print(
        json.dumps(
            {
                "ok": True,
                "db": db_path,
                "results_dir": results_dir,
                "packs_ingested": total_packs,
                "tool_records": total_tools,
                "patch_records": total_patches,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
