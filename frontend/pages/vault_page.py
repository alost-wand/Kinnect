import streamlit as st
from frontend.api_client import APIClient

def render():
    st.title("🗄️ Secure Document Vault")
    st.caption("Encrypted storage with session-based access control")

    # ─────────────────────────────
    # LOGIN / UNLOCK STATE
    # ─────────────────────────────
    if not st.session_state.get("vault_token"):

        st.subheader("🔐 Unlock Vault")

        q_res = APIClient.get("/vault/question")

        if not q_res or q_res.status_code != 200:
            st.warning("No security questions configured.")
            return

        question = q_res.json()

        st.write(f"**Security Question:** {question.get('question')}")

        sec_answer = st.text_input("Security Answer", type="password")
        vault_password = st.text_input("Vault Password", type="password")

        if st.button("Unlock Vault", use_container_width=True):

            payload = {
                "vault_password": vault_password,
                "question_id": question["question_id"],
                "security_answer": sec_answer
            }

            res = APIClient.post("/vault/unlock", json=payload)

            if res and res.status_code == 200:
                data = res.json()
                st.session_state.vault_token = data["session_token"]
                st.session_state.vault_password = vault_password
                st.rerun()
            else:
                st.error(res.json().get("detail", "Unlock failed"))

        return

    # ─────────────────────────────
    # ACTIVE VAULT
    # ─────────────────────────────
    st.success("🔓 Vault Active")

    if st.button("🔒 Lock Vault"):
        APIClient.post(f"/vault/lock?vault_token={st.session_state.vault_token}")
        st.session_state.vault_token = None
        st.session_state.vault_password = None
        st.rerun()

    st.divider()

    tab1, tab2 = st.tabs(["📂 Files", "📤 Upload"])

    # ─────────────────────────────
    # TAB 1: FILE LIST
    # ─────────────────────────────
    with tab1:

        category = st.selectbox(
            "Filter",
            ["All Files", "IDs", "Medical", "Legal", "Insurance", "Other"]
        )

        res = APIClient.get(
            "/vault/documents",
            params={
                "vault_token": st.session_state.vault_token,
                "category": category
            }
        )

        if not res or res.status_code != 200:
            st.error("Failed to load documents")
            return

        docs = res.json().get("documents", [])

        if not docs:
            st.info("No documents found")
            return

        for doc in docs:

            # SAFE ACCESS (prevents crashes)
            doc_id = doc.get("doc_id")
            file_name = doc.get("file_name", "Unknown")
            category = doc.get("category", "Unknown")
            uploaded_at = doc.get("uploaded_at", "")

            if not doc_id:
                continue

            with st.container(border=True):

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.write(f"📄 **{file_name}**")
                    st.caption(f"{category} | {uploaded_at}")

                with col2:

                    # DOWNLOAD (safe link)
                    dl = (
                        f"http://localhost:8000/vault/download/{doc_id}"
                        f"?vault_token={st.session_state.vault_token}"
                        f"&vault_password={st.session_state.vault_password}"
                    )

                    st.markdown(
                        f"<a href='{dl}' target='_blank'>"
                        "<button style='width:100%'>Download</button>"
                        "</a>",
                        unsafe_allow_html=True
                    )

                    # DELETE (FIXED + ALWAYS VISIBLE)
                    if st.button("Delete", key=f"del_{doc_id}"):

                        del_res = APIClient.delete(
                            f"/vault/{doc_id}",
                            params={"vault_token": st.session_state.vault_token}
                        )

                        if del_res and del_res.status_code in [200, 204]:
                            st.success("Deleted")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                            if del_res:
                                st.write(del_res.text)

    # ─────────────────────────────
    # TAB 2: UPLOAD
    # ─────────────────────────────
    with tab2:

        file = st.file_uploader("Choose file")

        category = st.selectbox(
            "Category",
            ["IDs", "Medical", "Legal", "Insurance", "Other"]
        )

        if st.button("Upload", use_container_width=True):

            if not file:
                st.error("Select a file first")
                return

            files = {
                "file": (file.name, file.getvalue(), file.type)
            }

            data = {
                "vault_token": st.session_state.vault_token,
                "vault_password": st.session_state.vault_password,
                "category": category
            }

            res = APIClient.post("/vault/upload", data=data, files=files)

            if res and res.status_code == 201:
                st.success("Uploaded")
                st.rerun()
            else:
                st.error("Upload failed")
                if res:
                    st.write(res.text)