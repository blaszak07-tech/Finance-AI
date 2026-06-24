"""Evaluation — measuring whether the pipeline's output is actually trustworthy.

Core idea: LLM-as-judge. A separate Claude call grades a generated summary against the
ORIGINAL transcript for faithfulness — does every claim hold up, and is anything important
missing? This turns "looks fine" into a number you can track.

- `score_accuracy(transcript, summary)` is the PRODUCTION piece: returns an accuracy score
  (0-100) + the specific hallucinations/omissions found. It's wired into the pipeline so every
  saved meeting carries an accuracy score.
- `run_eval` + `SAMPLE_TRANSCRIPTS` back the educational Eval tab so the mechanism is visible.
"""

import json
from src.llm import call
from src.prompts import SUMMARY_SYSTEM, SUMMARY_USER

JUDGE_SYSTEM = """You are a strict evaluator of AI-generated wealth-management meeting summaries.
Given the ORIGINAL transcript and a GENERATED summary, judge how accurate and faithful the summary is.
Return ONLY a JSON object (no markdown, no code fences):
{"accuracy": <integer 0-100>, "hallucinations": ["..."], "omissions": ["..."], "reasoning": "1-2 sentences"}
Definitions:
- accuracy 100 = every claim in the summary is supported by the transcript AND no important fact is missing.
- hallucinations = statements in the summary NOT supported by the transcript (invented facts).
- omissions = important facts present in the transcript but missing from the summary.
Be strict but fair; minor wording differences are not errors."""

JUDGE_USER = """ORIGINAL TRANSCRIPT:
{transcript}

GENERATED SUMMARY:
{summary}

Score the summary's accuracy against the transcript. Return JSON only."""


def score_accuracy(transcript: str, summary: str) -> dict:
    """LLM-as-judge accuracy score. Returns {accuracy, hallucinations, omissions, reasoning}."""
    raw = call(prompt=JUDGE_USER.format(transcript=transcript, summary=summary), system=JUDGE_SYSTEM)
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        return {"accuracy": None, "hallucinations": [], "omissions": [], "reasoning": "(could not parse judge output)"}
    # normalize
    return {
        "accuracy": data.get("accuracy"),
        "hallucinations": data.get("hallucinations", []) or [],
        "omissions": data.get("omissions", []) or [],
        "reasoning": data.get("reasoning", ""),
    }


def _generate_summary(transcript: str) -> str:
    """Generate a summary the same way the pipeline does (used by the educational eval)."""
    return call(
        prompt=SUMMARY_USER.format(notes=transcript, profile="(evaluation — no profile context)"),
        system=SUMMARY_SYSTEM,
    )


def run_eval(transcript: str, runs: int = 1) -> dict:
    """Educational eval: generate a summary (optionally several times to show consistency) and
    score each against the transcript. Returns the summaries + scores."""
    results = []
    for _ in range(max(1, runs)):
        summary = _generate_summary(transcript)
        results.append({"summary": summary, "score": score_accuracy(transcript, summary)})
    return {"transcript": transcript, "results": results}


SAMPLE_TRANSCRIPTS = {
    "Retirement & college (clean notes)": (
        "Met with John Smith, 52. Wants to retire at 60. Worried about market volatility after recent "
        "news. Daughter starting college in 2 years, about $50k/year. Asked about a Roth conversion — "
        "currently high tax bracket, expects lower in retirement. Received a $200k inheritance last month. "
        "Wants to revisit bond allocation, possibly increase it."
    ),
    "Liquidity event (transcript style)": (
        "Advisor: Congrats on the sale — walk me through where things stand.\n\n"
        "Client: We closed about six weeks ago, roughly four million after tax sitting in a money market. "
        "I want to retire by 58 and I'm worried about the tax hit.\n\n"
        "Advisor: Any other retirement accounts?\n\n"
        "Client: An old 401k with about 180k. My wife still works, makes around 350k, and we max her SEP-IRA. "
        "House is paid off, kids are through college."
    ),
}
