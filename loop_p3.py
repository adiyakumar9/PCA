"""
loop_p3.py — Phase 3: Reflexive Grounding (A/B/C Testing).

Groups:
  1. control:    No history, no reflection.
  2. belief:     History warning in prompt (Phase 2).
  3. reflection: Two-step reflect-then-act process (Phase 3).
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
from llm import (
    predict_confidence, generate_fix, 
    generate_fix_with_belief, generate_reflection, generate_fix_with_reflection
)
from runner import run_tests
from tasks import get_all_tasks

def run_single_p3(task, group: str, verbose: bool = True) -> dict:
    run_id = str(uuid.uuid4())[:8]

    if verbose:
        print(f"\n{'─'*62}")
        print(f"  Run {run_id}  │  {group.upper()}  │  {task.task_id}  │  {task.description}")
        print(f"{'─'*62}")

    # 1. Predict
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

    # 2. Reflection / Fix Generation
    reflection_text = None
    if verbose: print(f"  [2/4] Generating fix ({group})…", end=" ", flush=True)
    
    history = get_error_history(task.error_type)
    history_str = (f"Avg Error: {history['avg_err']:.2f}, Success Rate: {history['success_rate']:.1%}")

    if group == "reflection":
        # Step A: Reflect
        reflection_text = generate_reflection(task.broken_function, task.test_code, history_str)
        if verbose: print("\n         reflection ok", end=" ", flush=True)
        # Step B: Act
        fixed = generate_fix_with_reflection(task.broken_function, task.test_code, reflection_text)
    elif group == "belief":
        belief = f"In your history for {task.error_type}: {history_str}. Be careful."
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
        group=group, reflection_text=reflection_text
    )

    return {"success": result.success, "group": group}

def run_experiment_p3(n_runs=30, delay=1.0):
    init_db()
    all_tasks = get_all_tasks()
    
    # Primarily 'high' complexity for Phase 3 challenge
    hard_tasks = [t for t in all_tasks if t.complexity == "high"]
    if not hard_tasks: hard_tasks = all_tasks
    
    print(f"Starting Phase 3 A/B/C Test: {n_runs} runs on {len(hard_tasks)} hard tasks.")
    
    groups = ["control", "belief", "reflection"]
    stats = {g: {"runs": 0, "wins": 0} for g in groups}
    
    for i in range(n_runs):
        group = groups[i % 3] # Rotate groups
        task = random.choice(hard_tasks)
        res = run_single_p3(task, group)
        
        stats[group]["runs"] += 1
        if res["success"]:
            stats[group]["wins"] += 1
            
        if delay > 0: time.sleep(delay)
    
    print("\n" + "═"*62)
    print("  PHASE 3 PRELIMINARY RESULTS")
    print("═"*62)
    for g in groups:
        s = stats[g]
        rate = (s["wins"]/s["runs"]) if s["runs"] > 0 else 0
        print(f"  {g.upper():<12}: {s['wins']}/{s['runs']} success ({rate:.1%})")
    print("═"*62)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    run_experiment_p3(args.runs, args.delay)
