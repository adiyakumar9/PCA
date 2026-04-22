"""
llm.py — Two LLM calls: predict_confidence() and generate_fix().
Supports Anthropic Claude, Google Gemini, and OpenAI.
Configure using LLM_PROVIDER="anthropic", "gemini", or "openai".
"""

import os
import json
import re

# LLM Provider configuration
PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
ANTHROPIC_MODEL = "claude-sonnet-4-5"
GEMINI_MODEL = "gemini-flash-latest"
OPENAI_MODEL = "gpt-4o-mini"

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

REFLECTION_SYSTEM = """You are a software engineering researcher. Analyze your past error history 
and the current broken code. Write a short (2-3 sentence) strategy on how you will avoid 
your typical mistakes (like off-by-one errors or logic traps) in this specific task.

Be very specific about which lines or conditions you will check twice."""


# ── Client Initialization ─────────────────────────────────────────────────────

def get_completion(system_prompt, user_prompt, max_tokens=800):
    """
    Unified completion interface for Claude, Gemini, and OpenAI.
    """
    if PROVIDER == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text.strip()

    elif PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        is_json = "JSON" in system_prompt
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"} if is_json else None,
            temperature=0.0
        )
        return response.choices[0].message.content.strip()

    elif PROVIDER == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        
        # Use JSON mode if requested by the prompt containing "JSON"
        is_json = "JSON" in system_prompt
        config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.0,
            response_mime_type="application/json" if is_json else "text/plain"
        )
        
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_prompt
        )
        response = model.generate_content(
            user_prompt,
            generation_config=config
        )
        return response.text.strip()

    else:
        raise ValueError(f"Unsupported LLM provider: {PROVIDER}")


# ── Core Functions ────────────────────────────────────────────────────────────

def predict_confidence(broken_function: str, test_code: str) -> dict:
    """
    Ask the LLM: how confident are you that you can fix this?
    """
    prompt = (
        f"Broken function:\n```python\n{broken_function}\n```\n\n"
        f"Test that must pass:\n```python\n{test_code}\n```\n\n"
        "Predict your confidence of fixing this correctly in one attempt. "
        "Return only JSON."
    )

    try:
        raw = get_completion(PREDICTION_SYSTEM, prompt, max_tokens=256)
        
        # Strip accidental markdown fences
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("`")
        
        result = json.loads(raw)
        result["confidence"] = float(max(0.0, min(1.0, result.get("confidence", 0.5))))
        return result
    except (json.JSONDecodeError, ValueError, KeyError, Exception) as exc:
        # Fallback for parsing errors or API failures
        print(f" [LLM Warning] Parsing error: {exc}")
        return {
            "confidence":  0.5,
            "reasoning":   "Fallback confidence due to LLM error or parse failure.",
            "error_type":  "other",
            "complexity":  "medium",
        }


def generate_fix(broken_function: str, test_code: str) -> str:
    """
    Standard fix generation (Control group).
    """
    return _generate_fix_internal(broken_function, test_code, FIX_SYSTEM)


def generate_fix_with_belief(broken_function: str, test_code: str, belief_string: str) -> str:
    """
    Fix generation with injected belief (Belief group).
    """
    system_prompt = FIX_SYSTEM + f"\n\nSELF-CORRECTION HINT: {belief_string}"
    return _generate_fix_internal(broken_function, test_code, system_prompt)


def generate_reflection(broken_function: str, test_code: str, history_string: str) -> str:
    """
    Ask the LLM to reflect on its history and the current task.
    """
    prompt = (
        f"Broken function:\n{broken_function}\n\n"
        f"Test code:\n{test_code}\n\n"
        f"Your History:\n{history_string}\n\n"
        "Explain your specific strategy to avoid repeating these mistakes."
    )
    return get_completion(REFLECTION_SYSTEM, prompt, max_tokens=300)


def generate_fix_with_reflection(broken_function: str, test_code: str, reflection_text: str) -> str:
    """
    Fix generation with the LLM's own reflection injected.
    """
    system_prompt = FIX_SYSTEM + f"\n\nYOUR REFLECTION & PLAN:\n{reflection_text}"
    return _generate_fix_internal(broken_function, test_code, system_prompt)


def _generate_fix_internal(broken_function: str, test_code: str, system_prompt: str) -> str:
    """
    Common logic for fix generation.
    """
    prompt = (
        f"Broken function:\n{broken_function}\n\n"
        f"Test that must pass:\n{test_code}\n\n"
        "Return ONLY the fixed function, no other text."
    )

    fixed = get_completion(system_prompt, prompt, max_tokens=800)

    # Robust cleaning of markdown blocks
    if "```" in fixed:
        # Extract content between first and last triple backticks
        match = re.search(r"```(?:python)?\n?(.*?)\n?```", fixed, re.DOTALL)
        if match:
            fixed = match.group(1).strip()
        else:
            # Fallback: remove lines starting with ```
            lines = [l for l in fixed.split("\n") if not l.strip().startswith("```")]
            fixed = "\n".join(lines).strip()

    return fixed
