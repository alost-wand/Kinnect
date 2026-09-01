import streamlit as st
from frontend.api_client import APIClient

def render():
    st.title("🏡 Family Workspace")
    
    if not st.session_state.family_id:
        st.info("You are not currently in a family workspace. Create a workspace or accept a pending invite to get started.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Create a Workspace")
            family_name = st.text_input("Family Name")
            if st.button("Create Workspace", type="primary"):
                if not family_name:
                    st.error("Please enter a family name.")
                else:
                    res = APIClient.post("/auth/workspace/create", json={"family_name": family_name})
                    if res and res.status_code == 200:
                        data = res.json()
                        st.session_state.family_id = data.get("family_id")
                        st.session_state.access_token = data.get("access_token")
                        st.success("Workspace created successfully!")
                        st.rerun()
                    elif res:
                        st.error(res.json().get("detail", "Failed to create workspace."))
                        
        with col2:
            st.subheader("Pending Invites")
            res = APIClient.get("/auth/invites/pending")
            if res and res.status_code == 200:
                invites = res.json().get("invites", [])
                if not invites:
                    st.write("No pending invites.")
                for invite in invites:
                    with st.container(border=True):
                        st.write(f"Invite to join **{invite['family_name']}**")
                        st.caption(f"Received at: {invite['created_at']}")
                        if st.button("Accept", key=f"accept_{invite['invite_id']}", type="primary"):
                            accept_res = APIClient.post("/auth/workspace/accept", json={"invite_id": invite['invite_id']})
                            if accept_res and accept_res.status_code == 200:
                                accept_data = accept_res.json()
                                st.session_state.family_id = accept_data.get("family_id")
                                st.session_state.access_token = accept_data.get("access_token")
                                st.success("Joined workspace successfully!")
                                st.rerun()
                            elif accept_res:
                                st.error(accept_res.json().get("detail", "Failed to accept invite."))
    else:
        st.success(f"You are connected to family workspace ID: `{st.session_state.family_id}`")
        
        st.subheader("Invite a Member")
        invite_username = st.text_input("Enter member username to invite")
        if st.button("Send Invitation", type="primary"):
            if not invite_username:
                st.error("Please enter a username.")
            else:
                res = APIClient.post("/auth/workspace/invite", json={"target_username": invite_username})
                if res and res.status_code == 200:
                    st.success(f"Invitation sent to **{invite_username}** successfully!")
                elif res:
                    st.error(res.json().get("detail", "Failed to send invitation."))
