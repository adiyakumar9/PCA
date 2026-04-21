# Phase 1 — Adaptive Learning Experiment

Validates one hypothesis: **can prediction-error signals improve LLM behavior over time?**

The loop: pick a broken function → predict fix success (0–1) → generate fix →
run tests → log (prediction, outcome, discrepancy) to SQLite.

---

## Setup (5 minutes)

```bash
# 1. Clone / copy this folder, then:
cd phase1

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
# (Windows: set ANTHROPIC_API_KEY=sk-ant-...)

# 5. Smoke test — verifies your runner works before spending API credits
python test_runner_smoke.py
```

Expected smoke test output:
```
  task_001: PASS  (4 passed, 0 failed)
  task_002: PASS  (5 passed, 0 failed)
  task_003: PASS  (5 passed, 0 failed)

  Runner is working correctly. Ready to run `python loop.py`.
```

---

## Running the experiment

```bash
# Quick test — 10 runs, see if everything works end-to-end
python loop.py --runs 10

# Full experiment — 50 runs (recommended minimum for Gate 1)
python loop.py --runs 50

# More data = better calibration signal
python loop.py --runs 100 --delay 0.5

# Quiet mode — no per-run output, just checkpoints
python loop.py --runs 50 --quiet

# Focus on one task
python loop.py --runs 20 --task task_003
```

---

## Analysis

```bash
# Print full report (calibration, trends, Gate 1 verdict)
python analyze.py

# Also save to report.txt
python analyze.py --export
```

Sample output:
```
════════════════════════════════════════════════════════════════
  PHASE 1 ANALYSIS REPORT
════════════════════════════════════════════════════════════════
  Total runs            : 50
  Actual success rate   : 82.0%  ████████████████░░░░
  Directional accuracy  : 72.0%  ██████████████░░░░░░  (target > 60%)
  Avg prediction error  : 0.218  (target < 0.30)

  GATE 1 ASSESSMENT  [✓]
  Verdict  : PASS — proceed to Phase 2 (grounding validation)
```

---

## File structure

```
phase1/
├── db.py                   # SQLite schema + all queries
├── llm.py                  # predict_confidence() + generate_fix()
├── runner.py               # run pytest in subprocess, return pass/fail
├── tasks.py                # 6 broken functions + test cases
├── loop.py                 # main experiment loop (CLI entry point)
├── analyze.py              # calibration report + Gate 1 assessment
├── test_runner_smoke.py    # pre-flight check before spending API credits
├── requirements.txt
└── README.md
```

---

## Database schema

```sql
tasks        (task_id, description, broken_function, test_code, error_type, complexity)
predictions  (run_id, task_id, predicted_confidence, reasoning, error_type_predicted, ...)
outcomes     (run_id, task_id, fixed_function, actual_success, tests_passed, error_message, ...)

-- View (auto-computed):
logs         (all of the above + prediction_error, prediction_outcome)
```

Query the raw data directly:
```bash
sqlite3 phase1.db "SELECT run_id, task_id, predicted_confidence, actual_success, prediction_error FROM logs LIMIT 20;"
```

---

## Collecting 50+ samples fast

```bash
# Parallel runs in separate terminals (each uses its own run_ids, SQLite handles concurrent writes)
python loop.py --runs 25 --quiet &
python loop.py --runs 25 --quiet &
wait
python analyze.py
```

Or just run one longer session:
```bash
python loop.py --runs 100 --delay 0.5 --quiet
```

---

## Gate 1 criteria (proceed to Phase 2?)

| Metric               | Threshold  | Meaning                                  |
|----------------------|------------|------------------------------------------|
| Directional accuracy | > 60%      | Predictions are non-random               |
| Avg prediction error | < 0.30     | Confidence scores are meaningfully scaled |

If **both pass**: proceed to Phase 2 (grounding validation A/B test).
If **marginal**: tune the prediction prompt in `llm.py` → `PREDICTION_SYSTEM`.
If **fail**: the domain or metric is broken — redesign before adding complexity.

---

## Troubleshooting

**`ModuleNotFoundError: anthropic`** → `pip install anthropic`

**`AuthenticationError`** → check your `ANTHROPIC_API_KEY` is set and valid

**Smoke test failing** → check pytest is installed: `pip install pytest`

**Low directional accuracy (< 55%)** → try adding this line to `PREDICTION_SYSTEM` in `llm.py`:
> "If a bug is a simple typo or method name error, confidence should be 0.85+.
>  If the logic requires deep restructuring, confidence should be 0.4 or lower."

---

## What comes next (Phase 2)

Once Gate 1 passes, Phase 2 tests whether injecting belief updates into the LLM
prompt actually changes behavior. The key experiment: A/B test the same tasks with
and without a "belief block" derived from your Phase 1 prediction-error clusters.
If the belief group outperforms control, the grounding mechanism works.
