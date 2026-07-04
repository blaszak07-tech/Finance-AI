# DECISIONS.md — why things are the way they are

> Append-only log of meaningful decisions. Newest at the bottom. Each entry: what we decided,
> why, and the date. This is the "engineering reasoning" record — when a future session (or a
> future Shaun) asks "why did we do it this way?", the answer lives here. Don't rewrite history;
> if a decision is reversed, add a NEW entry that supersedes the old one.

---

### D-001 — Claude Code is the primary home for this project (2026-06-17)
**Decided:** All building AND planning/architecture/"why" discussion happens here in Claude Code
(VS Code). The separate chat-based Claude is used only for things outside the project's context:
finance domain-knowledge checks, resume/interview framing, career strategy.
**Why:** Claude Code has full project context (files, current state, prior decisions). Routing
architecture questions through a separate chat is a lossy, slower relay with no benefit.

### D-002 — Persistent project memory lives in the repo (2026-06-17)
**Decided:** Keep `PROJECT_NOTES.md` (current state, read-first) and `DECISIONS.md` (this file,
append-only "why"). First action of any new session: read PROJECT_NOTES.md, skim DECISIONS.md,
look at the file tree. Update after meaningful changes, not every edit.
**Why:** Shaun wants to reset sessions periodically to save credits. Resetting normally loses all
context. An in-repo memory file lets a new session catch up cheaply instead of replaying chat
history. This is the standard real-world pattern (a README/architecture doc, not a chat log).

### D-003 — Default model is Claude Haiku 4.5; Sonnet 4.6 reserved for judgment (2026-06-17)
**Decided:** Use `claude-haiku-4-5` (~$1/$5 per 1M input/output tokens) as the default model for
all pipeline steps. The "planning flags" step requires actual financial judgment, not just
extraction — if Haiku's output there is shallow once built, upgrade *only that step* to
`claude-sonnet-4-6` (~$3/$15). Evaluate empirically after building, don't pre-optimize.
**Why:** Budget constraint = tokens only. Haiku is extremely cheap and sufficient for
extraction/summarization. A $5 prepay of Haiku usage lasts a very long time at this volume.

### D-004 — V1 scope is locked (2026-06-17)
**Decided:** V1 = text input → prompt chain (summary · action items · planning flags · follow-up
email) → client profile memory (persists across sessions) → local JSON storage → Streamlit UI.
Explicitly OUT for V1: auth, payments, live meeting/video attachment, vector DB, RAG, agents,
multi-agent. Those are later, separate roadmap stages added one at a time.
**Why:** Depth over breadth. Get one clean, well-understood pipeline working and demoable before
layering on advanced techniques, so that when something breaks Shaun knows exactly where.

### D-005 — Version control from day one + CLAUDE.md auto-load (2026-06-17)
**Decided:** `git init` the repo at the start (local, free). Added a small `CLAUDE.md` at the root that
Claude Code auto-loads every session; it tells Claude to read PROJECT_NOTES.md + DECISIONS.md first and
restates the hard guardrails. GitHub remote (recommended public, for backup + resume value) to be added
on Shaun's explicit go — pushing publishes it.
**Why:** Local git is free and records how the project evolved (a resume-relevant skill). CLAUDE.md makes
session re-orientation automatic instead of relying on Shaun to remember to point Claude at the notes.
A public GitHub repo is a concrete portfolio artifact for finance interviews.

### D-006 — Agents = orchestrator-workers, not a tool-loop (2026-06-24)
**Decided:** The first "agents" stage is an **orchestrator + 3 specialist analysts** (Retirement & Income,
Tax, Risk & Portfolio). One orchestrator call reads the meeting and returns JSON picking which specialists
are relevant; only those run, each as its own focused Claude call. Three specialists = the real pillars of
WM planning; deliberately NOT more. Lives in its own "Agents" tab showing the routing decision + each
specialist's findings. Did NOT build a full autonomous tool-using agent loop (model acts→observes→repeats);
that's a later, separate stage.
**Why:** The only place in the app with a genuine control-flow *decision* is which analysis to run — that's
where an agent earns its keep. Orchestrator-workers is the honest, minimal pattern that demonstrates "the
model decides what runs" without overbuilding. Routing is visible in the UI so it's a real teaching/demo
artifact. Tool-loop agents add real complexity (stopping conditions, tool plumbing) and deserve their own
stage rather than being rushed in here. Keeping to 3 specialists honors "a couple is enough — don't build a zoo."

### D-007 — Tool-loop agent + eval system (2026-06-24)
**Decided:** (1) Added a full autonomous **tool-loop agent** (`src/tool_agent.py`, "Auto-Agent" tab) using
Claude tool use. Tools reuse existing capabilities (search_history, get_profile, run_specialist). It loops
act→observe→decide up to `max_steps` (6), then forces a final answer. UI shows the full trace. (2) Added an
**eval system** (`src/eval.py`) on the LLM-as-judge pattern. Two faces: a PRODUCTION `score_accuracy` wired
into `run_chain` (every saved meeting stores a 0-100 summary-accuracy score, shown under the summary), and an
EDUCATIONAL "Eval" tab showing the full breakdown (hallucinations/omissions/reasoning + multi-run consistency).
Default model stays Haiku for both, per budget.
**Why:** Tool-loop is the autonomous rung above D-006 — built second, deliberately, once orchestrator-workers
was solid. Eval is the honest answer to "is the output actually good?": LLM-as-judge turns "looks fine" into a
tracked number, and finally lets us answer empirically whether Haiku is enough or a step needs Sonnet. Shaun
wanted the accuracy score baked into the finished product (not just a demo), so it lives in the pipeline; the
tab is the teaching view. Adds one judge call per meeting — acceptable on the token-only budget.

### D-008 — V2 leftovers completed (2026-06-24)
**Decided:** Finished the remaining V2 items in one pass so only V3/V4/front-end remain:
(1) **Multi-agent panel** (`agents.run_panel`): specialists → cross-review each other → lead-advisor synthesis
that resolves conflicts. Exposed as a "Panel" mode in the Agents tab (Quick vs Panel).
(2) **MCP** (`mcp_server.py` + `mcp_bridge.py`): a genuine MCP server (FastMCP over stdio) exposing four finance
calculators; the tool-loop agent discovers them via the protocol and calls them for exact math. Sync bridge wraps
the async MCP client in `asyncio.run`; per-call subprocess (calculators are stateless). Falls back gracefully to
built-in tools if MCP is unavailable.
(3) **Structured financial extraction** (`financials.py`): a typed snapshot (accounts/other_assets/liabilities/
income/goals, numeric) reconciled each meeting by handing Claude the existing snapshot + new notes (LLM-as-merger,
avoids fuzzy name-matching in code). Net worth computed and shown in the sidebar. Wired into `run_chain`.
(4) **Stronger flags prompt**: FLAGS_SYSTEM rewritten around real WM frameworks.
**Why:** These round out the applied-AI surface: multi-agent collaboration (agents reading each other), the MCP
standard (external tools over a protocol, exact computation vs hallucinated math), and typed extraction with
structured-output discipline. All stay on the Haiku/token-only budget. MCP chosen as a real local server rather
than a hosted one to honor "no paid services" while still demonstrating the actual protocol.

### D-009 — V3 real-time voice: Pipecat + all-local stack (2026-06-24)
**Decided:** Built the V3 core (`live/bot.py`) with **Pipecat** orchestrating a fully local/free real-time
voice loop: SmallWebRTC transport (browser mic) → Silero VAD (barge-in/turn-taking) → MLX Whisper STT
(Apple-Silicon-native) → Claude Haiku (Anthropic service) → Kokoro TTS → speakers. Runs as a SEPARATE process
(Pipecat's runner serves a prebuilt WebRTC UI at :7860) because Streamlit can't do full-duplex audio; it shares
the `data/` store and on hangup runs `run_chain` + `save_meeting` so live meetings land in history. You play the
client, AI plays the advisor. Deps kept in a separate `requirements-live.txt` (heavy + macOS/MLX-specific) so the
main Streamlit app stays light. Fixed the macOS Python SSL/nltk cert issue via certifi. First feasibility-probed
the whole stack (installs + Kokoro RTF 0.22x + server boots + UI serves) before building.
**Why:** Real-time interruptible voice needs streaming + WebRTC, which Streamlit fundamentally can't do — so V3
is architecturally separate by necessity, not choice. Pipecat is the standard open-source framework for exactly
this loop and had free local services for every stage, keeping the tokens-only budget intact (money would only buy
lower latency / lifelike voices, not the feature). Probing before building retired the "biggest, riskiest build"
risk up front. Chose you=client / AI=advisor as the most natural first demo; two-AI-live and a live pipeline
overlay are clean follow-on extensions. This is the last major build before V4 platform integration, which reuses
this exact stack pointed at a real call instead of a browser mic.
