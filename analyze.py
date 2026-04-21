"""
analyze.py — Full analysis report from phase1.db.

Sections:
  1. Summary stats
  2. Calibration analysis  (are confidence scores meaningful?)
  3. Per-task breakdown     (which tasks are hard vs easy?)
  4. Error trend            (is prediction quality improving?)
  5. Overconfidence audit   (where did high confidence + failure cluster?)
  6. Gate 1 assessment      (should we proceed to Phase 2?)

Usage:
    python analyze.py
    python analyze.py --export   # also write report to report.txt
"""

import argparse
import statistics
from collections import defaultdict
from pathlib import Path

from db import get_all_logs, get_stats, DB_PATH


# ── Helpers ───────────────────────────────────────────────────────────────────

def bar(value: float, width: int = 20, fill: str = "█", empty: str = "░") -> str:
    """ASCII progress bar for a 0-1 value."""
    filled = round(value * width)
    return fill * filled + empty * (width - filled)


DIVIDER     = "─" * 64
THICK_DIV   = "═" * 64


# ── Analysis functions ────────────────────────────────────────────────────────

def summary(logs: list[dict], stats: dict) -> str:
    lines = [
        THICK_DIV,
        "  PHASE 1 ANALYSIS REPORT",
        THICK_DIV,
        f"  Total runs            : {stats['total_runs']}",
        f"  Actual success rate   : {stats['actual_success_rate']:.1%}  "
            f"{bar(stats['actual_success_rate'])}",
        f"  Directional accuracy  : {stats['directional_accuracy']:.1%}  "
            f"{bar(stats['directional_accuracy'])}  (target > 60%)",
        f"  Avg prediction error  : {stats['avg_prediction_error']:.3f}  "
            f"(target < 0.30)",
        "",
    ]
    return "\n".join(lines)


def calibration(logs: list[dict]) -> str:
    """Bucket predictions by confidence range; compare to actual success rate."""
    bins: dict[str, list] = defaultdict(list)
    edges  = [0.0, 0.2, 0.4, 0.6, 0.8, 1.01]
    labels = ["0.0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0"]

    for log in logs:
        c = log["predicted_confidence"]
        for i, (lo, hi) in enumerate(zip(edges, edges[1:])):
            if lo <= c < hi:
                bins[labels[i]].append(log["actual_success"])
                break

    lines = [
        DIVIDER,
        "  CALIBRATION ANALYSIS",
        "  (ideal: actual success in each bin ≈ bin midpoint)",
        DIVIDER,
        f"  {'Confidence':>12}  {'N':>5}  {'Actual Success':>15}  {'Calibrated?':>12}",
        f"  {'':─>12}  {'':─>5}  {'':─>15}  {'':─>12}",
    ]

    midpoints = [0.1, 0.3, 0.5, 0.7, 0.9]

    for label, mid in zip(labels, midpoints):
        items = bins[label]
        if not items:
            lines.append(f"  {label:>12}  {'—':>5}")
            continue
        actual = sum(items) / len(items)
        calibrated = abs(actual - mid) < 0.15
        flag = "OK " if calibrated else "OFF"
        lines.append(
            f"  {label:>12}  {len(items):>5}  {actual:>14.1%}  "
            f"  {flag}  {bar(actual, 14)}"
        )

    lines.append("")
    return "\n".join(lines)


def task_breakdown(logs: list[dict]) -> str:
    by_task: dict[str, list] = defaultdict(list)
    for log in logs:
        by_task[log["task_id"]].append(log)

    lines = [
        DIVIDER,
        "  PER-TASK BREAKDOWN",
        DIVIDER,
        f"  {'Task':>10}  {'Runs':>5}  {'Success':>8}  {'Avg Pred':>9}  {'Avg Err':>8}",
        f"  {'':─>10}  {'':─>5}  {'':─>8}  {'':─>9}  {'':─>8}",
    ]

    for task_id, tlogs in sorted(by_task.items()):
        n             = len(tlogs)
        success_rate  = sum(l["actual_success"] for l in tlogs) / n
        avg_pred      = sum(l["predicted_confidence"] for l in tlogs) / n
        avg_err       = sum(l["prediction_error"] for l in tlogs) / n
        lines.append(
            f"  {task_id:>10}  {n:>5}  {success_rate:>7.1%}  {avg_pred:>9.2f}  {avg_err:>8.3f}"
        )

    lines.append("")
    return "\n".join(lines)


def error_trend(logs: list[dict], window: int = 10) -> str:
    if len(logs) < window:
        return f"\n  Need at least {window} runs for trend analysis.\n"

    errors = [l["prediction_error"] for l in logs]
    lines  = [
        DIVIDER,
        f"  PREDICTION ERROR TREND  (rolling window = {window})",
        "  (declining values = model becoming better calibrated)",
        DIVIDER,
        f"  {'Runs':>12}  {'Avg Error':>10}  {'Chart':>4}",
        f"  {'':─>12}  {'':─>10}",
    ]

    for i in range(0, len(errors), window):
        chunk = errors[i:i + window]
        if len(chunk) < 3:
            break
        avg = statistics.mean(chunk)
        label = f"{i+1}–{i+len(chunk)}"
        lines.append(f"  {label:>12}  {avg:>10.3f}  {bar(avg, 16)}")

    lines.append("")
    return "\n".join(lines)


def overconfidence_audit(logs: list[dict]) -> str:
    fp = [l for l in logs if l["predicted_confidence"] >= 0.7 and l["actual_success"] == 0]
    fn = [l for l in logs if l["predicted_confidence"] <= 0.3 and l["actual_success"] == 1]

    lines = [
        DIVIDER,
        "  CONFIDENCE AUDIT",
        DIVIDER,
        f"  False positives (conf ≥ 0.7, test failed) : {len(fp)}",
        f"  False negatives (conf ≤ 0.3, test passed) : {len(fn)}",
    ]

    if fp:
        lines.append("\n  Top overconfident failures:")
        for l in sorted(fp, key=lambda x: -x["predicted_confidence"])[:5]:
            lines.append(
                f"    run={l['run_id']}  task={l['task_id']}  "
                f"conf={l['predicted_confidence']:.2f}"
            )

    if fn:
        lines.append("\n  Top underconfident successes:")
        for l in sorted(fn, key=lambda x: x["predicted_confidence"])[:5]:
            lines.append(
                f"    run={l['run_id']}  task={l['task_id']}  "
                f"conf={l['predicted_confidence']:.2f}"
            )

    lines.append("")
    return "\n".join(lines)


def gate1_assessment(stats: dict) -> str:
    da = stats["directional_accuracy"]
    ae = stats["avg_prediction_error"]
    n  = stats["total_runs"]

    if n < 30:
        verdict = "WAIT — collect at least 30 runs before assessing"
        detail  = f"  You have {n} runs. Run `python loop.py --runs {50 - n}` to continue."
        color   = "?"
    elif da > 0.60 and ae < 0.30:
        verdict = "PASS — proceed to Phase 2 (grounding validation)"
        detail  = (
            "  The prediction signal is non-random and error is below threshold.\n"
            "  Next: A/B test whether injecting beliefs actually changes LLM behavior."
        )
        color   = "✓"
    elif da > 0.55 and ae < 0.35:
        verdict = "MARGINAL — tune the prediction prompt, then collect more data"
        detail  = (
            "  The signal exists but is weak. Try rephrasing the prediction system prompt\n"
            "  to encourage more honest confidence estimates before proceeding."
        )
        color   = "~"
    else:
        verdict = "FAIL — prediction is near-random, redesign required"
        detail  = (
            "  The LLM is not producing calibrated predictions for this domain.\n"
            "  Options: simplify the task domain, improve the prediction prompt,\n"
            "  or switch to a harder-to-game success metric."
        )
        color   = "✗"

    lines = [
        THICK_DIV,
        f"  GATE 1 ASSESSMENT  [{color}]",
        THICK_DIV,
        f"  Directional accuracy : {da:.1%}  (threshold: > 60%)",
        f"  Avg prediction error : {ae:.3f}  (threshold: < 0.30)",
        f"  Verdict  : {verdict}",
        "",
        detail,
        "",
        THICK_DIV,
        "",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_analysis(export: bool = False):
    if not DB_PATH.exists():
        print("No database found. Run `python loop.py` first.")
        return

    logs  = get_all_logs()
    stats = get_stats()

    if not logs:
        print("No data yet. Run `python loop.py` first.")
        return

    sections = [
        summary(logs, stats),
        calibration(logs),
        task_breakdown(logs),
        error_trend(logs),
        overconfidence_audit(logs),
        gate1_assessment(stats),
    ]

    report = "\n".join(sections)
    print(report)

    if export:
        out = Path("report.txt")
        out.write_text(report)
        print(f"Report saved to {out.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 analysis report")
    parser.add_argument("--export", action="store_true", help="Save report to report.txt")
    args = parser.parse_args()
    run_analysis(export=args.export)
