import streamlit as st
from src.chain import run_chain
from src.storage import save_meeting, list_clients, rename_client, delete_client
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

# Show existing profile if there is one
if client_id:
    summary = profile_summary(client_id)
    if summary != "No prior profile on file for this client.":
        with st.sidebar.expander("Known profile"):
            st.text(summary)

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

# Client confirmed — show who we're working with
st.subheader(f"Meeting notes — {display_name}")
st.caption("Profile builds automatically from meeting notes as you add them.")

notes = st.text_area(
    "Paste raw notes or a transcript",
    height=250,
    placeholder="e.g. John wants to retire at 60, worried about market volatility, daughter starting college in 2 years...",
    label_visibility="collapsed",
)

run = st.button("Run", type="primary", disabled=not notes.strip())

# --- Results ---
if run:
    with st.spinner("Running through Haiku..."):
        result = run_chain(client_id, notes)
        save_meeting(client_id, {"notes": notes, **result})

    st.success("Done — meeting saved to client history")

    new_facts = result.get("new_profile_facts", {})
    if new_facts:
        with st.expander(f"Profile updated — {len(new_facts)} new fact(s) learned", expanded=True):
            for k, v in new_facts.items():
                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

    tab_summary, tab_actions, tab_flags, tab_email = st.tabs(
        ["Summary", "Action Items", "Planning Flags", "Follow-up Email"]
    )

    with tab_summary:
        st.markdown(result["summary"])

    with tab_actions:
        st.markdown(result["action_items"])

    with tab_flags:
        st.markdown(result["flags"])

    with tab_email:
        st.markdown(result["email"])
        st.divider()
        st.download_button(
            "Download email as .txt",
            data=result["email"],
            file_name=f"{client_id}_followup.txt",
            mime="text/plain",
        )
