"""
llm.py — Two LLM calls: predict_confidence() and generate_fix().
Uses Anthropic Claude. Set ANTHROPIC_API_KEY in your environment.
"""

import os
import json
import re
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"

# ── System Prompts ────────────────────────────────────────────────────────────

PREDICTION_SYSTEM = """You are a code analysis expert. Your only job is to predict
whether you can successfully fix a broken Python function in one attempt.

Analyze the broken function and failing test carefully. Be honest — overconfidence
is a worse error than underconfidence for this experiment.

Return ONLY valid JSON with exactly this structure (no markdown, no explanation):
{
  "confidence": <float 0.0–1.0>,
  "reasoning": "<one sentence, max 100 chars>",
  "error_type": "<one of: off_by_one | logic_error | wrong_method | operator_error | missing_edge_case | type_error | syntax_error | other>",
  "complexity": "<one of: low | medium | high>"
}"""

FIX_SYSTEM = """You are a Python debugging expert. Fix the broken function so all tests pass.

Rules (strictly follow all of them):
- Return ONLY the fixed Python function code
- No explanations, no markdown, no backticks, no code fences
- Keep the exact same function name and signature
- Make the minimal change needed to fix the bug"""


# ── Core Functions ────────────────────────────────────────────────────────────

def predict_confidence(broken_function: str, test_code: str) -> dict:
    """
    Ask the LLM: how confident are you that you can fix this?

    Returns:
        dict with keys: confidence (float), reasoning, error_type, complexity
    """
    prompt = (
        f"Broken function:\n```python\n{broken_function}\n```\n\n"
        f"Test that must pass:\n```python\n{test_code}\n```\n\n"
        "Predict your confidence of fixing this correctly in one attempt. "
        "Return only JSON."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=PREDICTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Strip accidental markdown fences
    raw = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("`")

    try:
        result = json.loads(raw)
        result["confidence"] = float(max(0.0, min(1.0, result.get("confidence", 0.5))))
        return result
    except (json.JSONDecodeError, ValueError, KeyError):
        # Graceful fallback: try regex extraction
        match = re.search(r'"confidence"\s*:\s*([\d.]+)', raw)
        confidence = float(match.group(1)) if match else 0.5
        return {
            "confidence":  confidence,
            "reasoning":   raw[:120],
            "error_type":  "other",
            "complexity":  "medium",
        }


def generate_fix(broken_function: str, test_code: str) -> str:
    """
    Ask the LLM to fix the broken function.

    Returns:
        str — the fixed function code (no markdown, just Python)
    """
    prompt = (
        f"Broken function:\n{broken_function}\n\n"
        f"Test that must pass:\n{test_code}\n\n"
        "Return only the fixed function."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=FIX_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    fixed = response.content[0].text.strip()

    # Strip markdown code fences if the model added them anyway
    if fixed.startswith("```"):
        lines = fixed.split("\n")
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        fixed = "\n".join(lines[1:end]).strip()

    return fixed
