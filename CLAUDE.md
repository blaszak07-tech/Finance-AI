# Claude Code — start here

**At the start of every session, read [PROJECT_NOTES.md](PROJECT_NOTES.md) (current state) and
[DECISIONS.md](DECISIONS.md) (the "why") before doing anything. They are the source of truth —
trust them over old chat history, and over this file if they ever conflict.**

**Project:** AI Wealth Management Meeting Assistant — see PROJECT_NOTES.md for what it is and where we are.

**Hard rules (stable guardrails):**
- Build V1 first; never build ahead. Add roadmap stages one at a time.
- Default model: `claude-haiku-4-5` (cost). Consider `claude-sonnet-4-6` only for the planning-flags step.
- Budget = LLM API tokens only. No paid tools or tiers.
- Wait for Shaun's approval before writing code.
- After a meaningful change (feature built, architecture choice, file added), update PROJECT_NOTES.md and DECISIONS.md.
