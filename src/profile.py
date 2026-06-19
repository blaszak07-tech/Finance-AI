from src.storage import load_profile, save_profile


def get_profile(client_id: str) -> dict:
    return load_profile(client_id)


def update_profile(client_id: str, new_facts: dict) -> dict:
    profile = load_profile(client_id)
    profile.update(new_facts)
    save_profile(client_id, profile)
    return profile


def profile_summary(client_id: str) -> str:
    """Return a plain-text summary of the profile to inject into prompts."""
    profile = load_profile(client_id)
    if not profile:
        return "No prior profile on file for this client."
    lines = [f"- {k}: {v}" for k, v in profile.items()]
    return "Known facts about this client:\n" + "\n".join(lines)
