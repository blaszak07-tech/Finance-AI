"""Client quick look — a scannable, AI-generated briefing on a client.

Synthesizes the flat profile facts, the structured financials, and recent meeting summaries into a
short, sectioned briefing (bullets, not a wall of text) an advisor can skim before a meeting.
"""

import json
from src.llm import call
from src.storage import load_profile, load_financials, load_meetings

QUICKLOOK_SYSTEM = """You are preparing a concise "quick look" briefing on a wealth management client for
their advisor to skim before a meeting. Write it SCANNABLE — short bold section labels, each followed by
bullet points. Never one long paragraph.

Cover, only where the data supports it:
- **Situation** — who they are: age, family, work, life stage
- **Assets & finances** — list each account / asset / liability as its own bullet, with figures
- **Income**
- **Goals** — objectives and time horizon
- **Watch for** — concerns, risk posture, tensions, or anything to keep in mind

Only state what the provided data supports — never invent figures or facts. Keep bullets short. Use
markdown: a bold label per section and "-" bullets. No preamble; start with the first section."""

QUICKLOOK_USER = """Known profile facts:
{profile}

Structured financials:
{financials}

Recent meeting summaries:
{summaries}

Write the client quick look."""


def client_quicklook(client_id: str) -> str:
    profile = load_profile(client_id)
    financials = load_financials(client_id)
    meetings = load_meetings(client_id)
    summaries = "\n\n".join(f"[{m['_timestamp']}] {m.get('summary', '')}" for m in meetings[:6])

    if not profile and not financials and not summaries.strip():
        return "_Not enough on file yet. Add a meeting to build this client's picture._"

    return call(
        prompt=QUICKLOOK_USER.format(
            profile=json.dumps(profile) if profile else "(none)",
            financials=json.dumps(financials) if financials else "(none)",
            summaries=summaries or "(none)",
        ),
        system=QUICKLOOK_SYSTEM,
    )
