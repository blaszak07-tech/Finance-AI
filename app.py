import json
import streamlit as st
from src.chain import run_chain
from src.simulator import simulate_conversation, random_persona, ai_opening_line, ai_reply
from src.voice import speak, transcribe, synthesize_conversation
from src.search import build_index, search_index, answer_from_context
from src.agents import run_analysis, run_panel
from src.tool_agent import run_agent, available_tools
from src.eval import run_eval, score_groundedness, SAMPLE_TRANSCRIPTS
from src.storage import save_meeting, load_meetings, list_clients, rename_client, delete_client, load_financials
from src.profile import profile_summary
from src.financials import net_worth


def accuracy_caption(result_or_meeting: dict) -> None:
    """Show the stored accuracy score, if present."""
    acc = (result_or_meeting or {}).get("accuracy")
    if acc and acc.get("accuracy") is not None:
        st.caption(f"📊 Summary accuracy (LLM-as-judge): **{acc['accuracy']}/100**")


def groundedness_caption(score: dict) -> None:
    """Show a groundedness score for a Q&A answer, with any flagged unsupported claims."""
    if score and score.get("groundedness") is not None:
        st.caption(f"📊 Groundedness (LLM-as-judge): **{score['groundedness']}/100** — is the answer supported by the evidence it used")
        if score.get("unsupported_claims"):
            with st.expander(f"⚠️ {len(score['unsupported_claims'])} unsupported claim(s) the judge flagged"):
                for c in score["unsupported_claims"]:
                    st.markdown(f"- {c}")


def md(text: str) -> None:
    """Render AI-generated markdown, escaping $ so Streamlit doesn't treat them as LaTeX."""
    st.markdown(text.replace("$", r"\$"))


def transcript_from(messages: list[dict]) -> str:
    """Turn a list of {role, text} messages into a plain-text transcript."""
    return "\n\n".join(f"{m['role']}: {m['text']}" for m in messages)


RISK_OPTIONS = ["Conservative", "Moderate", "Aggressive"]
PERSONALITY_OPTIONS = [
    "Cooperative and trusting", "Skeptical and cautious", "Anxious and risk-averse",
    "Analytical and detail-oriented", "Decisive and confident",
]

st.set_page_config(page_title="WM Meeting Assistant", layout="wide")

st.title("Wealth Management Meeting Assistant")

# --- Sidebar: client selection ---
st.sidebar.header("Client")
existing_clients = list_clients()

client_mode = st.sidebar.radio(
    "", ["Existing client", "New client"], label_visibility="collapsed"
)

client_id = ""
display_name = ""

if client_mode == "New client":
    raw_name = st.sidebar.text_input("Client name", placeholder="e.g. John Smith")
    if raw_name.strip():
        client_id = raw_name.strip().lower().replace(" ", "_")
        display_name = raw_name.strip()
    else:
        st.sidebar.caption("Type a name to get started.")
else:
    if existing_clients:
        selected = st.sidebar.selectbox("Select client", existing_clients)
        client_id = selected
        display_name = selected.replace("_", " ").title()
    else:
        st.sidebar.info("No clients yet. Switch to **New client**.")

# Known profile
if client_id:
    profile = profile_summary(client_id)
    if profile != "No prior profile on file for this client.":
        with st.sidebar.expander("Known profile"):
            st.text(profile)

# Structured financial snapshot
if client_id:
    fin = load_financials(client_id)
    if fin:
        with st.sidebar.expander("💰 Financial snapshot"):
            st.metric("Net worth", f"${net_worth(fin):,.0f}")
            if fin.get("accounts"):
                st.markdown("**Accounts**")
                for a in fin["accounts"]:
                    st.markdown(f"- {a.get('name', '?')} ({a.get('type', '')}): ${a.get('balance', 0):,.0f}")
            if fin.get("other_assets"):
                st.markdown("**Other assets**")
                for a in fin["other_assets"]:
                    st.markdown(f"- {a.get('name', '?')}: ${a.get('value', 0):,.0f}")
            if fin.get("liabilities"):
                st.markdown("**Liabilities**")
                for l in fin["liabilities"]:
                    st.markdown(f"- {l.get('name', '?')}: ${l.get('balance', 0):,.0f}")
            if fin.get("income"):
                st.markdown("**Income**")
                for inc in fin["income"]:
                    st.markdown(f"- {inc.get('source', '?')}: ${inc.get('annual', 0):,.0f}/yr")
            if fin.get("goals"):
                st.markdown("**Goals**")
                for g in fin["goals"]:
                    st.markdown(f"- {g.get('goal', '?')} — {g.get('target', '')}")

# Manage existing client (rename / delete)
if client_id and client_mode == "Existing client":
    with st.sidebar.expander("Manage client"):
        new_name = st.text_input("Rename to", placeholder="New name")
        if st.button("Rename", disabled=not new_name.strip()):
            try:
                rename_client(client_id, new_name.strip())
                st.success(f"Renamed to {new_name.strip()}")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

        st.divider()
        confirm_delete = st.checkbox("I understand this deletes all meeting history")
        if st.button("Delete client", disabled=not confirm_delete, type="secondary"):
            delete_client(client_id)
            st.success("Client deleted.")
            st.rerun()

st.sidebar.divider()
st.sidebar.caption("Finance AI")

# --- Main area ---
if not client_id:
    st.info("Select or create a client in the sidebar to get started.")
    st.stop()

st.subheader(display_name)

tab_new, tab_voice, tab_ask, tab_agents, tab_autoagent, tab_eval, tab_history = st.tabs(
    ["New Meeting", "Voice", "Ask", "Agents", "Auto-Agent", "Eval", "History"]
)

# ── New Meeting ──────────────────────────────────────────────
with tab_new:
    notes = st.text_area(
        "Paste raw notes or a transcript",
        height=250,
        placeholder="e.g. John wants to retire at 60, worried about market volatility...",
        label_visibility="collapsed",
    )

    run = st.button("Run", type="primary", disabled=not notes.strip())

    if run:
        with st.spinner("Running through Haiku..."):
            result = run_chain(client_id, notes)
            save_meeting(client_id, {"notes": notes, **result})

        st.success("Done — meeting saved to history")

        new_facts = result.get("new_profile_facts", {})
        if new_facts:
            with st.expander(f"Profile updated — {len(new_facts)} new fact(s) learned", expanded=True):
                for k, v in new_facts.items():
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

        r_summary, r_actions, r_flags, r_email = st.tabs(
            ["Summary", "Action Items", "Planning Flags", "Follow-up Email"]
        )
        with r_summary:
            md(result["summary"])
            accuracy_caption(result)
        with r_actions:
            md(result["action_items"])
        with r_flags:
            md(result["flags"])
        with r_email:
            md(result["email"])
            st.divider()
            st.download_button(
                "Download email as .txt",
                data=result["email"],
                file_name=f"{client_id}_followup.txt",
                mime="text/plain",
            )


# ── Voice ────────────────────────────────────────────────────
def _fill_random_persona_voc():
    p = random_persona()
    st.session_state.voc_age = p["age"]
    st.session_state.voc_risk = p["risk"]
    st.session_state.voc_personality = p["personality"]
    st.session_state.voc_situation = p["situation"]
    st.session_state.voc_concerns = p["concerns"]


_VOICE_KEYS = ["v_active", "v_messages", "v_human_role", "v_ai_role", "v_persona", "v_client", "v_last_audio", "v_summary", "v_accuracy"]


def _render_timed_transcript(timed: list[dict]):
    for t in timed:
        st.markdown(f"`{t['timestamp']}`  **{t['role']}**")
        md(t["text"])


with tab_voice:
    st.caption("Conduct a meeting by voice. When the conversation ends, the pipeline runs automatically and the meeting is saved — see full output under History. Free system voices: Daniel (advisor) & Samantha (client).")
    mode = st.radio("Mode", ["Two AI voices", "I speak (one side)"], horizontal=True, key="voice_top_mode")

    # ── Two AI voices: generate a voiced conversation, then auto-run the pipeline ──
    if mode == "Two AI voices":
        st.session_state.setdefault("voc_age", 50)
        st.session_state.setdefault("voc_risk", "Moderate")
        st.session_state.setdefault("voc_personality", PERSONALITY_OPTIONS[0])
        st.session_state.setdefault("voc_situation", "")
        st.session_state.setdefault("voc_concerns", "")

        st.button("🎲 Random persona", on_click=_fill_random_persona_voc, key="voc_random")
        vc1, vc2 = st.columns(2)
        with vc1:
            st.number_input("Age", min_value=25, max_value=85, key="voc_age")
            st.selectbox("Risk tolerance", RISK_OPTIONS, key="voc_risk")
        with vc2:
            st.selectbox("Personality", PERSONALITY_OPTIONS, key="voc_personality")
            voc_exchanges = st.slider("Conversation length (exchanges)", 2, 6, 3, key="voc_exchanges")
        st.text_area("Client situation", height=70, key="voc_situation")
        st.text_area("Key concerns", height=70, key="voc_concerns")

        voc_ready = bool(st.session_state.voc_situation.strip() and st.session_state.voc_concerns.strip())
        if st.button("Generate voiced conversation", type="primary", disabled=not voc_ready, key="voc_gen"):
            with st.spinner("Simulating conversation…"):
                turns = simulate_conversation(
                    name=display_name,
                    age=int(st.session_state.voc_age),
                    situation=st.session_state.voc_situation.strip(),
                    risk_tolerance=st.session_state.voc_risk.lower(),
                    personality=st.session_state.voc_personality.lower(),
                    concerns=st.session_state.voc_concerns.strip(),
                    num_exchanges=int(voc_exchanges),
                )
            with st.spinner("Generating audio…"):
                audio_bytes, timed = synthesize_conversation(turns)
            transcript = "\n\n".join(f"{t['role']}: {t['text']}" for t in turns)
            with st.spinner("Running pipeline & saving…"):
                result = run_chain(client_id, transcript)
                save_meeting(client_id, {"notes": transcript, **result})
            st.session_state.voc_audio = audio_bytes
            st.session_state.voc_timed = timed
            st.session_state.voc_summary = result["summary"]
            st.session_state.voc_accuracy = result.get("accuracy")

        if st.session_state.get("voc_audio"):
            st.success("Meeting saved to history")
            st.audio(st.session_state.voc_audio, format="audio/wav")
            st.subheader("Transcript")
            _render_timed_transcript(st.session_state.voc_timed)
            st.divider()
            st.markdown("#### Meeting summary")
            md(st.session_state.voc_summary)
            accuracy_caption({"accuracy": st.session_state.get("voc_accuracy")})
            st.caption("Action items, planning flags, and the follow-up email are under the History tab.")

    # ── I speak: push-to-talk, you play one side, AI plays the other ──
    else:
        if st.session_state.get("v_active") and st.session_state.get("v_client") != client_id:
            for k in _VOICE_KEYS:
                st.session_state.pop(k, None)

        if not st.session_state.get("v_active"):
            human_role = st.radio("You play the…", ["Advisor", "Client"], horizontal=True, key="v_role_choice")

            if human_role == "Advisor":
                st.markdown(f"The AI plays **{display_name}** (the client). Set their persona:")
                st.session_state.setdefault("v_age", 50)
                st.session_state.setdefault("v_risk", "Moderate")
                st.session_state.setdefault("v_personality", PERSONALITY_OPTIONS[0])
                st.session_state.setdefault("v_situation", "")
                st.session_state.setdefault("v_concerns", "")

                def _fill_v():
                    p = random_persona()
                    st.session_state.v_age = p["age"]; st.session_state.v_risk = p["risk"]
                    st.session_state.v_personality = p["personality"]
                    st.session_state.v_situation = p["situation"]; st.session_state.v_concerns = p["concerns"]

                st.button("🎲 Random client persona", on_click=_fill_v, key="v_random")
                vsc1, vsc2 = st.columns(2)
                with vsc1:
                    st.number_input("Age", min_value=25, max_value=85, key="v_age")
                    st.selectbox("Risk tolerance", RISK_OPTIONS, key="v_risk")
                with vsc2:
                    st.selectbox("Personality", PERSONALITY_OPTIONS, key="v_personality")
                st.text_area("Client situation", height=70, key="v_situation")
                st.text_area("Key concerns", height=70, key="v_concerns")
                v_ready = bool(st.session_state.v_situation.strip() and st.session_state.v_concerns.strip())
            else:
                st.markdown("The AI plays the **advisor** and will speak first. You answer out loud as the client.")
                v_ready = True

            if st.button("Start voice meeting", type="primary", disabled=not v_ready, key="v_start"):
                st.session_state.v_human_role = human_role
                st.session_state.v_ai_role = "Client" if human_role == "Advisor" else "Advisor"
                st.session_state.v_client = client_id
                st.session_state.v_messages = []
                st.session_state.v_last_audio = None
                st.session_state.v_summary = None
                if human_role == "Advisor":
                    st.session_state.v_persona = {
                        "name": display_name, "age": int(st.session_state.v_age),
                        "situation": st.session_state.v_situation.strip(),
                        "risk_tolerance": st.session_state.v_risk.lower(),
                        "personality": st.session_state.v_personality.lower(),
                        "concerns": st.session_state.v_concerns.strip(),
                    }
                else:
                    st.session_state.v_persona = None
                    with st.spinner("Starting the meeting…"):
                        opening = ai_opening_line("Advisor")
                        st.session_state.v_messages.append({"role": "Advisor", "text": opening})
                        st.session_state.v_last_audio = speak(opening, "Advisor")
                st.session_state.v_active = True
                st.rerun()

        else:
            human_role = st.session_state.v_human_role
            ai_role = st.session_state.v_ai_role
            messages = st.session_state.v_messages

            st.markdown(f"**You:** {human_role}  ·  **AI:** {ai_role}  ·  **Client:** {display_name}")

            for m in messages:
                who = "user" if m["role"] == human_role else "assistant"
                with st.chat_message(who):
                    st.markdown(f"**{m['role']}**")
                    md(m["text"])

            if st.session_state.get("v_last_audio"):
                st.audio(st.session_state.v_last_audio, format="audio/wav", autoplay=True)

            with st.form("voice_form", clear_on_submit=True):
                clip = st.audio_input(f"Record your message as the {human_role.lower()}")
                sent = st.form_submit_button("Send")

            if sent and clip is not None:
                with st.spinner("Transcribing…"):
                    text = transcribe(clip.getvalue())
                if text:
                    messages.append({"role": human_role, "text": text})
                    with st.spinner(f"{ai_role} is responding…"):
                        reply = ai_reply(ai_role, transcript_from(messages), st.session_state.v_persona)
                    messages.append({"role": ai_role, "text": reply})
                    st.session_state.v_messages = messages
                    st.session_state.v_last_audio = speak(reply, ai_role)
                    st.rerun()
                else:
                    st.warning("Didn't catch that — try recording again.")

            col_e, col_r = st.columns(2)
            with col_e:
                v_end = st.button("End meeting & save", type="primary", disabled=len(messages) < 2, key="v_end")
            with col_r:
                if st.button("Reset conversation", key="v_reset"):
                    for k in _VOICE_KEYS:
                        st.session_state.pop(k, None)
                    st.rerun()

            if v_end:
                transcript = transcript_from(messages)
                with st.spinner("Running pipeline & saving…"):
                    result = run_chain(client_id, transcript)
                    save_meeting(client_id, {"notes": transcript, **result})
                st.session_state.v_summary = result["summary"]
                st.session_state.v_accuracy = result.get("accuracy")

            if st.session_state.get("v_summary"):
                st.success("Meeting saved to history")
                st.divider()
                st.markdown("#### Meeting summary")
                md(st.session_state.v_summary)
                accuracy_caption({"accuracy": st.session_state.get("v_accuracy")})
                st.caption("Action items, planning flags, and the follow-up email are under the History tab.")


# ── Ask (semantic search + RAG over history) ─────────────────
@st.cache_data(show_spinner=False)
def _cached_index(client_id: str, n_meetings: int):
    # Cached by (client, #meetings) so we only re-embed when a meeting is added
    return build_index(client_id)


with tab_ask:
    st.caption("Ask anything about this client's history in plain language. Semantic search over past meetings (local embeddings) feeds the relevant moments to Claude.")
    meetings = load_meetings(client_id)

    if not meetings:
        st.info("No meetings on file yet. Generate or record one in the Voice tab first.")
    else:
        question = st.text_input(
            "Your question",
            placeholder="e.g. What are this client's concerns about retirement? · When did college funding come up?",
            key="ask_q",
        )
        if st.button("Ask", type="primary", disabled=not question.strip(), key="ask_btn"):
            with st.spinner("Searching meeting history…"):
                chunks, embs = _cached_index(client_id, len(meetings))
                hits = search_index(chunks, embs, question.strip(), top_k=5)
            with st.spinner("Thinking…"):
                answer = answer_from_context(question.strip(), hits)
            with st.spinner("Scoring groundedness…"):
                evidence = "\n\n".join(f"[{h['timestamp']}] {h['text']}" for h in hits)
                ground = score_groundedness(question.strip(), evidence, answer)

            st.markdown("### Answer")
            md(answer)
            groundedness_caption(ground)

            with st.expander(f"Sources — {len(hits)} passage(s) the answer drew from"):
                for h in hits:
                    st.markdown(f"`{h['timestamp']}` · similarity {h['score']:.2f}")
                    md(h["text"])
                    st.divider()


def _render_specialist_sources(sources):
    if sources:
        with st.expander(f"History this specialist pulled — {len(sources)} passage(s)"):
            for h in sources:
                st.markdown(f"`{h['timestamp']}` · similarity {h['score']:.2f}")
                md(h["text"])
                st.divider()


# ── Agents (orchestrator + specialist analysts) ──────────────
with tab_agents:
    st.caption("An orchestrator routes the meeting to only the relevant specialist analysts — Retirement & Income, Tax, Risk & Portfolio. Quick = one pass each. Panel = they also cross-review each other and a lead advisor synthesizes a conflict-resolved plan (multi-agent).")
    ag_meetings = load_meetings(client_id)

    ag_mode = st.radio("Analysis mode", ["Quick (single pass)", "Panel (multi-agent)"], horizontal=True, key="ag_mode")

    st.session_state.setdefault("ag_notes", "")
    if ag_meetings and ag_meetings[0].get("notes"):
        if st.button("Load last meeting's notes", key="ag_load"):
            st.session_state.ag_notes = ag_meetings[0]["notes"]

    ag_notes = st.text_area(
        "Meeting notes to analyze",
        height=200,
        placeholder="Paste meeting notes, or load the last meeting above.",
        key="ag_notes",
    )

    if st.button("Run analyst team", type="primary", disabled=not ag_notes.strip(), key="ag_run"):
        index = _cached_index(client_id, len(ag_meetings)) if ag_meetings else ([], None)
        if ag_mode.startswith("Panel"):
            with st.spinner("Routing → specialists analyzing → cross-review → lead advisor synthesis…"):
                st.session_state.ag_result = {"mode": "panel", **run_panel(client_id, ag_notes.strip(), index=index)}
        else:
            with st.spinner("Orchestrator routing → specialists analyzing history…"):
                st.session_state.ag_result = {"mode": "quick", **run_analysis(client_id, ag_notes.strip(), index=index)}

    res = st.session_state.get("ag_result")
    if res:
        st.divider()
        st.markdown("#### Orchestrator decision")
        engaged = [res["available"][k] for k in res["selected"]]
        skipped = [v for k, v in res["available"].items() if k not in res["selected"]]
        st.markdown("**Engaged:** " + " · ".join(f"`{e}`" for e in engaged))
        if skipped:
            st.caption("Skipped: " + ", ".join(skipped))
        md(f"_Reasoning:_ {res['reasoning']}")
        st.divider()

        if res.get("mode") == "panel":
            st.markdown("### 🧑‍⚖️ Lead advisor — synthesized plan")
            md(res["synthesis"])
            st.divider()
            st.markdown("#### Specialist findings & cross-review")
            cross_by_key = {c["key"]: c["text"] for c in res.get("cross", [])}
            for f in res["round1"]:
                with st.expander(f"{f['label']}"):
                    st.markdown("**Initial findings**")
                    md(f["text"])
                    if f["key"] in cross_by_key:
                        st.markdown("**Cross-review (after seeing the others)**")
                        md(cross_by_key[f["key"]])
                    _render_specialist_sources(f.get("sources", []))
        else:
            for f in res["findings"]:
                st.markdown(f"#### {f['label']}")
                md(f["text"])
                _render_specialist_sources(f.get("sources", []))


# ── Auto-Agent (full tool-use loop) ──────────────────────────
with tab_autoagent:
    st.caption("An autonomous agent. Unlike the Agents tab (one fixed routing step), this one runs in a loop: it decides which tool to call, sees the result, and decides its next move — until it can answer. You watch it work.")
    with st.expander("Tools the agent can use"):
        _tools = available_tools()
        st.markdown("**Built-in:** " + ", ".join(f"`{t}`" for t in _tools["built-in"]))
        st.markdown("**MCP server (finance calculators):** " + ", ".join(f"`{t}`" for t in _tools["MCP server"]))
        st.caption("The MCP tools run in a separate server process and are discovered over the Model Context Protocol — the agent gets exact math instead of estimating.")
    aa_meetings = load_meetings(client_id)

    aa_q = st.text_input(
        "Ask the agent to investigate something about this client",
        placeholder="e.g. Should this client do a Roth conversion this year, and is their portfolio positioned right?",
        key="aa_q",
    )
    if st.button("Run agent", type="primary", disabled=not aa_q.strip(), key="aa_run"):
        with st.spinner("Agent working — calling tools, observing, deciding…"):
            index = _cached_index(client_id, len(aa_meetings)) if aa_meetings else ([], None)
            res = run_agent(client_id, aa_q.strip(), index=index)
        with st.spinner("Scoring groundedness…"):
            evidence = "\n\n".join(s["result"] for s in res["steps"] if s["type"] == "action")
            res["groundedness"] = score_groundedness(aa_q.strip(), evidence, res["answer"])
        st.session_state.aa_result = res

    aa_res = st.session_state.get("aa_result")
    if aa_res:
        st.divider()
        st.markdown("#### Agent trace")
        st.caption(f"{sum(1 for s in aa_res['steps'] if s['type'] == 'action')} tool call(s) — the agent chose these itself")
        for s in aa_res["steps"]:
            if s["type"] == "thought":
                st.markdown(f"🤔 {s['text']}")
            else:
                st.markdown(f"🔧 **{s['tool']}**  `{json.dumps(s['input'])}`")
                with st.expander("tool result"):
                    md(s["result"])
        st.divider()
        st.markdown("#### Final answer")
        md(aa_res["answer"])
        groundedness_caption(aa_res.get("groundedness"))


# ── Eval (educational: how we measure quality) ───────────────
with tab_eval:
    st.caption("How do we know the AI's output is trustworthy? LLM-as-judge: a separate Claude call grades a generated summary against the original transcript for faithfulness. (This same scoring runs automatically on every saved meeting — see the accuracy score under each summary.)")

    eval_meetings = load_meetings(client_id)
    source_options = list(SAMPLE_TRANSCRIPTS.keys())
    if eval_meetings and eval_meetings[0].get("notes"):
        source_options = ["This client's last meeting"] + source_options

    source = st.selectbox("Transcript to evaluate", source_options, key="eval_source")
    runs = st.slider("Runs (more = shows consistency / non-determinism)", 1, 3, 1, key="eval_runs")

    if st.button("Run evaluation", type="primary", key="eval_run"):
        if source == "This client's last meeting":
            transcript = eval_meetings[0]["notes"]
        else:
            transcript = SAMPLE_TRANSCRIPTS[source]
        with st.spinner("Generating summary, then judging it…"):
            st.session_state.eval_result = run_eval(transcript, runs=runs)

    ev = st.session_state.get("eval_result")
    if ev:
        st.divider()
        with st.expander("Transcript that was evaluated"):
            st.text(ev["transcript"])

        scores = [r["score"]["accuracy"] for r in ev["results"] if r["score"]["accuracy"] is not None]
        if len(scores) > 1:
            st.markdown(f"**Accuracy across {len(scores)} runs:** {scores}  ·  avg **{sum(scores)/len(scores):.0f}/100**  ·  spread {min(scores)}–{max(scores)}")
            st.caption("Same input, different scores = the non-determinism eval exists to catch.")

        for i, r in enumerate(ev["results"], 1):
            sc = r["score"]
            st.markdown(f"#### Run {i}" if len(ev["results"]) > 1 else "#### Result")
            if sc["accuracy"] is not None:
                st.metric("Accuracy (LLM-as-judge)", f"{sc['accuracy']}/100")
            with st.expander("Generated summary"):
                md(r["summary"])
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Hallucinations**")
                if sc["hallucinations"]:
                    for h in sc["hallucinations"]:
                        st.markdown(f"- {h}")
                else:
                    st.caption("None found")
            with cols[1]:
                st.markdown("**Omissions**")
                if sc["omissions"]:
                    for o in sc["omissions"]:
                        st.markdown(f"- {o}")
                else:
                    st.caption("None found")
            md(f"_Judge reasoning:_ {sc['reasoning']}")
            st.divider()


# ── History ──────────────────────────────────────────────────
with tab_history:
    meetings = load_meetings(client_id)

    if not meetings:
        st.info("No meetings on file yet. Generate or record one in the Voice tab.")
    else:
        st.caption(f"{len(meetings)} meeting(s) on file — newest first")
        for i, m in enumerate(meetings):
            label = m.get("_timestamp", f"Meeting {len(meetings) - i}")
            with st.expander(label):
                h_summary, h_actions, h_flags, h_email, h_notes = st.tabs(
                    ["Summary", "Action Items", "Planning Flags", "Follow-up Email", "Raw Notes"]
                )
                with h_summary:
                    md(m.get("summary", "—"))
                    accuracy_caption(m)
                with h_actions:
                    md(m.get("action_items", "—"))
                with h_flags:
                    md(m.get("flags", "—"))
                with h_email:
                    md(m.get("email", "—"))
                with h_notes:
                    st.text(m.get("notes", "—"))
