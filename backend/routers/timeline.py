"""backend/routers/timeline.py — Module 2: Shared Timeline
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from backend.database import DB
from backend.models.schemas import EventCreate, EventUpdate
from backend.utils.auth import require_family
from backend.utils.ws_manager import ws_manager
from datetime import datetime, timedelta

router = APIRouter(prefix="/timeline", tags=["Timeline"])


# -------------------------
# WebSocket (unchanged)
# -------------------------

@router.websocket("/ws/{family_id}/{user_id}")
async def timeline_ws(ws: WebSocket, family_id: str, user_id: str):
    await ws_manager.connect(ws, family_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, family_id)


# -------------------------
# LIST EVENTS
# -------------------------

@router.get("/")
async def list_events(
    view: str = "month",
    start: str | None = None,
    end: str | None = None,
    user=Depends(require_family),
):

    family_id = user["family_id"]

    async with DB() as cur:
        query = """
            SELECT e.*, u.username AS creator_name
            FROM timeline_events e
            JOIN users u ON u.user_id = e.created_by
            WHERE e.family_id = %s
        """
        params = [family_id]

        if start:
            query += " AND e.start_time >= %s"
            params.append(start)

        if end:
            query += " AND e.start_time <= %s"
            params.append(end)

        query += " ORDER BY e.start_time ASC"

        await cur.execute(query, params)
        events = await cur.fetchall()

    # privacy rules
    caller_id = user["sub"]
    result = []

    for ev in events:
        if ev["visibility"] == "private" and ev["created_by"] != caller_id:
            ev["title"] = "🔒 Private"
            ev["description"] = None

        result.append(ev)

    return {"events": result}


# -------------------------
# CREATE EVENT (WITH RECURSION)
# -------------------------

def generate_recurrence_dates(start_dt, recurrence, limit=30):
    """MVP recurrence generator"""
    dates = [start_dt]

    if recurrence == "none" or not recurrence:
        return dates

    for i in range(limit):
        if recurrence == "daily":
            start_dt += timedelta(days=1)
        elif recurrence == "weekly":
            start_dt += timedelta(weeks=1)
        else:
            break

        dates.append(start_dt)

    return dates


@router.post("/", status_code=201)
async def add_event(payload: EventCreate, user=Depends(require_family)):

    family_id = user["family_id"]
    event_id = str(uuid.uuid4())

    start_dt = datetime.fromisoformat(payload.start_time)
    end_dt = datetime.fromisoformat(payload.end_time) if payload.end_time else None

    async with DB() as cur:

        for i, rec_start in enumerate(generate_recurrence_dates(start_dt, payload.recurrence)):

            rec_end = None
            if end_dt:
                delta = end_dt - start_dt
                rec_end = rec_start + delta

            await cur.execute(
                """
                INSERT INTO timeline_events
                (event_id, family_id, created_by, title, description,
                 event_type, start_time, end_time, visibility, alarm_config)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(uuid.uuid4()),
                    family_id,
                    user["sub"],
                    payload.title,
                    payload.description,
                    payload.event_type,
                    rec_start,
                    rec_end,
                    payload.visibility,
                    payload.recurrence
                ),
            )

    await ws_manager.broadcast(family_id, {
        "type": "event_added",
        "event_id": event_id
    })

    return {"message": "Event(s) created"}


# -------------------------
# PATCH (FIXED SAFE)
# -------------------------

@router.patch("/{event_id}")
async def update_event(event_id: str, payload: EventUpdate, user=Depends(require_family)):

    family_id = user["family_id"]

    updates, params = [], []

    if payload.is_completed is not None:
        updates.append("is_completed=%s")
        params.append(payload.is_completed)

    if payload.visibility is not None:
        updates.append("visibility=%s")
        params.append(payload.visibility)

    if payload.start_time is not None:
        updates.append("start_time=%s")
        params.append(payload.start_time)

    if payload.end_time is not None:
        updates.append("end_time=%s")
        params.append(payload.end_time)

    if not updates:
        raise HTTPException(status_code=400, detail="No update fields provided")

    params += [event_id, family_id]

    async with DB() as cur:
        await cur.execute(
            f"""
            UPDATE timeline_events
            SET {', '.join(updates)}
            WHERE event_id=%s AND family_id=%s
            """,
            params
        )

    return {"message": "updated"}


# -------------------------
# DELETE
# -------------------------

@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str, user=Depends(require_family)):

    family_id = user["family_id"]

    async with DB() as cur:
        await cur.execute(
            "DELETE FROM timeline_events WHERE event_id=%s AND family_id=%s",
            (event_id, family_id),
        )

    return None