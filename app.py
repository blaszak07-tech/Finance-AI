import streamlit as st
from src.chain import run_chain
from src.storage import save_meeting, load_meetings, list_clients, rename_client, delete_client
from src.profile import profile_summary

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

tab_new, tab_history = st.tabs(["New Meeting", "History"])

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
            st.markdown(result["summary"])
        with r_actions:
            st.markdown(result["action_items"])
        with r_flags:
            st.markdown(result["flags"])
        with r_email:
            st.markdown(result["email"])
            st.divider()
            st.download_button(
                "Download email as .txt",
                data=result["email"],
                file_name=f"{client_id}_followup.txt",
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
                    st.markdown(m.get("summary", "—"))
                with h_actions:
                    st.markdown(m.get("action_items", "—"))
                with h_flags:
                    st.markdown(m.get("flags", "—"))
                with h_email:
                    st.markdown(m.get("email", "—"))
                with h_notes:
                    st.text(m.get("notes", "—"))
