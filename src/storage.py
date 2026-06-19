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


def load_meetings(client_id: str) -> list[dict]:
    meetings_dir = _meetings_dir(client_id)
    files = sorted(meetings_dir.glob("*.json"))
    return [json.loads(f.read_text()) for f in files]


def save_profile(client_id: str, profile: dict) -> None:
    filepath = _client_dir(client_id) / "profile.json"
    filepath.write_text(json.dumps(profile, indent=2))


def load_profile(client_id: str) -> dict:
    filepath = _client_dir(client_id) / "profile.json"
    if not filepath.exists():
        return {}
    return json.loads(filepath.read_text())


def list_clients() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return [d.name for d in DATA_DIR.iterdir() if d.is_dir()]
