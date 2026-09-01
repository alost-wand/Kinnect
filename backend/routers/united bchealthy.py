"""
KINNECT — Wearable Health + AI Intelligence Module (Fixed Production Version)
"""

import json
import random
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from huggingface_hub import InferenceClient

from backend.database import DB
from backend.models.schemas import BiometricIngest
from backend.utils.auth import require_family

router = APIRouter(prefix="/health", tags=["Wearable Health"])

# ─────────────────────────────────────────────
# AI CONFIG
# ─────────────────────────────────────────────

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = "microsoft/Phi-3-mini-4k-instruct"

HF = InferenceClient(token=HF_TOKEN)

# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

WEIGHTS = {
    "heart_rate": 0.20,
    "sleep_minutes": 0.25,
    "hydration_ml": 0.20,
    "step_count": 0.20,
    "screen_minutes": 0.15,
}

NORMS = {
    "heart_rate": (60, 100),
    "sleep_minutes": (420, 540),
    "hydration_ml": (2000, 3000),
    "step_count": (7000, 12000),
    "screen_minutes": (0, 120),
}


def _score(key: str, value: Optional[int]) -> float:
    if value is None:
        return 50.0

    lo, hi = NORMS[key]

    if key == "screen_minutes":
        return max(0.0, min(100.0, 100 - (value - lo) / (hi - lo) * 100))

    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


def compute_lifestyle_score(row: dict) -> float:
    return round(
        sum(WEIGHTS[k] * _score(k, row.get(k)) for k in WEIGHTS),
        1
    )

# ─────────────────────────────────────────────
# MOCK DATA
# ─────────────────────────────────────────────

def mock_row(user_id: str, family_id: str):
    return {
        "user_id": user_id,
        "family_id": family_id,
        "heart_rate": random.randint(60, 95),
        "hydration_ml": random.randint(1200, 3200),
        "sleep_minutes": random.randint(300, 570),
        "screen_minutes": random.randint(30, 420),
        "step_count": random.randint(2000, 15000),
        "recorded_date": str(date.today()),
        "has_anomaly": False,
        "username": "mock"
    }


def detect_anomaly(row: dict) -> bool:
    return (
        (row.get("heart_rate") or 0) > 110
        or (row.get("sleep_minutes") or 0) < 240
        or (row.get("step_count") or 0) < 1000
    )

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

async def validate_user(user_id: str, family_id: str):
    """Prevents FK crash BEFORE insert"""
    async with DB() as cur:
        await cur.execute(
            "SELECT user_id FROM users WHERE user_id=%s AND family_id=%s",
            (user_id, family_id)
        )
        return await cur.fetchone()


def generate_ai_report(context: dict, mode: str = "daily"):
    prompt = f"""
You are a health intelligence assistant.

Generate a {mode} wellness report.

Rules:
- DO NOT diagnose disease
- Focus on lifestyle trends
- Be structured

Format:
1. Summary
2. Risk Flags
3. Recommendations

DATA:
{json.dumps(context, default=str, indent=2)}
"""

    response = HF.chat_completion(
        model="HuggingFaceH4/zephyr-7b-beta",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=350
    )

    return response.choices[0].message["content"]

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@router.post("/ingest")
async def ingest(payload: BiometricIngest, user=Depends(require_family)):
    family_id = user["family_id"]

    # STEP 1: validate ONLY user exists (no family check)
    async with DB() as cur:
        await cur.execute(
            "SELECT 1 FROM users WHERE user_id=%s",
            (payload.user_id,)
        )
        exists = await cur.fetchone()

    if not exists:
        raise HTTPException(
            status_code=400,
            detail="user_id does not exist"
        )

    anomaly = detect_anomaly(payload.model_dump())

    # STEP 2: insert safely using auth family_id
    async with DB() as cur:
        await cur.execute("""
            INSERT INTO wearable_telemetry
            (user_id, family_id, heart_rate, hydration_ml, sleep_minutes,
             screen_minutes, step_count, recorded_date, has_anomaly)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
            heart_rate=VALUES(heart_rate),
            hydration_ml=VALUES(hydration_ml),
            sleep_minutes=VALUES(sleep_minutes),
            screen_minutes=VALUES(screen_minutes),
            step_count=VALUES(step_count),
            has_anomaly=VALUES(has_anomaly)
        """, (
            payload.user_id,
            family_id,
            payload.heart_rate,
            payload.hydration_ml,
            payload.sleep_minutes,
            payload.screen_minutes,
            payload.step_count,
            payload.recorded_date,
            anomaly
        ))

    return {"status": "ok", "anomaly": anomaly}
    print("RAW PAYLOAD:", payload.model_dump())
    print("USER_ID TYPE:", type(payload.user_id))
    print("USER_ID VALUE:", repr(payload.user_id))
# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(user=Depends(require_family)):
    family_id = user["family_id"]
    today = str(date.today())

    async with DB() as cur:
        await cur.execute("""
            SELECT t.*, u.username
            FROM wearable_telemetry t
            JOIN users u ON u.user_id = t.user_id
            WHERE t.family_id=%s AND t.recorded_date=%s
        """, (family_id, today))
        rows = await cur.fetchall()

    if not rows:
        async with DB() as cur:
            await cur.execute("""
                SELECT user_id, username
                FROM users
                WHERE family_id=%s
            """, (family_id,))
            members = await cur.fetchall()

        rows = [
            mock_row(m["user_id"], family_id) | {"username": m["username"]}
            for m in members
        ]

    for r in rows:
        r["lifestyle_score"] = compute_lifestyle_score(r)

    return {"date": today, "members": rows}


# ─────────────────────────────────────────────
# SPARKLINES
# ─────────────────────────────────────────────

@router.get("/sparklines/{user_id}")
async def sparklines(user_id: str, days: int = 7, user=Depends(require_family)):
    family_id = user["family_id"]
    since = str(date.today() - timedelta(days=days))

    async with DB() as cur:
        await cur.execute("""
            SELECT recorded_date, heart_rate, step_count, sleep_minutes
            FROM wearable_telemetry
            WHERE user_id=%s AND family_id=%s AND recorded_date >= %s
            ORDER BY recorded_date ASC
        """, (user_id, family_id, since))
        rows = await cur.fetchall()

    return {"user_id": user_id, "sparklines": rows}


# ─────────────────────────────────────────────
# AI ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/ai/daily/{user_id}")
async def ai_daily(user_id: str, user=Depends(require_family)):
    family_id = user["family_id"]
    today = str(date.today())

    async with DB() as cur:
        await cur.execute("""
            SELECT * FROM wearable_telemetry
            WHERE user_id=%s AND family_id=%s AND recorded_date=%s
        """, (user_id, family_id, today))
        rows = await cur.fetchall()

    if not rows:
        return {"status": "no_data", "message": "No data for today"}

    context = build_ai_context(rows, user_id)
    report = generate_ai_report(context, "daily")

    return {"user_id": user_id, "report": report}


@router.get("/ai/weekly/{user_id}")
async def ai_weekly(user_id: str, user=Depends(require_family)):
    family_id = user["family_id"]
    since = str(date.today() - timedelta(days=7))

    async with DB() as cur:
        await cur.execute("""
            SELECT * FROM wearable_telemetry
            WHERE user_id=%s AND family_id=%s AND recorded_date >= %s
        """, (user_id, family_id, since))
        rows = await cur.fetchall()

    if not rows:
        return {"status": "no_data", "message": "No data for week"}

    context = build_ai_context(rows, user_id)
    report = generate_ai_report(context, "weekly")

    return {"user_id": user_id, "report": report}


# ─────────────────────────────────────────────
# DEBUG
# ─────────────────────────────────────────────

@router.get("/debug/user/{user_id}")
async def debug_user(user_id: str, user=Depends(require_family)):
    family_id = user["family_id"]

    async with DB() as cur:
        await cur.execute("""
            SELECT *
            FROM wearable_telemetry
            WHERE user_id=%s AND family_id=%s
        """, (user_id, family_id))
        rows = await cur.fetchall()

    return {
        "count": len(rows),
        "rows": rows
    }
