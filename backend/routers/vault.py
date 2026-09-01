import uuid
import os
import io
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from backend.database import DB
from backend.models.schemas import VaultUnlockRequest, VaultTokenResponse
from backend.utils.auth import require_family, verify_password
from backend.config import settings


router = APIRouter(prefix="/vault", tags=["Secure Vault"])

# in-memory session store
_vault_sessions: dict[str, dict] = {}


# ── AES helpers ───────────────────────────────────────────────

def _aes_encrypt(data: bytes, key: bytes):
    iv = secrets.token_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size)), iv


def _aes_decrypt(ciphertext: bytes, key: bytes, iv: bytes):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)


def _derive_key(vault_password: str) -> bytes:
    import hashlib
    return hashlib.sha256(vault_password.encode()).digest()


# ── session helper ───────────────────────────────────────────

def _require_vault_session(vault_token: str, family_id: str):
    session = _vault_sessions.get(vault_token)
    print("SESSION DEBUG:", session)
    print("REQUEST FAMILY:", family_id)
    print("TOKEN RECEIVED:", vault_token)
    print("ALL TOKENS:", list(_vault_sessions.keys()))

    if not session:
        raise HTTPException(status_code=401, detail="No active vault session.")

    # normalize types (IMPORTANT FIX)
    if str(session.get("family_id")) != str(family_id):
        raise HTTPException(status_code=403, detail="Invalid vault session (family mismatch).")

    if datetime.utcnow().timestamp() > session["expires"]:
        _vault_sessions.pop(vault_token, None)
        raise HTTPException(status_code=401, detail="Vault session expired.")

    return session


# ── security question ─────────────────────────────────────────

@router.get("/question")
async def get_security_question(user=Depends(require_family)):
    family_id = user["family_id"]

    async with DB() as cur:
        await cur.execute(
            """
            SELECT question_id, question
            FROM vault_security_questions
            WHERE family_id=%s
            ORDER BY RAND()
            LIMIT 1
            """,
            (family_id,),
        )
        row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No security questions configured.")

    return row


# ── unlock vault ─────────────────────────────────────────────

@router.post("/unlock", response_model=VaultTokenResponse)
async def unlock_vault(payload: VaultUnlockRequest, user=Depends(require_family)):
    family_id = user["family_id"]

    async with DB() as cur:
        await cur.execute(
            "SELECT password_hash FROM users WHERE user_id=%s",
            (user["sub"],),
        )
        u = await cur.fetchone()

        if not u or not verify_password(payload.vault_password, u["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid vault password.")

        await cur.execute(
            """
            SELECT answer_hash
            FROM vault_security_questions
            WHERE question_id=%s AND family_id=%s
            """,
            (payload.question_id, family_id),
        )
        q = await cur.fetchone()

        if not q or not verify_password(payload.security_answer.strip().lower(), q["answer_hash"]):
            raise HTTPException(status_code=401, detail="Incorrect security answer.")

    token = secrets.token_urlsafe(32)

    expires = datetime.utcnow() + timedelta(minutes=settings.VAULT_TOKEN_EXPIRE_MINUTES)

    _vault_sessions[token] = {
        "family_id": str(family_id),
        "user_id": str(user["sub"]),
        "expires": expires.timestamp()
    }

    return VaultTokenResponse(
        session_token=token,
        expires_in_seconds=settings.VAULT_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/lock")
async def lock_vault(vault_token: str, user=Depends(require_family)):
    _vault_sessions.pop(vault_token, None)
    return {"message": "Vault locked."}


# ── documents ────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    category: Optional[str] = None,
    vault_token: str = "",
    user=Depends(require_family),
):
    family_id = user["family_id"]
    _require_vault_session(vault_token, family_id)

    async with DB() as cur:
        if category and category != "All Files":
            await cur.execute(
                """
                SELECT doc_id, file_name, category, uploaded_at
                FROM vault_documents
                WHERE family_id=%s AND category=%s
                """,
                (family_id, category),
            )
        else:
            await cur.execute(
                """
                SELECT doc_id, file_name, category, uploaded_at
                FROM vault_documents
                WHERE family_id=%s
                """,
                (family_id,),
            )

        return {"documents": await cur.fetchall()}


# ── upload ───────────────────────────────────────────────────

@router.post("/upload", status_code=201)
async def upload_document(
    vault_token: str = Form(...),
    vault_password: str = Form(...),
    category: str = Form("Other"),
    file: UploadFile = File(...),
    user=Depends(require_family),
):
    family_id = user["family_id"]
    _require_vault_session(vault_token, family_id)

    storage_dir = settings.VAULT_STORAGE_PATH
    os.makedirs(storage_dir, exist_ok=True)

    raw = await file.read()

    key = _derive_key(vault_password)
    ciphertext, iv = _aes_encrypt(raw, key)

    doc_id = str(uuid.uuid4())
    enc_path = os.path.join(storage_dir, f"{doc_id}.enc")

    with open(enc_path, "wb") as f:
        f.write(ciphertext)

    async with DB() as cur:
        await cur.execute(
            """
            INSERT INTO vault_documents
            (doc_id, family_id, uploaded_by, file_name, category, enc_path, iv_hex)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (doc_id, family_id, user["sub"], file.filename, category, enc_path, iv.hex()),
        )

    return {"message": "Uploaded", "doc_id": doc_id}


# ── download ─────────────────────────────────────────────────

@router.get("/download/{doc_id}")
async def download_document(
    doc_id: str,
    vault_token: str,
    vault_password: str,
    user=Depends(require_family),
):
    family_id = user["family_id"]
    _require_vault_session(vault_token, family_id)

    async with DB() as cur:
        await cur.execute(
            "SELECT * FROM vault_documents WHERE doc_id=%s AND family_id=%s",
            (doc_id, family_id),
        )
        doc = await cur.fetchone()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    with open(doc["enc_path"], "rb") as f:
        ciphertext = f.read()

    key = _derive_key(vault_password)
    iv = bytes.fromhex(doc["iv_hex"])

    try:
        plaintext = _aes_decrypt(ciphertext, key, iv)
    except Exception:
        raise HTTPException(status_code=401, detail="Wrong vault password.")

    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc["file_name"]}"'},
    )


# ── delete ───────────────────────────────────────────────────
from fastapi import Query

@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    vault_token: str = Query(...),
    user=Depends(require_family),
):
    family_id = user["family_id"]

    _require_vault_session(vault_token, family_id)

    async with DB() as cur:
        await cur.execute(
            "SELECT enc_path FROM vault_documents WHERE doc_id=%s AND family_id=%s",
            (doc_id, family_id),
        )
        doc = await cur.fetchone()

        if doc:
            try:
                os.remove(doc["enc_path"])
            except FileNotFoundError:
                pass

            await cur.execute(
                "DELETE FROM vault_documents WHERE doc_id=%s",
                (doc_id,),
            )

   