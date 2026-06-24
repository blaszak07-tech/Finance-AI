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
