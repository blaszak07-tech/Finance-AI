import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "clients"


def _client_dir(client_id: str) -> Path:
    path = DATA_DIR / client_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meetings_dir(client_id: str) -> Path:
    path = _client_dir(client_id) / "meetings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_meeting(client_id: str, meeting: dict) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = _meetings_dir(client_id) / f"{timestamp}.json"
    filepath.write_text(json.dumps(meeting, indent=2))
    return filepath


def _pretty_timestamp(stem: str) -> str:
    try:
        return datetime.strptime(stem, "%Y%m%d_%H%M%S").strftime("%B %d, %Y — %I:%M %p")
    except ValueError:
        return stem


def load_meetings(client_id: str) -> list[dict]:
    meetings_dir = _meetings_dir(client_id)
    files = sorted(meetings_dir.glob("*.json"), reverse=True)  # newest first
    meetings = []
    for f in files:
        data = json.loads(f.read_text())
        data["id"] = f.stem
        data["_timestamp"] = _pretty_timestamp(f.stem)
        meetings.append(data)
    return meetings


def load_meeting(client_id: str, meeting_id: str) -> dict | None:
    filepath = _meetings_dir(client_id) / f"{meeting_id}.json"
    if not filepath.exists():
        return None
    data = json.loads(filepath.read_text())
    data["id"] = meeting_id
    data["_timestamp"] = _pretty_timestamp(meeting_id)
    return data


def save_profile(client_id: str, profile: dict) -> None:
    filepath = _client_dir(client_id) / "profile.json"
    filepath.write_text(json.dumps(profile, indent=2))


def load_profile(client_id: str) -> dict:
    filepath = _client_dir(client_id) / "profile.json"
    if not filepath.exists():
        return {}
    return json.loads(filepath.read_text())


def save_financials(client_id: str, financials: dict) -> None:
    filepath = _client_dir(client_id) / "financials.json"
    filepath.write_text(json.dumps(financials, indent=2))


def load_financials(client_id: str) -> dict:
    filepath = _client_dir(client_id) / "financials.json"
    if not filepath.exists():
        return {}
    return json.loads(filepath.read_text())


def list_clients() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return [d.name for d in DATA_DIR.iterdir() if d.is_dir()]


def _id_from_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def create_client(name: str) -> str:
    """Create a client (name only). Persists a display name in meta.json."""
    name = name.strip()
    if not name:
        raise ValueError("Client name is required.")
    client_id = _id_from_name(name)
    path = DATA_DIR / client_id
    if path.exists():
        raise ValueError(f"A client named '{name}' already exists.")
    path.mkdir(parents=True, exist_ok=True)
    (path / "meta.json").write_text(json.dumps({
        "name": name,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=2))
    return client_id


def client_name(client_id: str) -> str:
    """Display name for a client — from meta.json, falling back to a title-cased id."""
    meta = DATA_DIR / client_id / "meta.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text()).get("name") or client_id.replace("_", " ").title()
        except json.JSONDecodeError:
            pass
    return client_id.replace("_", " ").title()


def rename_client(old_id: str, new_name: str) -> str:
    new_name = new_name.strip()
    new_id = _id_from_name(new_name)
    old_path = DATA_DIR / old_id
    new_path = DATA_DIR / new_id
    if new_id != old_id and new_path.exists():
        raise ValueError(f"A client named '{new_name}' already exists.")
    if new_id != old_id:
        old_path.rename(new_path)
    (new_path / "meta.json").write_text(json.dumps({"name": new_name}, indent=2))
    return new_id


def delete_client(client_id: str) -> None:
    import shutil
    path = DATA_DIR / client_id
    if path.exists():
        shutil.rmtree(path)
