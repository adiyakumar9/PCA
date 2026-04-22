"""
db.py — SQLite schema + all database operations for Phase 1.
Three tables: tasks, predictions, outcomes.
One view:    logs (joined, with prediction_error computed).
"""

import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path("phase1.db")

# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id      TEXT PRIMARY KEY,
    description  TEXT,
    broken_function TEXT NOT NULL,
    test_code    TEXT NOT NULL,
    error_type   TEXT,
    complexity   TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
)
"""

CREATE_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS predictions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT NOT NULL UNIQUE,
    task_id              TEXT NOT NULL,
    predicted_confidence REAL NOT NULL,
    reasoning            TEXT,
    error_type_predicted TEXT,
    complexity_predicted TEXT,
    context_hash         TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
)
"""

CREATE_OUTCOMES = """
CREATE TABLE IF NOT EXISTS outcomes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            TEXT NOT NULL UNIQUE,
    task_id           TEXT NOT NULL,
    fixed_function    TEXT,
    actual_success    INTEGER NOT NULL,
    tests_passed      INTEGER DEFAULT 0,
    tests_failed      INTEGER DEFAULT 0,
    error_message     TEXT,
    execution_time_ms INTEGER,
    experiment_group  TEXT DEFAULT 'control',
    reflection_text   TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
)
"""

# Joined view — the main analysis surface
CREATE_LOGS_VIEW = """
CREATE VIEW IF NOT EXISTS logs AS
SELECT
    p.run_id,
    p.task_id,
    p.predicted_confidence,
    p.reasoning,
    p.error_type_predicted                                AS error_type,
    p.complexity_predicted,
    p.context_hash,
    o.actual_success,
    o.tests_passed,
    o.tests_failed,
    o.error_message,
    o.execution_time_ms,
    o.experiment_group,
    o.reflection_text,
    p.created_at                                          AS predicted_at,
    o.created_at                                          AS resolved_at,
    ABS(p.predicted_confidence - o.actual_success)        AS prediction_error,
    CASE
        WHEN p.predicted_confidence >= 0.5 AND o.actual_success = 1 THEN 'true_positive'
        WHEN p.predicted_confidence <  0.5 AND o.actual_success = 0 THEN 'true_negative'
        WHEN p.predicted_confidence >= 0.5 AND o.actual_success = 0 THEN 'false_positive'
        ELSE 'false_negative'
    END AS prediction_outcome
FROM predictions p
JOIN outcomes o ON p.run_id = o.run_id
"""

# ── Connection ────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_TASKS)
        conn.execute(CREATE_PREDICTIONS)
        conn.execute(CREATE_OUTCOMES)
        
        # Migrations for Phase 2 & 3
        try:
            conn.execute("ALTER TABLE outcomes ADD COLUMN experiment_group TEXT DEFAULT 'control'")
        except sqlite3.OperationalError:
            pass 
        try:
            conn.execute("ALTER TABLE outcomes ADD COLUMN reflection_text TEXT")
        except sqlite3.OperationalError:
            pass 
            
        conn.execute("DROP VIEW IF EXISTS logs")
        conn.execute(CREATE_LOGS_VIEW)
        conn.commit()
    print(f"Database ready at {DB_PATH.resolve()}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_context(broken_function: str) -> str:
    """Short fingerprint of the broken function for deduplication analysis."""
    return hashlib.md5(broken_function.encode()).hexdigest()[:12]


# ── Writes ────────────────────────────────────────────────────────────────────

def insert_task(task_id, description, broken_function, test_code,
                error_type=None, complexity=None):
    with get_connection() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO tasks
               (task_id, description, broken_function, test_code, error_type, complexity)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, description, broken_function, test_code, error_type, complexity)
        )
        conn.commit()


def insert_prediction(run_id, task_id, predicted_confidence, reasoning=None,
                      error_type_predicted=None, complexity_predicted=None,
                      context_hash=None):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO predictions
               (run_id, task_id, predicted_confidence, reasoning,
                error_type_predicted, complexity_predicted, context_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, task_id, predicted_confidence, reasoning,
             error_type_predicted, complexity_predicted, context_hash)
        )
        conn.commit()


def insert_outcome(run_id, task_id, fixed_function, actual_success,
                    tests_passed=0, tests_failed=0, error_message=None,
                    execution_time_ms=None, group="control", reflection_text=None):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO outcomes
               (run_id, task_id, fixed_function, actual_success, tests_passed,
                tests_failed, error_message, execution_time_ms, experiment_group, reflection_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, task_id, fixed_function, int(actual_success),
             tests_passed, tests_failed, error_message, execution_time_ms, group, reflection_text)
        )
        conn.commit()


# ── Reads ─────────────────────────────────────────────────────────────────────

def get_error_history(error_type: str) -> dict:
    """
    Retrieve past performance for a specific error type from Phase 1.
    """
    with get_connection() as conn:
        row = conn.execute("""
            SELECT AVG(prediction_error) as avg_err, AVG(actual_success) as success_rate
            FROM logs
            WHERE error_type = ?
        """, (error_type,)).fetchone()

        if not row or row['avg_err'] is None:
            return {"avg_err": 0.0, "success_rate": 1.0}

        return dict(row)
def get_all_logs() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY predicted_at"
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        if total == 0:
            return {"total_runs": 0, "directional_accuracy": 0,
                    "avg_prediction_error": 0, "actual_success_rate": 0}

        correct = conn.execute("""
            SELECT COUNT(*) FROM logs
            WHERE (predicted_confidence >= 0.5 AND actual_success = 1)
               OR (predicted_confidence <  0.5 AND actual_success = 0)
        """).fetchone()[0]

        avg_error = conn.execute(
            "SELECT AVG(prediction_error) FROM logs"
        ).fetchone()[0]

        success_rate = conn.execute(
            "SELECT AVG(actual_success) FROM logs"
        ).fetchone()[0]

        return {
            "total_runs":            total,
            "directional_accuracy":  correct / total,
            "avg_prediction_error":  avg_error or 0.0,
            "actual_success_rate":   success_rate or 0.0,
        }
