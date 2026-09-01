import streamlit as st
from datetime import datetime, date
from frontend.api_client import APIClient

try:
    from streamlit_calendar import calendar
    CALENDAR_AVAILABLE = True
except:
    CALENDAR_AVAILABLE = False


# =========================
# COLORS
# =========================
EVENT_COLORS = {
    "appointment": "#3b82f6",
    "chore": "#10b981",
    "milestone": "#8b5cf6",
    "reminder": "#f59e0b"
}


# =========================
# FORMAT EVENTS
# =========================
def format_events(events):
    return [
        {
            "title": e["title"],
            "start": e["start_time"],
            "end": e["end_time"] or e["start_time"],
            "color": EVENT_COLORS.get(e["event_type"], "#64748b"),
            "extendedProps": e
        }
        for e in events
    ]


# =========================
# LOAD EVENTS (SAFE)
# =========================
def load_events():
    try:
        res = APIClient.get("/timeline/")
        if res and res.status_code == 200:
            return res.json().get("events", [])
    except:
        pass
    return []


# =========================
# MAIN RENDER
# =========================
def render():

    st.title("📅 Family Timeline")

    # -------------------------
    # CACHE (NO RELOAD LOOP)
    # -------------------------
    if "events_cache" not in st.session_state:
        st.session_state.events_cache = load_events()

    events = st.session_state.events_cache

    # -------------------------
    # METRICS
    # -------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Events", len(events))
    c2.metric("Chores", len([e for e in events if e["event_type"] == "chore"]))
    c3.metric("Reminders", len([e for e in events if e["event_type"] == "reminder"]))

    st.divider()

    # -------------------------
    # LAYOUT
    # -------------------------
    col1, col2 = st.columns([3, 1])

    # =========================
    # CALENDAR
    # =========================
    with col1:

        if CALENDAR_AVAILABLE:

            cal = calendar(
                events=format_events(events),
                options={
                    "initialView": "dayGridMonth",
                    "height": 700,
                    "editable": False,          # 🔥 CRITICAL FIX
                    "selectable": False,        # 🔥 prevents rerun loops
                    "headerToolbar": {
                        "left": "prev,next today",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek,timeGridDay"
                    }
                },
                key="calendar"
            )

            # -------------------------
            # EVENT CLICK
            # -------------------------
            if cal and cal.get("eventClick"):
                ev = cal["eventClick"]["event"]["extendedProps"]

                st.subheader(ev["title"])
                st.caption(f"{ev['event_type']} • {ev.get('visibility','public')}")

                st.write("Start:", ev["start_time"])
                if ev.get("end_time"):
                    st.write("End:", ev["end_time"])

                st.write("---")

                colA, colB = st.columns(2)

                with colA:
                    if st.button("🗑 Delete"):
                        APIClient.delete(f"/timeline/{ev['event_id']}")

                        # update cache only (NO rerun)
                        st.session_state.events_cache = [
                            e for e in events if e["event_id"] != ev["event_id"]
                        ]

                with colB:
                    if ev["event_type"] == "chore":
                        if st.button("✅ Complete"):
                            APIClient.patch(
                                f"/timeline/{ev['event_id']}",
                                json={"is_completed": True}
                            )
                            st.session_state.events_cache = load_events()

        else:
            st.warning("Install streamlit-calendar for calendar view")

    # =========================
    # TODAY PANEL
    # =========================
    with col2:

        st.subheader("⚡ Today")

        today = date.today().isoformat()

        todays = [e for e in events if e["start_time"].startswith(today)]

        if not todays:
            st.info("No events today 🎉")

        for ev in todays:
            st.write(f"• {ev['title']} ({ev['event_type']})")

    st.divider()

    # =========================
    # CREATE EVENT
    # =========================
    st.subheader("➕ Create Event")

    title = st.text_input("Title")

    event_type = st.selectbox(
        "Type",
        ["appointment", "chore", "milestone", "reminder"]
    )

    visibility = st.selectbox(
        "Visibility",
        ["public", "private", "busy_only"]
    )

    start_date = st.date_input("Start Date")
    start_time = st.time_input("Start Time")

    end_date = st.date_input("End Date")
    end_time = st.time_input("End Time")

    description = st.text_area("Notes")

    start_dt = datetime.combine(start_date, start_time).isoformat()
    end_dt = datetime.combine(end_date, end_time).isoformat()

    if st.button("Create Event"):

        if not title:
            st.error("Title required")
            return

        payload = {
            "title": title,
            "description": description,
            "event_type": event_type,
            "start_time": start_dt,
            "end_time": end_dt,
            "visibility": visibility
        }

        res = APIClient.post("/timeline/", json=payload)

        if res and res.status_code == 201:
            st.session_state.events_cache = load_events()
            st.success("Event created 🎉")