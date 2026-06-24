"""Orchestrator-workers agents — the V2 "agentic" layer.

Pattern: an ORCHESTRATOR reads a meeting and decides which SPECIALIST analysts are
actually relevant, then only those run. This is the real agentic idea — the model
decides the control flow (which workers fire) instead of a fixed script. It's the
"orchestrator-workers" pattern, one step below a full tool-using agent loop.

The three specialists map to how wealth management planning actually divides.
All calls go through the existing Claude `call` (default Haiku).
"""

import json
from src.llm import call
from src.profile import profile_summary
from src.search import build_index, search_index

SPECIALISTS = {
    "retirement": {
        "label": "Retirement & Income",
        "system": """You are a retirement and income planning specialist on a wealth management team.
Focus ONLY on your domain: retirement timeline and feasibility, income replacement, withdrawal/drawdown
strategy, savings adequacy, Social Security / pension timing, and longevity risk. Ignore tax and
portfolio-construction issues unless they directly affect retirement readiness.""",
        "retrieval_query": "retirement timeline, retirement age, income drawdown, withdrawals, savings adequacy, pension, social security, longevity",
    },
    "tax": {
        "label": "Tax Planning",
        "system": """You are a tax planning specialist on a wealth management team.
Focus ONLY on your domain: tax brackets, Roth conversions, tax-loss harvesting, account-type tax
efficiency, and tax-sensitive events (inheritance, liquidity events, RSU vesting, large gains).
Ignore retirement-timeline and portfolio-risk issues unless they are tax-relevant.""",
        "retrieval_query": "taxes, tax bracket, Roth conversion, capital gains, RSU vesting, inheritance, tax-loss harvesting, deductions",
    },
    "risk": {
        "label": "Risk & Portfolio",
        "system": """You are a risk and portfolio specialist on a wealth management team.
Focus ONLY on your domain: asset allocation, concentration risk, diversification, risk-tolerance
signals and mismatches, market-volatility concerns, and rebalancing. Ignore tax and retirement-income
issues unless they directly affect portfolio construction.""",
        "retrieval_query": "asset allocation, portfolio risk, concentration, diversification, market volatility, risk tolerance, rebalancing",
    },
}

ORCHESTRATOR_SYSTEM = """You are the orchestrator of a wealth management analyst team. Given meeting
notes, decide which specialist analysts should review them. Available specialists:
- retirement: retirement timeline, income/drawdown planning, savings adequacy
- tax: tax brackets, Roth conversions, tax-sensitive events, account efficiency
- risk: asset allocation, concentration, risk-tolerance signals, volatility

Select ONLY the specialists genuinely relevant to these notes (one or more — not all by default).
Return ONLY a JSON object, no markdown or code fences:
{"specialists": ["retirement", "tax"], "reasoning": "one short sentence"}"""

ORCHESTRATOR_USER = """Meeting notes:
{notes}

Client profile context:
{profile}

Which specialists should review this? Return JSON only."""

SPECIALIST_USER = """Current meeting notes:
{notes}

Client profile context:
{profile}

Relevant excerpts from this client's PAST meetings (may be empty):
{history}

As the {label} specialist, identify the planning flags and considerations in YOUR domain only.
Focus on the current meeting, but use the past excerpts where they add insight or show a change over
time — cite the meeting date when you reference one. Format as a short numbered list, each with a brief
explanation. If nothing in your domain applies, reply exactly: "Nothing flagged in this area." """


def _format_history(hits: list[dict]) -> str:
    if not hits:
        return "(no relevant prior history found)"
    return "\n\n".join(f"[{h['timestamp']}] {h['text']}" for h in hits)


def _route(notes: str, profile: str) -> tuple[list[str], str]:
    """Orchestrator step: decide which specialists run. Falls back to all on parse failure."""
    raw = call(prompt=ORCHESTRATOR_USER.format(notes=notes, profile=profile), system=ORCHESTRATOR_SYSTEM)
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        decision = json.loads(cleaned)
        selected = [s for s in decision.get("specialists", []) if s in SPECIALISTS]
        reasoning = decision.get("reasoning", "").strip()
    except (json.JSONDecodeError, AttributeError):
        selected, reasoning = [], "(couldn't parse routing — ran all specialists)"
    if not selected:
        selected = list(SPECIALISTS.keys())
        reasoning = reasoning or "(no clear routing — ran all specialists)"
    return selected, reasoning


def run_analysis(client_id: str, notes: str, index: tuple | None = None) -> dict:
    """Route to the relevant specialists and collect their findings. Each specialist also
    retrieves domain-relevant passages from the client's PAST meetings (RAG). Pass a prebuilt
    `index` (chunks, embeddings) to reuse a cached one; otherwise it's built here."""
    profile = profile_summary(client_id)
    chunks, embeddings = index if index is not None else build_index(client_id)
    selected, reasoning = _route(notes, profile)

    findings = []
    for key in selected:
        spec = SPECIALISTS[key]
        hits = []
        if len(chunks):
            query = f"{spec['retrieval_query']}. {notes}"
            hits = search_index(chunks, embeddings, query, top_k=3)
        out = call(
            prompt=SPECIALIST_USER.format(
                notes=notes, profile=profile, history=_format_history(hits), label=spec["label"],
            ),
            system=spec["system"],
        )
        findings.append({"key": key, "label": spec["label"], "text": out, "sources": hits})

    return {
        "reasoning": reasoning,
        "selected": selected,
        "findings": findings,
        "available": {k: v["label"] for k, v in SPECIALISTS.items()},
    }
