"""backend/routers/auth.py — Module 1: Auth & Workspace Scoping."""
import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, status

from backend.database import DB
from backend.models.schemas import (
    UserRegister, UserLogin, TokenResponse,
    CreateWorkspace, InviteUser, AcceptInvite,
)
from backend.utils.auth import (
    hash_password, verify_password,
    create_access_token, get_current_user, require_family,
)

router = APIRouter(prefix="/auth", tags=["Auth & Workspace"])


# ── Registration ──────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    user_id = str(uuid.uuid4())
    async with DB() as cur:
        await cur.execute("SELECT user_id FROM users WHERE username=%s", (payload.username,))
        if await cur.fetchone():
            raise HTTPException(status_code=409, detail="Username already taken.")
        await cur.execute(
            "INSERT INTO users (user_id, username, password_hash, email) VALUES (%s,%s,%s,%s)",
            (user_id, payload.username, hash_password(payload.password), payload.email),
        )
    return {"message": "User created.", "user_id": user_id}


# ── Login ─────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    async with DB() as cur:
        await cur.execute(
            "SELECT user_id, password_hash, family_id FROM users WHERE username=%s",
            (payload.username,),
        )
        row = await cur.fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = create_access_token(
        {"sub": row["user_id"], "username": payload.username, "family_id": row["family_id"]}
    )
    return TokenResponse(access_token=token, family_id=row["family_id"])


# ── Create Family Workspace ───────────────────────────────────

@router.post("/workspace/create")
async def create_workspace(payload: CreateWorkspace, user=Depends(get_current_user)):
    if user.get("family_id"):
        raise HTTPException(status_code=400, detail="You are already in a family workspace.")
    family_id = str(uuid.uuid4())
    async with DB() as cur:
        await cur.execute(
            "INSERT INTO families (family_id, family_name) VALUES (%s,%s)",
            (family_id, payload.family_name),
        )
        await cur.execute(
            "UPDATE users SET family_id=%s, role='admin' WHERE user_id=%s",
            (family_id, user["sub"]),
        )
    new_token = create_access_token(
        {"sub": user["sub"], "username": user["username"], "family_id": family_id}
    )
    return {"message": "Workspace created.", "family_id": family_id, "access_token": new_token}


# ── Dispatch Invite ───────────────────────────────────────────

@router.post("/workspace/invite")
async def invite_user(payload: InviteUser, user=Depends(require_family)):
    async with DB() as cur:
        await cur.execute(
            "SELECT user_id FROM users WHERE username=%s", (payload.target_username,)
        )
        target = await cur.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        invite_id = str(uuid.uuid4())
        await cur.execute(
            "INSERT INTO family_invites (invite_id, family_id, invitee_id) VALUES (%s,%s,%s)",
            (invite_id, user["family_id"], target["user_id"]),
        )
    return {"message": "Invite sent.", "invite_id": invite_id}


# ── Accept Invite ─────────────────────────────────────────────

@router.post("/workspace/accept")
async def accept_invite(payload: AcceptInvite, user=Depends(get_current_user)):
    async with DB() as cur:
        await cur.execute(
            "SELECT * FROM family_invites WHERE invite_id=%s AND invitee_id=%s AND status='pending'",
            (payload.invite_id, user["sub"]),
        )
        invite = await cur.fetchone()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found or already actioned.")
        await cur.execute(
            "UPDATE family_invites SET status='accepted' WHERE invite_id=%s", (payload.invite_id,)
        )
        await cur.execute(
            "UPDATE users SET family_id=%s WHERE user_id=%s",
            (invite["family_id"], user["sub"]),
        )
    new_token = create_access_token(
        {"sub": user["sub"], "username": user["username"], "family_id": invite["family_id"]}
    )
    return {"message": "Joined workspace.", "family_id": invite["family_id"], "access_token": new_token}


# ── List Pending Invites ──────────────────────────────────────

@router.get("/invites/pending")
async def list_invites(user=Depends(get_current_user)):
    async with DB() as cur:
        await cur.execute(
            """SELECT fi.invite_id, f.family_name, fi.created_at
               FROM family_invites fi
               JOIN families f ON f.family_id = fi.family_id
               WHERE fi.invitee_id=%s AND fi.status='pending'""",
            (user["sub"],),
        )
        rows = await cur.fetchall()
    return {"invites": rows}
