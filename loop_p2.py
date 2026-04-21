"""
loop_p2.py — Phase 2: Grounding Validation (A/B Testing).

Each iteration:
  1. Pick a task
  2. Assign to 'control' or 'belief' group
  3. Generate fix (with or without belief injection)
  4. Run pytest and log results to compare performance
"""

import uuid
import time
import random
import argparse
from datetime import datetime

from db import (
    init_db, insert_task, insert_prediction,
    insert_outcome, hash_context, get_error_history
)
from llm import predict_confidence, generate_fix, generate_fix_with_belief
from runner import run_tests
from tasks import get_all_tasks

def run_single_p2(task, group: str, verbose: bool = True) -> dict:
    run_id = str(uuid.uuid4())[:8]

    if verbose:
        print(f"\n{'─'*62}")
        print(f"  Run {run_id}  │  {group.upper()}  │  {task.task_id}  │  {task.description}")
        print(f"{'─'*62}")

    # 1. Predict (Always same as Phase 1)
    if verbose: print("  [1/4] Predicting…", end=" ", flush=True)
    pred = predict_confidence(task.broken_function, task.test_code)
    conf = pred["confidence"]
    if verbose: print(f"conf={conf:.2f}")

    insert_prediction(
        run_id=run_id, task_id=task.task_id,
        predicted_confidence=conf, reasoning=pred.get("reasoning"),
        error_type_predicted=pred.get("error_type"),
        complexity_predicted=pred.get("complexity"),
        context_hash=hash_context(task.broken_function),
    )

    # 2. Generate Fix (A/B logic)
    if verbose: print(f"  [2/4] Generating fix ({group})…", end=" ", flush=True)
    
    if group == "belief":
        history = get_error_history(task.error_type)
        # Only inject if we have some significant error history
        if history["avg_err"] > 0.15:
            belief = (f"In your history, you have an average error of {history['avg_err']:.2f} "
                     f"on {task.error_type} tasks (Success rate: {history['success_rate']:.1%}). "
                     f"Be extra careful to avoid standard {task.error_type} patterns.")
        else:
            belief = f"Be careful with this {task.error_type} task."
        
        fixed = generate_fix_with_belief(task.broken_function, task.test_code, belief)
    else:
        fixed = generate_fix(task.broken_function, task.test_code)
    
    if verbose: print("ok")

    # 3. Run tests
    if verbose: print("  [3/4] Running tests…", end=" ", flush=True)
    result = run_tests(fixed, task.test_code)
    status = "PASS" if result.success else "FAIL"
    if verbose: print(f"{status} ({result.tests_passed} passed)")

    # 4. Log
    insert_outcome(
        run_id=run_id, task_id=task.task_id,
        fixed_function=fixed, actual_success=result.success,
        tests_passed=result.tests_passed, tests_failed=result.tests_failed,
        error_message=result.error_message, execution_time_ms=result.execution_time_ms,
        group=group
    )

    return {"success": result.success, "group": group}

def run_experiment_p2(n_runs=40, delay=1.0):
    init_db()
    all_tasks = get_all_tasks()
    
    # We want tasks with complexity 'high' primarily for Phase 2
    hard_tasks = [t for t in all_tasks if t.complexity == "high"]
    if not hard_tasks:
        hard_tasks = all_tasks # fallback
    
    print(f"Starting Phase 2 A/B Test: {n_runs} runs on {len(hard_tasks)} hard tasks.")
    
    stats = {"control": {"runs": 0, "wins": 0}, "belief": {"runs": 0, "wins": 0}}
    
    for i in range(n_runs):
        group = "belief" if i % 2 == 0 else "control" # Alternate for balance
        task = random.choice(hard_tasks)
        res = run_single_p2(task, group)
        
        stats[group]["runs"] += 1
        if res["success"]:
            stats[group]["wins"] += 1
            
        if delay > 0: time.sleep(delay)
    
    print("\n" + "═"*62)
    print("  PHASE 2 PRELIMINARY RESULTS")
    print("═"*62)
    for g in ["control", "belief"]:
        s = stats[g]
        rate = (s["wins"]/s["runs"]) if s["runs"] > 0 else 0
        print(f"  {g.upper():<10}: {s['wins']}/{s['runs']} success ({rate:.1%})")
    print("═"*62)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    run_experiment_p2(args.runs, args.delay)
