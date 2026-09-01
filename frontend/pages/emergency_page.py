import streamlit as st
import pandas as pd
import urllib.request
import json
from streamlit_geolocation import streamlit_geolocation
from frontend.api_client import APIClient

SIREN_URL = "https://upload.wikimedia.org/wikipedia/commons/1/15/Emergency_siren.ogg"


@st.cache_data(ttl=86400, show_spinner=False)
def get_address_from_coords(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Kinnect-App'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            return data.get("display_name", f"{lat:.4f}, {lon:.4f}")
    except:
        return f"{lat:.4f}, {lon:.4f}"


def render():
    st.title("🚨 SOS Emergency System")

    # ── ACTIVE SOS ───────────────────────────────
    res = APIClient.get("/emergency/active")

    active = []
    if res and res.status_code == 200:
        active = res.json().get("active", [])

    if active:
        st.markdown(
            f"""
            <audio autoplay loop style="display:none;">
                <source src="{SIREN_URL}" type="audio/ogg">
            </audio>
            """,
            unsafe_allow_html=True
        )

    for item in active:
        address = get_address_from_coords(item["latitude"], item["longitude"])

        st.error(
            f"🚨 ACTIVE SOS\n\n"
            f"User: {item['activated_by']}\n"
            f"Location: {address}\n"
            f"[Open Maps](https://maps.google.com/?q={item['latitude']},{item['longitude']})"
        )

        if st.button("Resolve", key=item["sos_id"]):
            r = APIClient.post("/emergency/resolve", json={"sos_id": item["sos_id"]})
            if r and r.status_code == 200:
                st.success("Resolved")
            else:
                st.error("Failed")


    col1, col2 = st.columns([1.5, 2])

    # ── TRIGGER SOS ─────────────────────────────
    with col1:
        st.subheader("Trigger SOS")

        location = streamlit_geolocation()
        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat and lon:
            st.success(get_address_from_coords(lat, lon))
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))

            if st.button("🚨 TRIGGER SOS"):
                r = APIClient.post("/emergency/trigger", json={
                    "latitude": lat,
                    "longitude": lon
                })

                if r and r.status_code == 201:
                    st.error("SOS SENT")
                else:
                    st.error("Failed")

        else:
            st.warning("Enable location")

    # ── LOGS ───────────────────────────────
    with col2:
        st.subheader("Logs")

        logs = APIClient.get("/emergency/logs")
        if logs and logs.status_code == 200:
            for log in logs.json().get("logs", []):
                with st.container():
                    st.write(f"User: {log['activated_by']}")
                    st.write(f"Status: {log['status']}")
                    st.write(f"Time: {log['activated_at']}")