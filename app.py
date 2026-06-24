import streamlit as st
from src.chain import run_chain
from src.simulator import run_simulation, random_persona, ai_opening_line, ai_reply
from src.storage import save_meeting, load_meetings, list_clients, rename_client, delete_client
from src.profile import profile_summary


def md(text: str) -> None:
    """Render AI-generated markdown, escaping $ so Streamlit doesn't treat them as LaTeX."""
    st.markdown(text.replace("$", r"\$"))


def transcript_from(messages: list[dict]) -> str:
    """Turn a list of {role, text} messages into a plain-text transcript."""
    return "\n\n".join(f"{m['role']}: {m['text']}" for m in messages)

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
st.sidebar.caption("Finance AI — V1")

# --- Main area ---
if not client_id:
    st.info("Select or create a client in the sidebar to get started.")
    st.stop()

st.subheader(display_name)

tab_new, tab_simulate, tab_live, tab_history = st.tabs(
    ["New Meeting", "Simulate", "Live Meeting", "History"]
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

# ── Simulate ─────────────────────────────────────────────────
def _fill_random_persona():
    p = random_persona()
    st.session_state.sim_age = p["age"]
    st.session_state.sim_risk = p["risk"]
    st.session_state.sim_personality = p["personality"]
    st.session_state.sim_situation = p["situation"]
    st.session_state.sim_concerns = p["concerns"]


RISK_OPTIONS = ["Conservative", "Moderate", "Aggressive"]
PERSONALITY_OPTIONS = [
    "Cooperative and trusting", "Skeptical and cautious", "Anxious and risk-averse",
    "Analytical and detail-oriented", "Decisive and confident",
]

with tab_simulate:
    st.caption("Configure a client persona and generate a realistic meeting transcript automatically.")

    # Initialize defaults once so the random button can overwrite them without warnings
    st.session_state.setdefault("sim_age", 50)
    st.session_state.setdefault("sim_risk", "Moderate")
    st.session_state.setdefault("sim_personality", PERSONALITY_OPTIONS[0])
    st.session_state.setdefault("sim_situation", "")
    st.session_state.setdefault("sim_concerns", "")

    st.button("🎲 Generate random persona", on_click=_fill_random_persona, key="sim_random")

    col1, col2 = st.columns(2)
    with col1:
        sim_name = st.text_input("Client name", value=display_name, key="sim_name")
        sim_age = st.number_input("Age", min_value=25, max_value=85, key="sim_age")
        sim_risk = st.selectbox("Risk tolerance", RISK_OPTIONS, key="sim_risk")
    with col2:
        sim_personality = st.selectbox("Personality", PERSONALITY_OPTIONS, key="sim_personality")
        sim_exchanges = st.slider("Conversation length (exchanges)", min_value=2, max_value=6, value=3, key="sim_exchanges")

    sim_situation = st.text_area(
        "Client situation",
        placeholder="e.g. Software executive, recently sold startup equity, net worth around 4M. Wife is a doctor.",
        height=80,
        key="sim_situation",
    )
    sim_concerns = st.text_area(
        "Key concerns to seed the conversation",
        placeholder="e.g. Worried about taxes from the liquidity event, wants to retire by 58",
        height=80,
        key="sim_concerns",
    )

    sim_ready = all([sim_name.strip(), sim_situation.strip(), sim_concerns.strip()])
    if st.button("Generate transcript", type="primary", disabled=not sim_ready, key="sim_btn"):
        with st.spinner("Simulating conversation..."):
            st.session_state.sim_transcript = run_simulation(
                name=sim_name.strip(),
                age=int(sim_age),
                situation=sim_situation.strip(),
                risk_tolerance=sim_risk.lower(),
                personality=sim_personality.lower(),
                concerns=sim_concerns.strip(),
                num_exchanges=int(sim_exchanges),
            )

    # Persisted transcript (survives reruns so the pipeline button works)
    transcript = st.session_state.get("sim_transcript")
    if transcript:
        st.subheader("Generated transcript")
        st.text(transcript)
        st.divider()

        if st.button("Run pipeline on this transcript", type="primary", key="sim_run_chain"):
            with st.spinner("Running through Haiku..."):
                result = run_chain(client_id, transcript)
                save_meeting(client_id, {"notes": transcript, **result})

            st.success("Done — meeting saved to history")

            new_facts = result.get("new_profile_facts", {})
            if new_facts:
                with st.expander(f"Profile updated — {len(new_facts)} new fact(s) learned", expanded=True):
                    for k, v in new_facts.items():
                        st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

            s_summary, s_actions, s_flags, s_email = st.tabs(
                ["Summary", "Action Items", "Planning Flags", "Follow-up Email"]
            )
            with s_summary:
                md(result["summary"])
            with s_actions:
                md(result["action_items"])
            with s_flags:
                md(result["flags"])
            with s_email:
                md(result["email"])
                st.divider()
                st.download_button(
                    "Download email as .txt",
                    data=result["email"],
                    file_name=f"{client_id}_simulated_followup.txt",
                    mime="text/plain",
                )

# ── Live Meeting (human-in-the-loop) ─────────────────────────
def _fill_random_persona_hil():
    p = random_persona()
    st.session_state.hil_age = p["age"]
    st.session_state.hil_risk = p["risk"]
    st.session_state.hil_personality = p["personality"]
    st.session_state.hil_situation = p["situation"]
    st.session_state.hil_concerns = p["concerns"]


_HIL_KEYS = ["hil_active", "hil_messages", "hil_human_role", "hil_ai_role", "hil_persona", "hil_client"]

with tab_live:
    # If the selected client changed mid-conversation, drop the live session
    if st.session_state.get("hil_active") and st.session_state.get("hil_client") != client_id:
        for k in _HIL_KEYS:
            st.session_state.pop(k, None)

    if not st.session_state.get("hil_active"):
        st.caption("Have a real back-and-forth — you play one side, the AI plays the other. End it whenever and run the pipeline on the conversation.")

        human_role = st.radio("You play the…", ["Advisor", "Client"], horizontal=True, key="hil_role_choice")

        if human_role == "Advisor":
            st.markdown(f"The AI plays **{display_name}** (the client). Set their persona:")
            st.session_state.setdefault("hil_age", 50)
            st.session_state.setdefault("hil_risk", "Moderate")
            st.session_state.setdefault("hil_personality", PERSONALITY_OPTIONS[0])
            st.session_state.setdefault("hil_situation", "")
            st.session_state.setdefault("hil_concerns", "")

            st.button("🎲 Random client persona", on_click=_fill_random_persona_hil, key="hil_random")
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("Age", min_value=25, max_value=85, key="hil_age")
                st.selectbox("Risk tolerance", RISK_OPTIONS, key="hil_risk")
            with c2:
                st.selectbox("Personality", PERSONALITY_OPTIONS, key="hil_personality")
            st.text_area("Client situation", height=80, key="hil_situation")
            st.text_area("Key concerns", height=80, key="hil_concerns")

            ready = bool(st.session_state.hil_situation.strip() and st.session_state.hil_concerns.strip())
        else:
            st.markdown("The AI plays the **advisor**. You speak as the client — just talk naturally.")
            ready = True

        if st.button("Start meeting", type="primary", disabled=not ready, key="hil_start"):
            st.session_state.hil_human_role = human_role
            st.session_state.hil_ai_role = "Client" if human_role == "Advisor" else "Advisor"
            st.session_state.hil_client = client_id
            st.session_state.hil_messages = []

            if human_role == "Advisor":
                st.session_state.hil_persona = {
                    "name": display_name,
                    "age": int(st.session_state.hil_age),
                    "situation": st.session_state.hil_situation.strip(),
                    "risk_tolerance": st.session_state.hil_risk.lower(),
                    "personality": st.session_state.hil_personality.lower(),
                    "concerns": st.session_state.hil_concerns.strip(),
                }
            else:
                st.session_state.hil_persona = None
                with st.spinner("Starting the meeting…"):
                    opening = ai_opening_line("Advisor")
                st.session_state.hil_messages.append({"role": "Advisor", "text": opening})

            st.session_state.hil_active = True
            st.rerun()

    else:
        human_role = st.session_state.hil_human_role
        ai_role = st.session_state.hil_ai_role
        messages = st.session_state.hil_messages

        st.markdown(f"**You:** {human_role}  ·  **AI:** {ai_role}  ·  **Client:** {display_name}")

        for m in messages:
            who = "user" if m["role"] == human_role else "assistant"
            with st.chat_message(who):
                st.markdown(f"**{m['role']}**")
                md(m["text"])

        with st.form("hil_form", clear_on_submit=True):
            user_text = st.text_input(f"Your message as the {human_role.lower()}")
            sent = st.form_submit_button("Send")

        if sent and user_text.strip():
            messages.append({"role": human_role, "text": user_text.strip()})
            with st.spinner(f"{ai_role} is responding…"):
                reply = ai_reply(ai_role, transcript_from(messages), st.session_state.hil_persona)
            messages.append({"role": ai_role, "text": reply})
            st.session_state.hil_messages = messages
            st.rerun()

        col_end, col_reset = st.columns(2)
        with col_end:
            end = st.button("End & run pipeline", type="primary", disabled=len(messages) < 2, key="hil_end")
        with col_reset:
            if st.button("Reset conversation", key="hil_reset"):
                for k in _HIL_KEYS:
                    st.session_state.pop(k, None)
                st.rerun()

        if end:
            transcript = transcript_from(messages)
            with st.spinner("Running through Haiku…"):
                result = run_chain(client_id, transcript)
                save_meeting(client_id, {"notes": transcript, **result})
            st.success("Done — meeting saved to history")

            new_facts = result.get("new_profile_facts", {})
            if new_facts:
                with st.expander(f"Profile updated — {len(new_facts)} new fact(s) learned", expanded=True):
                    for k, v in new_facts.items():
                        st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

            l_summary, l_actions, l_flags, l_email = st.tabs(
                ["Summary", "Action Items", "Planning Flags", "Follow-up Email"]
            )
            with l_summary:
                md(result["summary"])
            with l_actions:
                md(result["action_items"])
            with l_flags:
                md(result["flags"])
            with l_email:
                md(result["email"])


# ── History ──────────────────────────────────────────────────
with tab_history:
    meetings = load_meetings(client_id)

    if not meetings:
        st.info("No meetings on file yet. Run one from the New Meeting tab.")
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
                with h_actions:
                    md(m.get("action_items", "—"))
                with h_flags:
                    md(m.get("flags", "—"))
                with h_email:
                    md(m.get("email", "—"))
                with h_notes:
                    st.text(m.get("notes", "—"))
