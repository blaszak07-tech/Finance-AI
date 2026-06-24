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


def _extract_json(raw: str) -> dict | None:
    """Robustly pull a JSON object out of an LLM response (handles code fences / stray prose)."""
    if not isinstance(raw, str):
        return None
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None

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
    data = _extract_json(raw)
    if data is None:
        return {"accuracy": None, "hallucinations": [], "omissions": [], "reasoning": "(could not parse judge output)"}
    return {
        "accuracy": data.get("accuracy"),
        "hallucinations": data.get("hallucinations", []) or [],
        "omissions": data.get("omissions", []) or [],
        "reasoning": data.get("reasoning", ""),
    }


GROUND_JUDGE_SYSTEM = """You evaluate whether an AI assistant's answer is GROUNDED in the evidence it was
given. You receive the user's QUESTION, the EVIDENCE excerpts the assistant was shown, and the assistant's
ANSWER. Judge how well the answer's factual claims are supported by the evidence.
Return ONLY a JSON object (no markdown, no code fences):
{"groundedness": <integer 0-100>, "unsupported_claims": ["..."], "reasoning": "1-2 sentences"}
Rules:
- groundedness 100 = every client-specific factual claim in the answer is supported by the evidence, nothing invented.
- unsupported_claims = specific claims about the client NOT backed by the evidence (or contradicting it).
- General financial reasoning, advice, and recommendations that follow from the evidence are FINE — do not
  penalize them. Penalize ONLY invented client-specific facts."""

GROUND_JUDGE_USER = """QUESTION:
{question}

EVIDENCE THE ASSISTANT WAS SHOWN:
{evidence}

ASSISTANT'S ANSWER:
{answer}

Score how grounded the answer is in the evidence. Return JSON only."""


def score_groundedness(question: str, evidence: str, answer: str) -> dict:
    """LLM-as-judge groundedness/faithfulness for a question-answering response (Ask / Auto-Agent).
    Returns {groundedness, unsupported_claims, reasoning}."""
    if not evidence.strip():
        return {"groundedness": None, "unsupported_claims": [], "reasoning": "(no evidence to judge against)"}
    raw = call(
        prompt=GROUND_JUDGE_USER.format(question=question, evidence=evidence, answer=answer),
        system=GROUND_JUDGE_SYSTEM,
    )
    data = _extract_json(raw)
    if data is None:
        return {"groundedness": None, "unsupported_claims": [], "reasoning": "(could not parse judge output)"}
    return {
        "groundedness": data.get("groundedness"),
        "unsupported_claims": data.get("unsupported_claims", []) or [],
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
