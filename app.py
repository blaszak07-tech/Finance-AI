import streamlit as st
from src.chain import run_chain
from src.storage import save_meeting, list_clients
from src.profile import profile_summary

st.set_page_config(page_title="WM Meeting Assistant", layout="wide")

st.title("Wealth Management Meeting Assistant")
st.caption("Paste meeting notes → get structured output instantly")

# --- Sidebar: client selection ---
st.sidebar.header("Client")
existing_clients = list_clients()

client_mode = st.sidebar.radio("", ["Existing client", "New client"], label_visibility="collapsed")

if client_mode == "New client":
    raw_name = st.sidebar.text_input("Client name", placeholder="e.g. John Smith")
    client_id = raw_name.strip().lower().replace(" ", "_") if raw_name else ""
else:
    if existing_clients:
        selected = st.sidebar.selectbox("Select client", existing_clients)
        client_id = selected
    else:
        st.sidebar.info("No clients yet. Switch to New client.")
        client_id = ""

# Show existing profile if there is one
if client_id:
    summary = profile_summary(client_id)
    if summary != "No prior profile on file for this client.":
        with st.sidebar.expander("Known profile"):
            st.text(summary)

st.sidebar.divider()
st.sidebar.caption("Finance AI — V1")

# --- Main area ---
notes = st.text_area(
    "Meeting notes",
    height=220,
    placeholder="Paste raw meeting notes or a transcript here...",
)

run = st.button("Run", type="primary", disabled=not (client_id and notes.strip()))

if not client_id:
    st.info("Select or create a client in the sidebar to get started.")

# --- Results ---
if run:
    with st.spinner("Running through Haiku..."):
        result = run_chain(client_id, notes)
        save_meeting(client_id, {"notes": notes, **result})

    st.success("Done")

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
