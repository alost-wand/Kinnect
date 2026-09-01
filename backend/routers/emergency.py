"""backend/routers/emergency.py — FIXED SOS SYSTEM"""

import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from backend.database import DB
from backend.models.schemas import SOSTrigger, SOSResolve
from backend.utils.auth import require_family
from backend.utils.ws_manager import ws_manager
from backend.config import get_settings

router = APIRouter(prefix="/emergency", tags=["SOS Emergency"])


# ─────────────────────────────────────────────
# SMS FALLBACK (FIXED SAFE VERSION)
# ─────────────────────────────────────────────
def _sms_fallback_sync(family_id: str, sender: str, lat: float, lon: float, sos_id: str):
    cfg = get_settings()

    if not cfg.twilio_account_sid or not cfg.twilio_auth_token:
        print("[KINNECT] Twilio not configured — SMS skipped.")
        return

    try:
        from twilio.rest import Client

        client = Client(cfg.twilio_account_sid, cfg.twilio_auth_token)

        maps_link = f"https://maps.google.com/?q={lat},{lon}"
        body = (
            f"🚨 SOS ALERT — {sender}\n"
            f"Location: {maps_link}\n"
            f"SOS ID: {sos_id}"
        )

        print(f"[KINNECT] SMS FALLBACK TRIGGERED: {body}")

    except Exception as e:
        print(f"[KINNECT] SMS error: {e}")


# ─────────────────────────────────────────────
# TRIGGER SOS
# ─────────────────────────────────────────────
@router.post("/trigger", status_code=201)
async def trigger_sos(
    payload: SOSTrigger,
    bg: BackgroundTasks,
    user=Depends(require_family),
):
    family_id = user["family_id"]
    sos_id = str(uuid.uuid4())

    async with DB() as cur:
        await cur.execute(
            """
            INSERT INTO emergency_events
            (sos_id, family_id, activated_by, latitude, longitude, status)
            VALUES (%s,%s,%s,%s,%s,'ACTIVE')
            """,
            (
                sos_id,
                family_id,
                user["sub"],
                payload.latitude,
                payload.longitude,
            ),
        )

    ws_payload = {
        "type": "SOS_ACTIVE",
        "sos_id": sos_id,
        "family_id": family_id,
        "activated_by": user.get("username", user["sub"]),
        "activated_by_id": user["sub"],
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "can_resolve": user["sub"],
    }

    await ws_manager.broadcast_emergency(family_id, ws_payload)

    bg.add_task(
        _sms_fallback_sync,
        family_id,
        user.get("username", user["sub"]),
        payload.latitude,
        payload.longitude,
        sos_id,
    )

    return {"message": "SOS triggered", "sos_id": sos_id}


# ─────────────────────────────────────────────
# RESOLVE SOS (FIXED)
# ─────────────────────────────────────────────
@router.post("/resolve")
async def resolve_sos(payload: SOSResolve, user=Depends(require_family)):

    async with DB() as cur:
        await cur.execute(
            """
            SELECT activated_by, status
            FROM emergency_events
            WHERE sos_id=%s AND family_id=%s
            """,
            (payload.sos_id, user["family_id"]),
        )
        sos = await cur.fetchone()

        if not sos:
            raise HTTPException(status_code=404, detail="SOS not found")

        if sos["status"] == "RESOLVED":
            return {"message": "Already resolved"}

        if sos["activated_by"] != user["sub"]:
            raise HTTPException(
                status_code=403,
                detail="Only SOS creator can resolve this"
            )

        await cur.execute(
            """
            UPDATE emergency_events
            SET status='RESOLVED'
            WHERE sos_id=%s AND family_id=%s
            """,
            (payload.sos_id, user["family_id"]),
        )

    await ws_manager.broadcast(
        user["family_id"],
        {
            "type": "SOS_RESOLVED",
            "sos_id": payload.sos_id,
            "resolved_by": user.get("username", user["sub"]),
        },
    )

    return {"message": "resolved"}


# ─────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────
@router.get("/logs")
async def emergency_logs(user=Depends(require_family)):

    async with DB() as cur:
        await cur.execute(
            """
            SELECT e.*, u.username AS triggered_by
            FROM emergency_events e
            JOIN users u ON u.user_id = e.activated_by
            WHERE e.family_id=%s
            ORDER BY e.sos_id DESC
            LIMIT 50
            """,
            (user["family_id"],),
        )
        rows = await cur.fetchall()

    return {"logs": rows}


# ─────────────────────────────────────────────
# ACTIVE SOS
# ─────────────────────────────────────────────
@router.get("/active")
async def active_sos(user=Depends(require_family)):

    async with DB() as cur:
        await cur.execute(
            """
            SELECT * FROM emergency_events
            WHERE family_id=%s AND status='ACTIVE'
            """,
            (user["family_id"],),
        )
        active = await cur.fetchall()

    return {"active": active}