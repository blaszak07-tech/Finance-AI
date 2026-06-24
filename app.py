import streamlit as st
from src.chain import run_chain
from src.simulator import run_simulation
from src.storage import save_meeting, load_meetings, list_clients, rename_client, delete_client
from src.profile import profile_summary


def md(text: str) -> None:
    """Render AI-generated markdown, escaping $ so Streamlit doesn't treat them as LaTeX."""
    st.markdown(text.replace("$", r"\$"))

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

tab_new, tab_simulate, tab_history = st.tabs(["New Meeting", "Simulate", "History"])

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
with tab_simulate:
    st.caption("Configure a client persona and generate a realistic meeting transcript automatically.")

    col1, col2 = st.columns(2)
    with col1:
        sim_name = st.text_input("Client name", value=display_name, key="sim_name")
        sim_age = st.number_input("Age", min_value=25, max_value=85, value=50, key="sim_age")
        sim_risk = st.selectbox("Risk tolerance", ["Conservative", "Moderate", "Aggressive"], index=1, key="sim_risk")
    with col2:
        sim_personality = st.selectbox(
            "Personality",
            ["Cooperative and trusting", "Skeptical and cautious", "Anxious and risk-averse", "Analytical and detail-oriented", "Decisive and confident"],
            key="sim_personality",
        )
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
