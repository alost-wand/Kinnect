import streamlit as st
from frontend.api_client import APIClient

def render():
    st.markdown("<h1 style='text-align: center;'>🏠 KINNECT</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Family Connectivity Platform — Secure & Private</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔒 Sign In", "📝 Create Account"])
        
        with tab1:
            st.subheader("Login to your Workspace")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Sign In", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    res = APIClient.post("/auth/login", json={"username": username, "password": password}, need_auth=False)
                    if res and res.status_code == 200:
                        data = res.json()
                        st.session_state.access_token = data.get("access_token")
                        st.session_state.family_id = data.get("family_id")
                        st.session_state.username = username
                        st.session_state.page = "workspace"
                        st.success("Successfully logged in!")
                        st.rerun()
                    elif res:
                        st.error(res.json().get("detail", "Invalid username or password."))
        
        with tab2:
            st.subheader("Register a new user")
            reg_username = st.text_input("Username", key="reg_username")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            
            if st.button("Create Account", use_container_width=True):
                if not reg_username or not reg_password:
                    st.error("Username and password are required.")
                else:
                    payload = {
                        "username": reg_username,
                        "password": reg_password,
                    }
                    if reg_email:
                        payload["email"] = reg_email
                    res = APIClient.post("/auth/register", json=payload, need_auth=False)
                    if res and res.status_code == 201:
                        st.success("Account created successfully! Please sign in.")
                    elif res:
                        st.error(res.json().get("detail", "Registration failed."))
