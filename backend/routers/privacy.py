"""
backend/routers/privacy.py
AI Privacy Protection API (Stable Production Version)
"""

import io
import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ai_privacy.pipeline import process_image
from backend.utils.auth import require_family

router = APIRouter(prefix="/privacy", tags=["AI Privacy"])


def to_bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


@router.post("/protect")
async def protect_photo(
    file: UploadFile = File(...),
    blur_targets: str = Form("true"),
    adversarial_noise: str = Form("true"),
    use_pgd: str = Form("false"),
    user=Depends(require_family),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    img_bytes = await file.read()

    # ───────────────────────────────
    # MODE SELECTION
    # ───────────────────────────────
    blur = to_bool(blur_targets)
    noise = to_bool(adversarial_noise)
    pgd = to_bool(use_pgd)

    if pgd:
        mode = "strict"
    elif not blur:
        mode = "family_safe"
    else:
        mode = "social_media"

    try:
        processed_bytes, report = process_image(img_bytes, mode=mode)

        report.update({
            "blur_targets": blur,
            "adversarial_noise": noise,
            "pgd": pgd,
            "mode": mode,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")

    headers = {
        "X-Privacy-Report": json.dumps(report),
        "X-Privacy-Mode": mode,
    }

    return StreamingResponse(
        io.BytesIO(processed_bytes),
        media_type="image/jpeg",
        headers=headers,
    )