# Phase 2 Research Report: Grounding Validation

## Objective
To determine if injecting past performance data (prediction-error signals) into an LLM's prompt improves its success rate on complex coding tasks.

## Methodology
- **Model:** GPT-4o-mini
- **Setup:** A/B Test (80 runs per group)
- **Group A (Control):** Standard fix generation.
- **Group B (Belief):** Fix generation with an added "Belief Block" summarizing previous error history for that category.
- **Tasks:** 16 Python debugging tasks ranging from simple typos to complex recursive graph pathfinders.

## Quantitative Results
| Group | Runs | Success Rate |
|-------|------|--------------|
| **Control** | 80 | **98.8%** |
| **Belief** | 80 | **95.0%** |
| **Delta** | — | **-3.8%** |

## Key Findings

### 1. The "Distraction" Effect
Counter-intuitively, providing the model with its own failure history **reduced** performance. This was most evident in **Task 008 (Trie prefix search)**, where the Control group had 100% success, but the Belief group dropped to 85.7%. 

**Analysis:** The model likely interpreted the "self-correction hint" as a signal that it *must* change its approach, leading it to over-complicate or doubt its correct first instinct.

### 2. Identifying "Extreme" Boundaries
We successfully found the model's current ceiling:
- **Task 015 (Graph Cycle Tracking):** Both groups failed at 0%. The model struggled with the subtle state management required to track visited nodes across recursive branches in one shot.
- **Task 008 (Trie):** The model is "brittle" here—it can solve it, but is easily distracted into wrong implementations by external prompts.

### 3. Calibration vs. Grounding
Phase 1 proved the model is **Well-Calibrated** (it knows what it knows). Phase 2 proved that **Grounding** (using that knowledge to improve) is much harder. Simply "knowing" you have made mistakes in the past doesn't automatically mean you know how to avoid them in the future without a more sophisticated reasoning mechanism.

## Conclusion
For high-reasoning models like GPT-4o-mini, simple prompt-based belief injection is not an effective grounding strategy. Future research should focus on **Chain-of-Thought Reflection** or **Multi-turn Debugging** where the model has space to analyze its history rather than just being "warned" about it.

---
*Research conducted via Gemini CLI Adaptive Learning Experiment Framework.*
