"""frontend/app.py — KINNECT Streamlit main entry point."""
import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


st.set_page_config(
    page_title="KINNECT",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────
for key, default in {
    "access_token": None,
    "username": None,
    "family_id": None,
    "page": "login",
    "vault_token": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Dynamic page imports ──────────────────────────────────────
from frontend.pages import (
    login_page,
    workspace_page,
    timeline_page,
    health_page,
    emergency_page,
    vault_page,
    privacy_page,
)

# ── Sidebar nav (only when logged in) ─────────────────────────
if st.session_state.access_token:
    st.sidebar.title("🏠 KINNECT")
    st.sidebar.markdown(f"**{st.session_state.username}**")
    if st.session_state.family_id:
        st.sidebar.caption(f"Family: `{st.session_state.family_id[:8]}…`")

    pages = {
        "🏡 Workspace": "workspace",
        "📅 Timeline": "timeline",
        "💓 Health": "health",
        "🚨 Emergency": "emergency",
        "🗄️ Secure Vault": "vault",
        "🛡️ AI Privacy": "privacy",
    }
    for label, key in pages.items():
        if st.sidebar.button(label, use_container_width=True):
            st.session_state.page = key

    st.sidebar.divider()
    if st.sidebar.button("🚪 Log Out", use_container_width=True):
        for k in ["access_token", "username", "family_id", "vault_token"]:
            st.session_state[k] = None
        st.session_state.page = "login"
        st.rerun()

# ── Page routing ──────────────────────────────────────────────
page = st.session_state.page

if not st.session_state.access_token:
    login_page.render()
elif page == "workspace":
    workspace_page.render()
elif page == "timeline":
    timeline_page.render()
elif page == "health":
    health_page.render()
elif page == "emergency":
    emergency_page.render()
elif page == "vault":
    vault_page.render()
elif page == "privacy":
    privacy_page.render()
else:
    workspace_page.render()
