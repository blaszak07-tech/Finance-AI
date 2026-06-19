from src.llm import call
from src.profile import profile_summary
from src.prompts import (
    SUMMARY_SYSTEM, SUMMARY_USER,
    ACTION_ITEMS_SYSTEM, ACTION_ITEMS_USER,
    FLAGS_SYSTEM, FLAGS_USER,
    EMAIL_SYSTEM, EMAIL_USER,
)


def run_chain(client_id: str, notes: str) -> dict:
    """Run the full 4-step prompt chain on meeting notes. Returns all outputs as a dict."""
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

    return {
        "summary": summary,
        "action_items": action_items,
        "flags": flags,
        "email": email,
    }
