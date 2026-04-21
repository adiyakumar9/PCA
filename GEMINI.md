# GEMINI.md

## Project Overview
**Phase 1 — Adaptive Learning Experiment (PCA)** is a research project designed to validate whether prediction-error signals can improve Large Language Model (LLM) behavior over time. The core hypothesis is that by forcing the model to predict its own success and then measuring the discrepancy (error) against actual outcomes, we can create a calibration signal for better grounding.

### Architecture
- **Loop (`loop.py`)**: The main driver that orchestrates the experiment cycles.
- **LLM Layer (`llm.py`)**: Handles interactions with Anthropic's Claude (default: `claude-sonnet-4-5`) for both success prediction and code generation.
- **Task Registry (`tasks.py`)**: Contains a curated set of broken Python functions with varying error types (off-by-one, logic errors, etc.) and associated test cases.
- **Execution Engine (`runner.py`)**: Runs the generated code against tests in a isolated subprocess using `pytest`.
- **Data Layer (`db.py`)**: Manages a SQLite database (`phase1.db`) to log tasks, predictions, and outcomes.
- **Analysis (`analyze.py`)**: Evaluates the gathered data against "Gate 1" criteria (Directional accuracy > 60% and Avg prediction error < 0.30).

---

## Building and Running

### Prerequisites
- Python 3.10+
- An Anthropic API Key (`ANTHROPIC_API_KEY`)

### Setup
```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

### Running Experiments
```bash
# 1. Pre-flight smoke test (verify runner/pytest setup)
python test_runner_smoke.py

# 2. Run the experiment loop
python loop.py --runs 50

# 3. Focus on a specific task
python loop.py --runs 10 --task task_003
```

### Analysis and Reporting
```bash
# Generate the calibration report and Gate 1 verdict
python analyze.py
```

---

## Development Conventions

### LLM Interactions
- **Prediction**: Returns JSON containing `confidence`, `reasoning`, `error_type`, and `complexity`.
- **Generation**: Follows a "minimal change" rule—only the fixed code is returned, without explanations or markdown formatting.

### Testing
- All tasks must include a `test_code` block that can be executed by `pytest`.
- The `runner.py` uses temporary files to safely execute and evaluate generated code.

### Database
- The schema uses a view called `logs` that automatically calculates `prediction_error` (absolute difference between predicted confidence and actual success).
- Concurrent writes are handled by SQLite's default locking mechanisms, allowing for parallel experiment runs.

### Coding Style
- Type hints are used for core data structures (see `Task` dataclass in `tasks.py`).
- Clear separation between experiment logic (`loop.py`), model interface (`llm.py`), and data persistence (`db.py`).
