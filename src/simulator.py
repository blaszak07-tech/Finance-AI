from src.llm import call

CLIENT_SYSTEM = """You are roleplaying as a wealth management client in a meeting with your financial advisor.
Stay in character the entire time. Speak naturally — like a real person, not a formal document.
Keep each response to 3-5 sentences. Don't wrap things up or say goodbye until told to.
Never break character or refer to yourself as an AI."""

ADVISOR_SYSTEM = """You are an experienced, professional wealth management advisor conducting a client meeting.
Ask follow-up questions, surface concerns the client may not have considered, and provide brief guidance.
Keep each response to 3-5 sentences. Be warm but professional.
Never break character or refer to yourself as an AI."""

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
