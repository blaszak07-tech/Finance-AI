"""FastAPI backend for the wealth-management assistant web app.

Thin HTTP layer over the existing `src/` AI code — no business logic here, it just wraps
the functions the Streamlit app already used. The React frontend in `web/` calls these.

Run:  python3 -m uvicorn api.server:app --reload --port 8000
"""

import sys
import os
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import storage
from src.profile import profile_summary
from src.financials import net_worth
from src.chain import run_chain
from src.search import build_index, search_index
from src.agents import run_panel
from src.tool_agent import run_agent
from src.simulator import simulate_conversation
from src.overview import client_quicklook

app = FastAPI(title="WM Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run blocking AI work off the event loop
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)


async def _run(fn, *args):
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(_pool, fn, *args)


# ── Models ───────────────────────────────────────────────────
class NewClient(BaseModel):
    name: str


class RenameClient(BaseModel):
    name: str


class NewMeeting(BaseModel):
    notes: str


class AskBody(BaseModel):
    question: str


class SimulateBody(BaseModel):
    age: int = 50
    situation: str
    concerns: str
    risk_tolerance: str = "moderate"
    personality: str = "cooperative and trusting"
    num_exchanges: int = 3
    save: bool = True


# ── Helpers ──────────────────────────────────────────────────
def _client_summary(client_id: str) -> dict:
    meetings = storage.load_meetings(client_id)
    fin = storage.load_financials(client_id)
    return {
        "id": client_id,
        "name": storage.client_name(client_id),
        "meetingCount": len(meetings),
        "lastMeeting": meetings[0]["_timestamp"] if meetings else None,
        "netWorth": net_worth(fin) if fin else None,
    }


def _meeting_brief(m: dict) -> dict:
    return {"id": m["id"], "timestamp": m["_timestamp"], "summary": m.get("summary", "")}


# ── Clients ──────────────────────────────────────────────────
@app.get("/api/clients")
def get_clients():
    return [_client_summary(c) for c in storage.list_clients()]


@app.post("/api/clients")
def create_client(body: NewClient):
    try:
        client_id = storage.create_client(body.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _client_summary(client_id)


@app.get("/api/clients/{client_id}")
def get_client(client_id: str):
    if client_id not in storage.list_clients():
        raise HTTPException(status_code=404, detail="Client not found")
    fin = storage.load_financials(client_id)
    return {
        "id": client_id,
        "name": storage.client_name(client_id),
        "profile": storage.load_profile(client_id),
        "financials": fin,
        "netWorth": net_worth(fin) if fin else None,
        "meetings": [_meeting_brief(m) for m in storage.load_meetings(client_id)],
    }


@app.patch("/api/clients/{client_id}")
def patch_client(client_id: str, body: RenameClient):
    try:
        new_id = storage.rename_client(client_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _client_summary(new_id)


@app.delete("/api/clients/{client_id}")
def remove_client(client_id: str):
    storage.delete_client(client_id)
    return {"ok": True}


# ── Meetings ─────────────────────────────────────────────────
@app.get("/api/clients/{client_id}/quicklook")
async def quicklook(client_id: str):
    if client_id not in storage.list_clients():
        raise HTTPException(status_code=404, detail="Client not found")
    return {"markdown": await _run(client_quicklook, client_id)}


@app.get("/api/clients/{client_id}/meetings/{meeting_id}")
def get_meeting(client_id: str, meeting_id: str):
    m = storage.load_meeting(client_id, meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return m


@app.post("/api/clients/{client_id}/meetings")
async def create_meeting(client_id: str, body: NewMeeting):
    if not body.notes.strip():
        raise HTTPException(status_code=400, detail="Notes are required")

    def _work():
        result = run_chain(client_id, body.notes)
        path = storage.save_meeting(client_id, {"notes": body.notes, **result})
        return path.stem, result

    meeting_id, result = await _run(_work)
    return {"id": meeting_id, **result}


@app.post("/api/clients/{client_id}/meetings/{meeting_id}/analyze")
async def analyze_meeting(client_id: str, meeting_id: str):
    m = storage.load_meeting(client_id, meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    result = await _run(run_panel, client_id, m.get("notes", ""))
    return result


# ── Ask (the smart agent) ────────────────────────────────────
@app.post("/api/clients/{client_id}/ask")
async def ask(client_id: str, body: AskBody):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    return await _run(run_agent, client_id, body.question.strip())


# ── Simulate ─────────────────────────────────────────────────
@app.post("/api/clients/{client_id}/simulate")
async def simulate(client_id: str, body: SimulateBody):
    def _work():
        turns = simulate_conversation(
            name=storage.client_name(client_id),
            age=body.age,
            situation=body.situation,
            risk_tolerance=body.risk_tolerance,
            personality=body.personality,
            concerns=body.concerns,
            num_exchanges=body.num_exchanges,
        )
        transcript = "\n\n".join(f"{t['role']}: {t['text']}" for t in turns)
        meeting_id = None
        if body.save:
            result = run_chain(client_id, transcript)
            path = storage.save_meeting(client_id, {"notes": transcript, **result})
            meeting_id = path.stem
        return {"turns": turns, "transcript": transcript, "meetingId": meeting_id}

    return await _run(_work)


@app.get("/api/health")
def health():
    return {"ok": True}
