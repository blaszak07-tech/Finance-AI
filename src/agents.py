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


# ── Multi-agent panel: specialists cross-review, a lead advisor synthesizes ──

CROSS_REVIEW_USER = """You are the {label} specialist. You already gave your initial findings. Here are the
OTHER specialists' findings on the same client:

{others}

Add cross-domain considerations from YOUR perspective ONLY: where your domain interacts with theirs, conflicts
or dependencies between recommendations (e.g., a tax move that strains liquidity), or a risk they missed that
touches your domain. 2-4 short bullets. If there's genuinely nothing to add, reply exactly: "No cross-domain concerns." """

LEAD_ADVISOR_SYSTEM = """You are the lead wealth management advisor coordinating a team of specialists.
Synthesize their analysis into ONE prioritized action plan for the client. Where specialists conflict
(e.g., tax wants a Roth conversion but liquidity needs argue against it), state the tradeoff explicitly and
make a recommendation. Be concrete and grounded in what the specialists actually found — never invent client
facts. Output a short, prioritized numbered list of recommendations, highest-impact first."""

LEAD_ADVISOR_USER = """Client meeting notes:
{notes}

Specialist findings and cross-review notes:
{panel}

Produce a single prioritized action plan, resolving any conflicts between specialists."""


def _specialist_findings(key, notes, profile, chunks, embeddings):
    spec = SPECIALISTS[key]
    hits = []
    if len(chunks):
        hits = search_index(chunks, embeddings, f"{spec['retrieval_query']}. {notes}", top_k=3)
    text = call(
        prompt=SPECIALIST_USER.format(
            notes=notes, profile=profile, history=_format_history(hits), label=spec["label"],
        ),
        system=spec["system"],
    )
    return {"key": key, "label": spec["label"], "text": text, "sources": hits}


def run_panel(client_id: str, notes: str, index: tuple | None = None) -> dict:
    """Multi-agent panel: (1) each relevant specialist gives initial findings, (2) each then cross-reviews
    the others' findings, (3) a lead advisor synthesizes a unified, conflict-resolved plan."""
    profile = profile_summary(client_id)
    chunks, embeddings = index if index is not None else build_index(client_id)
    selected, reasoning = _route(notes, profile)

    # Round 1 — initial findings
    round1 = [_specialist_findings(key, notes, profile, chunks, embeddings) for key in selected]

    # Round 2 — cross-review (only meaningful with 2+ specialists)
    cross = []
    if len(round1) > 1:
        for item in round1:
            others = "\n\n".join(f"### {o['label']}\n{o['text']}" for o in round1 if o["key"] != item["key"])
            text = call(
                prompt=CROSS_REVIEW_USER.format(label=item["label"], others=others),
                system=SPECIALISTS[item["key"]]["system"],
            )
            cross.append({"key": item["key"], "label": item["label"], "text": text})

    # Synthesis — lead advisor
    panel_text = "".join(f"## {o['label']} — initial\n{o['text']}\n\n" for o in round1)
    panel_text += "".join(f"## {c['label']} — cross-review\n{c['text']}\n\n" for c in cross)
    synthesis = call(
        prompt=LEAD_ADVISOR_USER.format(notes=notes, panel=panel_text),
        system=LEAD_ADVISOR_SYSTEM,
    )

    return {
        "reasoning": reasoning,
        "selected": selected,
        "round1": round1,
        "cross": cross,
        "synthesis": synthesis,
        "available": {k: v["label"] for k, v in SPECIALISTS.items()},
    }
