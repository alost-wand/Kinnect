import streamlit as st
import pandas as pd
from datetime import date
from frontend.api_client import APIClient


def render():
    st.title("🧠 Kinnect Health Intelligence Dashboard")
    st.caption("Family wellness tracking powered by AI insights")

    tab1, tab2, tab3 = st.tabs([
        "📊 Live Dashboard",
        "🤖 AI Health Reports",
        "📥 Ingest Data"
    ])

    # ─────────────────────────────
    # TAB 1 — DASHBOARD
    # ─────────────────────────────
    with tab1:
        st.subheader("Family Health Overview")

        res = APIClient.get("/health/dashboard")

        if not res or res.status_code != 200:
            st.error("Failed to load dashboard")
            return

        data = res.json()
        members = data.get("members") or []

        if not members:
            st.info("No data available yet. Please ingest wearable data.")
            return

        cols = st.columns(len(members))

        for i, m in enumerate(members):
            with cols[i]:
                st.markdown(f"### 👤 {m.get('username', 'Member')}")

                score = m.get("lifestyle_score", 0)

                if score >= 80:
                    st.success(f"🟢 Score: {score}/100")
                elif score >= 60:
                    st.warning(f"🟡 Score: {score}/100")
                else:
                    st.error(f"🔴 Score: {score}/100")

                st.metric("❤️ Heart Rate", f"{m.get('heart_rate', 0)} bpm")
                st.metric("🚶 Steps", f"{m.get('step_count', 0)}")
                st.metric("💧 Hydration", f"{m.get('hydration_ml', 0)} ml")
                st.metric("📱 Screen Time", f"{m.get('screen_minutes', 0)} min")

                if m.get("has_anomaly"):
                    st.error("⚠️ Health anomaly detected")

                st.divider()

        # ───── Trend Section ─────
        st.subheader("📈 Family Trend Snapshot")

        user = members[0]["user_id"]
        trend = APIClient.get(f"/health/sparklines/{user}")

        if trend and trend.status_code == 200:
            try:
                df = pd.DataFrame(trend.json().get("sparklines", []))

                if not df.empty:
                    df = df.rename(columns={
                        "recorded_date": "Date",
                        "heart_rate": "Heart Rate",
                        "step_count": "Steps",
                        "sleep_minutes": "Sleep"
                    }).set_index("Date")

                    st.line_chart(df, height=250)

            except Exception as e:
                st.warning(f"Trend chart error: {e}")

    # ─────────────────────────────
    # TAB 2 — AI REPORTS
    # ─────────────────────────────
    with tab2:
        st.subheader("🤖 AI Health Intelligence")

        dash_res = APIClient.get("/health/dashboard")

        if not dash_res or dash_res.status_code != 200:
            st.error("Unable to load family members")
            return

        members = dash_res.json().get("members") or []

        if not members:
            st.warning("No family members found")
            return

        # SAFE SELECTBOX (FIXED)
        member_map = {
            f"{m.get('username')} ({m.get('user_id')})": m
            for m in members
        }

        selected_label = st.selectbox(
            "Select Family Member",
            list(member_map.keys())
        )

        selected_member = member_map[selected_label]
        selected_user_id = selected_member["user_id"]

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📅 Generate Daily Report", use_container_width=True):
                with st.spinner("Generating daily report..."):
                    res = APIClient.get(f"/health/ai/daily/{selected_user_id}")

                    if not res or res.status_code != 200:
                        st.error("Daily report failed")
                    else:
                        try:
                            payload = res.json()
                            report = payload.get("report")

                            if report:
                                st.markdown("### 🧾 Daily Report")
                                st.success(report)
                            else:
                                st.warning("No report returned")
                        except Exception:
                            st.error(res.text)

        with col2:
            if st.button("📊 Generate Weekly Report", use_container_width=True):
                with st.spinner("Generating weekly report..."):
                    res = APIClient.get(f"/health/ai/weekly/{selected_user_id}")

                    if not res or res.status_code != 200:
                        st.error("Weekly report failed")
                    else:
                        try:
                            payload = res.json()
                            report = payload.get("report")

                            if report:
                                st.markdown("### 📈 Weekly Report")
                                st.success(report)
                            else:
                                st.warning("No report returned")
                        except Exception:
                            st.error(res.text)

        st.markdown("---")
        st.json({
            "username": selected_member.get("username"),
            "user_id": selected_member.get("user_id"),
            "heart_rate": selected_member.get("heart_rate"),
            "steps": selected_member.get("step_count"),
            "sleep": selected_member.get("sleep_minutes"),
            "hydration": selected_member.get("hydration_ml"),
        })

    # ─────────────────────────────
    # TAB 3 — INGEST
    # ─────────────────────────────
    with tab3:
        st.subheader("📥 Simulated Wearable Data Input")
        dash_res = APIClient.get("/health/dashboard")

        members = []

        if dash_res and dash_res.status_code == 200:
            members = dash_res.json().get("members", [])

        if members:
            selected_member = st.selectbox(
                "Family Member",
                members,
                format_func=lambda m: m["username"]
            )

            user_id = selected_member["user_id"]

            st.caption(f"User ID: {user_id}")
        else:
            st.error("No family members found")
            return

        col1, col2 = st.columns(2)

        with col1:
            heart_rate = st.slider("Heart Rate (bpm)", 50, 200, 72)
            step_count = st.slider("Steps", 0, 20000, 8000)
            sleep_minutes = st.slider("Sleep (minutes)", 0, 900, 480)

        with col2:
            hydration_ml = st.slider("Hydration (ml)", 0, 5000, 2000)
            screen_minutes = st.slider("Screen Time (minutes)", 0, 900, 180)
            recorded_date = st.date_input("Date", date.today())

        if st.button("🚀 Submit Health Data", use_container_width=True):
            payload = {
                "user_id": user_id,
                "heart_rate": heart_rate,
                "step_count": step_count,
                "sleep_minutes": sleep_minutes,
                "hydration_ml": hydration_ml,
                "screen_minutes": screen_minutes,
                "recorded_date": recorded_date.isoformat()
            }

            res = APIClient.post("/health/ingest", json=payload)
            if res and res.status_code == 200:
                data = res.json()
                st.success("Data submitted successfully")

                if data.get("anomaly"):
                    st.warning("⚠️ Anomaly detected!")
            else:
                st.error("Ingest failed")
