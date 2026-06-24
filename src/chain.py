import json
from src.llm import call
from src.profile import profile_summary, update_profile
from src.eval import score_accuracy
from src.prompts import (
    SUMMARY_SYSTEM, SUMMARY_USER,
    ACTION_ITEMS_SYSTEM, ACTION_ITEMS_USER,
    FLAGS_SYSTEM, FLAGS_USER,
    EMAIL_SYSTEM, EMAIL_USER,
    PROFILE_EXTRACT_SYSTEM, PROFILE_EXTRACT_USER,
)


def run_chain(client_id: str, notes: str) -> dict:
    """Run the full prompt chain on meeting notes. Returns all outputs + profile updates."""
    profile = profile_summary(client_id)

    summary = call(
        prompt=SUMMARY_USER.format(notes=notes, profile=profile),
        system=SUMMARY_SYSTEM,
    )

    action_items = call(
        prompt=ACTION_ITEMS_USER.format(notes=notes),
        system=ACTION_ITEMS_SYSTEM,
    )

    flags = call(
        prompt=FLAGS_USER.format(notes=notes, profile=profile),
        system=FLAGS_SYSTEM,
    )

    email = call(
        prompt=EMAIL_USER.format(notes=notes, summary=summary, action_items=action_items),
        system=EMAIL_SYSTEM,
    )

    # Extract new profile facts and persist them
    raw = call(
        prompt=PROFILE_EXTRACT_USER.format(notes=notes, profile=profile),
        system=PROFILE_EXTRACT_SYSTEM,
    )
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        new_facts = json.loads(cleaned)
    except json.JSONDecodeError:
        new_facts = {}

    if new_facts:
        update_profile(client_id, new_facts)

    # Production eval: score the summary's faithfulness to the notes (LLM-as-judge)
    accuracy = score_accuracy(notes, summary)

    return {
        "summary": summary,
        "action_items": action_items,
        "flags": flags,
        "email": email,
        "new_profile_facts": new_facts,
        "accuracy": accuracy,
    }
