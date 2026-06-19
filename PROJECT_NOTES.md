# PROJECT_NOTES.md — read this FIRST

> **Purpose of this file:** This is the project's memory. Read it at the start of every
> new Claude Code session to get caught up *without* replaying old chat history (which
> costs credits). When something meaningful changes, this file gets updated. If this file
> and the code ever disagree, trust the code and fix this file.

**Last updated:** 2026-06-17 (plan approved; repo initialized + V1 scaffold created; building next)

---

## What this project is

An **AI Wealth Management Meeting Assistant**. A wealth advisor finishes a client meeting
with messy notes (e.g. *"John wants to retire at 60, worried about market volatility,
daughter starting college in 2 years, asked about Roth conversion"*). This tool turns that
unstructured text into structured, useful output.

**Core V1 workflow — text in → structured output out:**
1. Advisor pastes meeting notes / a transcript (plain text).
2. Text runs through a **prompt chain** (several separate AI calls, each with ONE job):
   - Client summary
   - Action items
   - Portfolio / planning flags (risk-tolerance comments, life events, goal changes)
   - Follow-up email draft
3. The client's **profile** updates with new facts learned this meeting (persists across sessions).
4. Everything is saved locally as **JSON** → a searchable per-client history.
5. Output shown on a simple **Streamlit** web UI (not a terminal app — matters for demoing in interviews).

## Who this is for

Shaun — finance student (heading into sophomore year as of June 2026), targeting wealth
management. This is a multi-year *learning* project: the goal is genuinely understanding
agentic AI / modern AI engineering well enough to speak to it in finance interviews, not
just shipping a working app. Build for depth, explain the "why," don't just hand over code.

## Hard constraints (do not violate without an explicit new decision)

- **Money:** No spend beyond LLM API tokens. No paid tools, no paid tiers. Everything free.
- **Model:** Default to **Claude Haiku 4.5** (`claude-haiku-4-5`, ~$1/$5 per 1M in/out
  tokens) — cheap and good enough for extraction/summarization. The "planning flags" step
  needs real judgment; if Haiku is too shallow there, consider upgrading *only that step*
  to **Claude Sonnet 4.6** (`claude-sonnet-4-6`, ~$3/$15). Evaluate after it's built.
- **Build V1 first. Never build ahead of where Shaun is.** Add later stages one at a time.
- **Wait for Shaun's approval before writing code.**

## Current status

- ✅ Memory system: `PROJECT_NOTES.md` + `DECISIONS.md` + `CLAUDE.md` (CLAUDE.md auto-loads each
  session and tells Claude to read these first — so a reset re-orients automatically).
- ✅ Plan approved. Repo `git init`'d; V1 scaffold created (`src/`, `data/clients/`, `requirements.txt`,
  `.gitignore`, `.env.example`).
- ⬜ Next: build the pipeline (see build order). GitHub remote + Anthropic API key pending Shaun.
- Local env: Python 3.11 ✓, git ✓. Before the `llm.py` step: `pip install -r requirements.txt` + an
  Anthropic API key in `.env`.

## Build order (each step independently testable)

1. ✅ Skeleton — folders, `requirements.txt`, `.gitignore`, `.env.example`.
2. ⬜ `src/llm.py` — one Haiku call end-to-end (needs API key). Proves the SDK + key work.
3. ⬜ `src/storage.py` + `src/profile.py` — JSON read/write + client profile (no key, no cost).
4. ⬜ `src/prompts.py` + `src/chain.py` — the 4-step chain, tested on a sample note in the terminal.
5. ⬜ `app.py` — Streamlit UI: paste → run → show the 4 outputs → save.
6. ⬜ Wire the profile-memory update into the flow.
7. ⬜ Per-client meeting history view.

## Repo structure

```
Finance AI/
├── CLAUDE.md              ← auto-loaded; tells Claude to read the two files below first
├── PROJECT_NOTES.md       ← current state (this file)
├── DECISIONS.md           ← append-only "why" log
├── requirements.txt
├── .gitignore
├── .env.example           ← copy to .env and add your key (.env is gitignored)
├── src/                   ← app modules (one job each) — built step by step
└── data/clients/          ← per-client profile.json + meetings/<timestamp>.json (created at runtime)
```

## Roadmap (one stage at a time — do NOT bundle)

- **V1** — the core pipeline above. ← we are here
- **V1.5** — conversation simulator with three modes:
  1. **Batch**: two AI personas (client + wealth manager) auto-generate a full synthetic transcript fast → feeds into V1 pipeline
  2. **Human-in-the-loop**: Shaun plays one side (client OR advisor), AI plays the other in real back-and-forth
  3. **Real-time / live**: simulation runs in real time with audio so Shaun can listen to the call as it happens, with the V1 pipeline running live on the output
- **V2+ (separate, deliberate stages, no required order):** RAG over past meetings · vector DB
  (semantic search of history) · a real evaluation system (score accuracy/consistency/hallucination
  across many transcripts) · agents (AI picks which steps to run) · multi-agent · MCP tool connections.
- **V3 — voice personas + live platform integration (final vision):** AI personas get real voices
  (TTS with distinct character voices). Modes: AI talks to AI (full audio call simulation you listen
  to) · Shaun talks to an AI persona in real time (STT → AI responds → TTS) · AI personas join or
  simulate a Zoom call. This is the "you can actually hear the meeting happening" endgame.

## Final UI vision (additive — each version builds on the last)

The UI grows incrementally. Nothing gets rebuilt from scratch; features get added on top.

**What V1 UI does (now):** paste notes → pick client → run → see 4 outputs in tabs → download email.

**Confirmed future UI features (add as stages are built):**
- Conversation list in sidebar — click any past meeting to open it
- Full transcript view per meeting + audio playback (once V1.5/V3 voice is built)
- Semantic search across meetings — ask a question like "when did John mention college funding?" not keyword search (needs RAG / V2)
- Creative Q&A against the full meeting history — "given X, Y, Z what do you recommend?" routed to a WM-specialized LLM (this is model routing / agentic — V2+)
- Simulation launcher inside the UI — trigger a test conversation without needing the terminal; option to play one side yourself or have AI play both
- Client persona toggles for simulation — set age, risk profile, life stage, personality to shape how the AI client talks
- Action item tracker — mark items done, set reminders, see outstanding items across all clients

**Features Shaun didn't mention but should be in there:**
- Export full meeting output as PDF (not just email .txt) — makes the tool usable in a real advisory context
- Meeting timeline view — see all meetings for a client in chronological order with key facts surfaced
- Profile diff — "what changed about this client since last meeting?" shown automatically

**Optional / decide later:**
- Calendar integration — auto-suggest follow-up meeting based on action items
- Document upload — drop in a PDF transcript instead of pasting text
- Multi-advisor support — if this ever becomes a team tool, meetings are tagged by advisor
- Comparison view — look at two clients side by side (useful for portfolio benchmarking)

## Out of scope for V1 (and a while)

Authentication, payments, live meeting/video-call attachment, vector databases, agents,
multi-agent systems, RAG. These are real *future* stages, not abandoned — see roadmap.

---

## How to resume a session (the routine)

When a fresh Claude Code session starts:
1. Read this file (PROJECT_NOTES.md) top to bottom.
2. Skim `DECISIONS.md` for the "why" behind choices already made.
3. Look at the actual file tree to see what exists.
4. Then continue. Don't ask Shaun to re-explain context this file already covers.

**When to update this file:** after a meaningful change — a feature built, an architecture
choice made, a file added, scope changed. NOT after every small edit. Keep it short and true.
Log the *decision* and its *why* in `DECISIONS.md`; keep current *state* here.
