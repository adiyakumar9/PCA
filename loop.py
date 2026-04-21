"""
loop.py — Main experiment runner.

Each iteration:
  1. Pick a task
  2. Ask LLM to predict confidence (0-1)
  3. Ask LLM to generate fix
  4. Run pytest on the fix
  5. Log prediction + outcome to SQLite

Usage:
    python loop.py              # 50 runs, default settings
    python loop.py --runs 100   # more data
    python loop.py --task task_001  # single task only
    python loop.py --quiet      # suppress per-run output
"""

import uuid
import time
import random
import argparse
from datetime import datetime

from db import (
    init_db, insert_task, insert_prediction,
    insert_outcome, hash_context, get_stats,
)
from llm import predict_confidence, generate_fix
from runner import run_tests
from tasks import get_all_tasks, get_task


# ── Single run ────────────────────────────────────────────────────────────────

def run_single(task, verbose: bool = True) -> dict:
    """
    Execute one full cycle for a task.
    Returns a summary dict (also written to DB as a side effect).
    """
    run_id = str(uuid.uuid4())[:8]

    if verbose:
        print(f"\n{'─'*62}")
        print(f"  Run {run_id}  │  {task.task_id}  │  {task.description}")
        print(f"{'─'*62}")

    # ── Step 1: Predict ───────────────────────────────────────────────────
    if verbose:
        print("  [1/4] Predicting…", end=" ", flush=True)

    try:
        pred = predict_confidence(task.broken_function, task.test_code)
    except Exception as exc:
        print(f"\n  ERROR in predict: {exc}")
        return {"run_id": run_id, "error": str(exc)}

    conf = pred["confidence"]

    if verbose:
        print(f"confidence={conf:.2f}  type={pred.get('error_type')}  "
              f"complexity={pred.get('complexity')}")
        print(f"         reasoning: {pred.get('reasoning', '')[:80]}")

    insert_prediction(
        run_id=run_id,
        task_id=task.task_id,
        predicted_confidence=conf,
        reasoning=pred.get("reasoning"),
        error_type_predicted=pred.get("error_type"),
        complexity_predicted=pred.get("complexity"),
        context_hash=hash_context(task.broken_function),
    )

    # ── Step 2: Generate fix ──────────────────────────────────────────────
    if verbose:
        print("  [2/4] Generating fix…", end=" ", flush=True)

    try:
        fixed = generate_fix(task.broken_function, task.test_code)
    except Exception as exc:
        print(f"\n  ERROR in generate_fix: {exc}")
        insert_outcome(
            run_id=run_id, task_id=task.task_id,
            fixed_function=None, actual_success=False,
            error_message=str(exc),
        )
        return {"run_id": run_id, "error": str(exc)}

    if verbose:
        first_line = fixed.split("\n")[0]
        print(f"ok  ({first_line[:60]}…)")

    # ── Step 3: Run tests ─────────────────────────────────────────────────
    if verbose:
        print("  [3/4] Running tests…", end=" ", flush=True)

    result = run_tests(fixed, task.test_code)
    status = "PASS" if result.success else "FAIL"

    if verbose:
        print(f"{status}  passed={result.tests_passed}  "
              f"failed={result.tests_failed}  {result.execution_time_ms}ms")
        if not result.success and result.error_message:
            snippet = result.error_message.strip().split("\n")[0][:100]
            print(f"         error: {snippet}")

    # ── Step 4: Log ───────────────────────────────────────────────────────
    insert_outcome(
        run_id=run_id,
        task_id=task.task_id,
        fixed_function=fixed,
        actual_success=result.success,
        tests_passed=result.tests_passed,
        tests_failed=result.tests_failed,
        error_message=result.error_message,
        execution_time_ms=result.execution_time_ms,
    )

    discrepancy = abs(conf - (1.0 if result.success else 0.0))

    if verbose:
        print(f"  [4/4] Logged  │  prediction_error = {discrepancy:.2f}")

    return {
        "run_id":                run_id,
        "task_id":               task.task_id,
        "predicted_confidence":  conf,
        "actual_success":        result.success,
        "discrepancy":           discrepancy,
    }


# ── Experiment ────────────────────────────────────────────────────────────────

def run_experiment(
    n_runs:        int   = 50,
    delay_seconds: float = 1.0,
    verbose:       bool  = True,
    task_filter:   str   = None,
) -> list[dict]:
    """
    Run n_runs cycles.  Tasks are sampled randomly (or filtered to task_filter).
    Progress stats are printed every 10 runs.
    """
    print(f"\n{'═'*62}")
    print(f"  Phase 1 Experiment  │  {n_runs} runs  │  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'═'*62}")

    init_db()

    all_tasks = get_all_tasks()
    if task_filter:
        all_tasks = [t for t in all_tasks if t.task_id == task_filter]
        if not all_tasks:
            print(f"No task found with id {task_filter!r}. Available: "
                  + ", ".join(t.task_id for t in get_all_tasks()))
            return []

    # Seed the tasks table
    for t in all_tasks:
        insert_task(
            task_id=t.task_id, description=t.description,
            broken_function=t.broken_function, test_code=t.test_code,
            error_type=t.error_type, complexity=t.complexity,
        )

    print(f"  Loaded {len(all_tasks)} task(s). Starting loop…")

    results = []

    for i in range(n_runs):
        task = random.choice(all_tasks)
        result = run_single(task, verbose=verbose)
        results.append(result)

        # Rolling stats every 10 runs
        if (i + 1) % 10 == 0:
            s = get_stats()
            print(f"\n  ── Checkpoint {i+1}/{n_runs} ──────────────────────────")
            print(f"     Directional accuracy : {s['directional_accuracy']:.1%}")
            print(f"     Avg prediction error : {s['avg_prediction_error']:.3f}")
            print(f"     Actual success rate  : {s['actual_success_rate']:.1%}")
            print()

        if delay_seconds > 0 and i < n_runs - 1:
            time.sleep(delay_seconds)

    # Final summary
    s = get_stats()
    print(f"\n{'═'*62}")
    print("  EXPERIMENT COMPLETE")
    print(f"{'═'*62}")
    print(f"  Total runs            : {s['total_runs']}")
    print(f"  Directional accuracy  : {s['directional_accuracy']:.1%}  (target > 60%)")
    print(f"  Avg prediction error  : {s['avg_prediction_error']:.3f}  (target < 0.30)")
    print(f"  Actual success rate   : {s['actual_success_rate']:.1%}")
    print(f"{'═'*62}")
    print("\n  Run `python analyze.py` for the full report.\n")

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 1 — prediction-error experiment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--runs",   type=int,   default=50,  help="Number of iterations")
    parser.add_argument("--delay",  type=float, default=1.0, help="Seconds between runs")
    parser.add_argument("--task",   type=str,   default=None, help="Run one specific task_id only")
    parser.add_argument("--quiet",  action="store_true",      help="Suppress per-run output")
    args = parser.parse_args()

    run_experiment(
        n_runs=args.runs,
        delay_seconds=args.delay,
        verbose=not args.quiet,
        task_filter=args.task,
    )
