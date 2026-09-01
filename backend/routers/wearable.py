"""
KINNECT — Wearable Health + AI Intelligence Module (CLEAN GEMINI VERSION)
"""

import json
import random
import time
from datetime import date, timedelta, datetime
from typing import Optional

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException

from backend.database import DB
from backend.models.schemas import BiometricIngest
from backend.utils.auth import require_family

router = APIRouter(prefix="/health", tags=["Wearable Health"])

# ─────────────────────────────────────────────
# GEMINI CONFIG
# ─────────────────────────────────────────────

GEMINI_API_KEY = "AIzaSyBHXZtmQOg-pg-CtUUY6-jJf5sNqeDqQC8"

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"


def safe_json(obj):
    return json.dumps(obj, default=str, indent=2)


def call_gemini(prompt: str):
    model = genai.GenerativeModel(MODEL_NAME)

    for attempt in range(5):
        try:
            res = model.generate_content(prompt)
            return res.text

        except Exception as e:
            msg = str(e).lower()

            if "429" in msg or "resource_exhausted" in msg:
                time.sleep(2 ** attempt)
                continue

            break

    return "AI temporarily unavailable."


def build_ai_context(rows, user_id: str):
    return {
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
        "count": len(rows or []),
        "data": rows or []
    }


def generate_ai_report(context: dict, mode: str = "daily"):
    prompt = f"""
You are a wearable health AI assistant.

Generate a {mode} report.

Rules:
- No diagnosis
- Focus on lifestyle insights
- Be structured

Format:
1. Summary
2. Risk Flags
3. Recommendations

DATA:
{safe_json(context)}
"""

    return call_gemini(prompt)


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
    return round(sum(WEIGHTS[k] * _score(k, row.get(k)) for k in WEIGHTS), 1)


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
# INGEST
# ─────────────────────────────────────────────

@router.post("/ingest")
async def ingest(payload: BiometricIngest, user=Depends(require_family)):
    family_id = user["family_id"]

    async with DB() as cur:
        await cur.execute(
            "SELECT 1 FROM users WHERE user_id=%s",
            (payload.user_id,)
        )
        exists = await cur.fetchone()

    if not exists:
        raise HTTPException(status_code=400, detail="user_id does not exist")

    anomaly = detect_anomaly(payload.model_dump())

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

        rows = [mock_row(m["user_id"], family_id) | {"username": m["username"]} for m in members]

    for r in rows:
        r["lifestyle_score"] = compute_lifestyle_score(r)

    return {"date": today, "members": rows}


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
        return {"status": "no_data"}

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
        return {"status": "no_data"}

    context = build_ai_context(rows, user_id)
    report = generate_ai_report(context, "weekly")

    return {"user_id": user_id, "report": report}