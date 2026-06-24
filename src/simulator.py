import random
from src.llm import call

# Coherent ready-made personas for the "random" button. Each one's situation,
# concerns, age, risk, and personality fit together so the simulation stays realistic.
# Risk/personality strings must match the UI selectbox options exactly.
RANDOM_PERSONAS = [
    {
        "age": 38, "risk": "Aggressive", "personality": "Decisive and confident",
        "situation": "Tech sales director, dual income with spouse, combined ~$450k/yr. Two young kids. Recently started maxing out the 401k.",
        "concerns": "Wants to retire early around 50, unsure how to split between taxable and retirement accounts, curious about real estate as an investment.",
    },
    {
        "age": 59, "risk": "Conservative", "personality": "Anxious and risk-averse",
        "situation": "Manufacturing manager, single income, ~$1.1M in a 401k and a small pension. Wife handles the household.",
        "concerns": "Nervous about retiring in 3 years, worried a market drop could wipe out the timeline, doesn't understand how to turn savings into income.",
    },
    {
        "age": 47, "risk": "Moderate", "personality": "Analytical and detail-oriented",
        "situation": "Owns a successful dental practice, ~$2M net worth mostly tied up in the business and real estate. Three kids, oldest starts college next year.",
        "concerns": "Heavy concentration in the practice, wants to diversify, juggling college funding and a possible practice sale in 10 years.",
    },
    {
        "age": 34, "risk": "Aggressive", "personality": "Cooperative and trusting",
        "situation": "Software engineer at a mid-size company, single, ~$280k salary plus RSUs. First time working with an advisor.",
        "concerns": "Sitting on a lot of company stock, not sure how aggressive to be, wants to eventually buy a home in a high cost-of-living area.",
    },
    {
        "age": 62, "risk": "Moderate", "personality": "Skeptical and cautious",
        "situation": "Recently widowed, inherited a ~$1.5M portfolio she didn't manage before. Former teacher with a modest pension.",
        "concerns": "Overwhelmed managing money alone for the first time, distrustful after a bad experience with a previous advisor, wants simplicity and safety.",
    },
    {
        "age": 51, "risk": "Moderate", "personality": "Decisive and confident",
        "situation": "Corporate executive, recently divorced, restarting financially with ~$900k after the settlement. Two teenagers, shared custody.",
        "concerns": "Rebuilding a retirement plan from a new baseline, wants to catch up aggressively but protect the kids' college money.",
    },
    {
        "age": 29, "risk": "Aggressive", "personality": "Cooperative and trusting",
        "situation": "Young physician finishing residency, ~$300k in student loans, salary jumping to ~$240k. Just married.",
        "concerns": "Drowning in student debt, doesn't know whether to pay it down or invest, wants to start building wealth but feels behind.",
    },
    {
        "age": 55, "risk": "Conservative", "personality": "Anxious and risk-averse",
        "situation": "Sandwich generation — supporting aging parents and a kid still in college. ~$700k saved, single income of $160k.",
        "concerns": "Stretched thin caring for parents and child at once, worried she'll never catch up for her own retirement, possible long-term-care costs for parents.",
    },
]


def random_persona() -> dict:
    return random.choice(RANDOM_PERSONAS)

_TRANSCRIPT_RULES = """This is a transcript of spoken words only. Critical rules:
- Output ONLY what the person says out loud. Nothing else.
- NO stage directions, NO actions, NO narration. Never write things like *leans back*, *nods*, *shakes hands*, *pauses*. A transcript can't capture those.
- Don't be polished or essay-like. Real people use contractions, filler ("yeah", "I mean", "honestly"), and sometimes trail off or change direction mid-thought.
- Keep it short — usually 2-4 sentences. People don't monologue in conversation.
- Never break character or mention being an AI."""

CLIENT_SYSTEM = f"""You are a wealth management client talking with your financial advisor.
{_TRANSCRIPT_RULES}"""

ADVISOR_SYSTEM = f"""You are an experienced wealth management advisor talking with a client.
Ask natural follow-up questions and give brief guidance. Don't lecture.
{_TRANSCRIPT_RULES}"""

CLIENT_OPENING = """You are {name}, {age} years old. Here is your situation:
{situation}

Your risk tolerance is {risk_tolerance} and your personality is {personality}.
Your main concerns going into this meeting: {concerns}

Start the conversation by greeting your advisor and briefly explaining why you're here today."""

ADVISOR_TURN = """The conversation so far:
{transcript}

Respond as the advisor. Ask a follow-up question or address what the client just said."""

CLIENT_TURN = """The conversation so far:
{transcript}

Your persona: {name}, {age}, {situation}. Personality: {personality}. Concerns: {concerns}

Respond as the client."""

CLIENT_CLOSE = """The conversation so far:
{transcript}

Your persona: {name}, {age}. Concerns: {concerns}

This is your final message. Wrap up naturally — thank the advisor and confirm next steps."""

ADVISOR_CLOSE = """The conversation so far:
{transcript}

This is your final message as the advisor. Summarize what was discussed, confirm action items, and close the meeting warmly."""

ADVISOR_OPENING = """You're beginning a meeting with a client. Greet them warmly and ask one open-ended question about what they'd like to focus on today. Keep it to 1-2 sentences."""


def run_simulation(
    name: str,
    age: int,
    situation: str,
    risk_tolerance: str,
    personality: str,
    concerns: str,
    num_exchanges: int = 4,
) -> str:
    """
    Run a simulated advisor-client conversation and return the full transcript as plain text.
    num_exchanges = number of back-and-forth pairs (client + advisor = 1 exchange).
    """
    transcript_lines = []

    # Client opens
    opening = call(
        prompt=CLIENT_OPENING.format(
            name=name, age=age, situation=situation,
            risk_tolerance=risk_tolerance, personality=personality, concerns=concerns,
        ),
        system=CLIENT_SYSTEM,
    )
    transcript_lines.append(f"Client: {opening.strip()}")

    # Alternating turns
    for i in range(num_exchanges):
        transcript_so_far = "\n\n".join(transcript_lines)
        is_last = (i == num_exchanges - 1)

        # Advisor turn
        if is_last:
            advisor_msg = call(
                prompt=ADVISOR_CLOSE.format(transcript=transcript_so_far),
                system=ADVISOR_SYSTEM,
            )
        else:
            advisor_msg = call(
                prompt=ADVISOR_TURN.format(transcript=transcript_so_far),
                system=ADVISOR_SYSTEM,
            )
        transcript_lines.append(f"Advisor: {advisor_msg.strip()}")

        if not is_last:
            transcript_so_far = "\n\n".join(transcript_lines)
            client_msg = call(
                prompt=CLIENT_TURN.format(
                    transcript=transcript_so_far, name=name, age=age,
                    situation=situation, personality=personality, concerns=concerns,
                ),
                system=CLIENT_SYSTEM,
            )
            transcript_lines.append(f"Client: {client_msg.strip()}")

    # Client closing line
    transcript_so_far = "\n\n".join(transcript_lines)
    closing = call(
        prompt=CLIENT_CLOSE.format(
            transcript=transcript_so_far, name=name, age=age, concerns=concerns,
        ),
        system=CLIENT_SYSTEM,
    )
    transcript_lines.append(f"Client: {closing.strip()}")

    return "\n\n".join(transcript_lines)


# ── Interactive (human-in-the-loop) helpers ──────────────────────────
# The human plays one side; the AI plays the other, one message at a time.

def ai_opening_line(ai_role: str, persona: dict | None = None) -> str:
    """First line spoken by the AI (used when the AI is the advisor and opens the meeting,
    or the AI is the client and states why they're here)."""
    if ai_role == "Client":
        return call(prompt=CLIENT_OPENING.format(**persona), system=CLIENT_SYSTEM).strip()
    return call(prompt=ADVISOR_OPENING, system=ADVISOR_SYSTEM).strip()


def ai_reply(ai_role: str, transcript: str, persona: dict | None = None) -> str:
    """Generate the AI's next message given the conversation so far.
    persona is required only when the AI plays the client."""
    if ai_role == "Client":
        return call(
            prompt=CLIENT_TURN.format(transcript=transcript, **persona),
            system=CLIENT_SYSTEM,
        ).strip()
    return call(
        prompt=ADVISOR_TURN.format(transcript=transcript),
        system=ADVISOR_SYSTEM,
    ).strip()
