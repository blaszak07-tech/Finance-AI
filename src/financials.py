"""Structured financial extraction — pull the client's finances into typed fields, not prose.

The flat profile (`profile.py`) stores loose facts. This stores a real financial SNAPSHOT with a fixed
schema: accounts, other assets, liabilities, income, goals, risk tolerance — with balances as numbers so
we can compute net worth. Each meeting updates it: rather than fuzzy code-merging (is "401k" == "401(k)"?),
we hand the existing snapshot + new notes to Claude and get back the reconciled full snapshot (LLM-as-merger).
"""

import json
from src.llm import call
from src.storage import load_financials, save_financials

SCHEMA_HINT = """{
  "accounts": [{"name": "401(k)", "type": "retirement|brokerage|cash|other", "balance": 1200000}],
  "other_assets": [{"name": "primary home", "value": 800000}],
  "liabilities": [{"name": "mortgage", "balance": 0}],
  "income": [{"source": "salary", "annual": 320000}],
  "goals": [{"goal": "retire", "target": "age 55", "notes": "..."}],
  "risk_tolerance": "conservative|moderate|aggressive or a short phrase"
}"""

FIN_SYSTEM = f"""You maintain a structured financial snapshot for a wealth management client.
You are given the EXISTING snapshot (JSON) and NEW meeting notes. Return the UPDATED, COMPLETE snapshot as
a single JSON object in exactly this shape (omit a section only if there's truly nothing for it):

{SCHEMA_HINT}

Rules:
- Merge new information into the existing snapshot: update figures that changed, add new items, keep still-valid
  ones. Reconcile duplicates (same account named slightly differently = one entry).
- Balances/values/income are NUMBERS (no "$" or commas). Convert "800k" -> 800000, "1.2M" -> 1200000.
- Only include facts supported by the notes or existing snapshot — never invent figures.
- Return ONLY the JSON object. No markdown, no code fences, no commentary."""

FIN_USER = """EXISTING SNAPSHOT:
{existing}

NEW MEETING NOTES:
{notes}

Return the updated complete snapshot as JSON."""


def _extract_json(raw: str) -> dict | None:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None


def update_financials(client_id: str, notes: str) -> dict:
    """Extract/merge structured financials from a meeting's notes and persist the snapshot."""
    existing = load_financials(client_id)
    raw = call(
        prompt=FIN_USER.format(existing=json.dumps(existing) or "{}", notes=notes),
        system=FIN_SYSTEM,
    )
    snapshot = _extract_json(raw)
    if snapshot is None:
        return existing  # keep prior snapshot on parse failure
    save_financials(client_id, snapshot)
    return snapshot


def net_worth(financials: dict) -> float:
    accounts = sum(_num(a.get("balance")) for a in financials.get("accounts", []))
    assets = sum(_num(a.get("value")) for a in financials.get("other_assets", []))
    liabilities = sum(_num(l.get("balance")) for l in financials.get("liabilities", []))
    return accounts + assets - liabilities


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
