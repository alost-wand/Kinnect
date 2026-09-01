import streamlit as st
import json
from frontend.api_client import APIClient


def render():
    st.title("🛡️ AI Privacy Shield")

    st.caption("Protect family photos before sharing — remove sensitive data automatically.")

    uploaded_file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png", "webp", "heic"]
    )

    if not uploaded_file:
        return

    image_bytes = uploaded_file.getvalue()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Original")
        st.image(image_bytes)

    with col2:
        st.subheader("Controls")

        blur_targets = st.checkbox("Blur Sensitive Objects", value=True)
        adversarial_noise = st.checkbox("Privacy Noise Layer", value=True)

        run = st.button("Protect Image 🚀")

    if run:
        with st.spinner("Applying privacy protection..."):

            files = {
                "file": (
                    uploaded_file.name,
                    image_bytes,
                    uploaded_file.type or "application/octet-stream",
                )
            }

            data = {
                "blur_targets": str(blur_targets),
                "adversarial_noise": str(adversarial_noise),
                "use_pgd": "false",
            }

            res = APIClient.post(
                "/privacy/protect",
                data=data,
                files=files,
            )

            if not res:
                st.error("Backend not responding")
                return

            if res.status_code != 200:
                st.error(res.text)
                return

            st.session_state["protected_image"] = res.content

            # safe header parsing
            try:
                st.session_state["privacy_report"] = json.loads(
                    res.headers.get("X-Privacy-Report", "{}")
                )
            except Exception:
                st.session_state["privacy_report"] = {}

            st.success("Privacy protection applied!")

    # ─────────────────────────────
    # OUTPUT
    # ─────────────────────────────

    if "protected_image" in st.session_state:
        st.subheader("Protected Image")
        st.image(st.session_state["protected_image"])

        st.download_button(
            "Download",
            st.session_state["protected_image"],
            file_name=f"protected_{uploaded_file.name}",
            mime="image/jpeg",
        )

    if "privacy_report" in st.session_state:
        st.subheader("Privacy Report")

        report = st.session_state["privacy_report"]

        st.json(report)

        col1, col2, col3 = st.columns(3)

        col1.metric("Faces", report.get("faces_detected", 0))
        col2.metric("Text Regions", report.get("text_regions_detected", 0))
        col3.metric("Objects", report.get("objects_detected", 0))

        st.progress(min(report.get("privacy_risk_after", 0) / 100, 1.0))