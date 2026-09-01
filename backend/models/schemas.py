from pydantic import BaseModel
from typing import Optional, Any


# ==========================
# AUTH
# ==========================

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    family_id: Optional[str] = None


# ==========================
# FAMILY
# ==========================

class CreateWorkspace(BaseModel):
    family_name: str


class InviteUser(BaseModel):
    target_username: str


class AcceptInvite(BaseModel):
    invite_id: str


# ==========================
# TIMELINE / CALENDAR
# ==========================

class EventCreate(BaseModel):

    title: str

    description: Optional[str] = None

    event_type: str
    # appointment
    # chore
    # milestone
    # reminder

    start_time: str

    end_time: Optional[str] = None

    visibility: str = "public"
    # public
    # private
    # busy_only

    alarm_config: Optional[Any] = None

    assigned_to: Optional[str] = None

    is_recurring: Optional[bool] = False

    recurrence_pattern: Optional[str] = None
    # daily
    # weekly
    # monthly


class EventUpdate(BaseModel):

    is_completed: Optional[bool] = None

    visibility: Optional[str] = None

    start_time: Optional[str] = None

    end_time: Optional[str] = None

    title: Optional[str] = None

    description: Optional[str] = None

    assigned_to: Optional[str] = None


# ==========================
# HEALTH / WEARABLE
# ==========================

class BiometricIngest(BaseModel):

    user_id: str

    heart_rate: Optional[int] = None

    hydration_ml: Optional[int] = 0

    sleep_minutes: Optional[int] = 0

    screen_minutes: Optional[int] = 0

    step_count: Optional[int] = 0

    recorded_date: str


# ==========================
# SOS
# ==========================

class SOSTrigger(BaseModel):

    latitude: float

    longitude: float


class SOSResolve(BaseModel):

    sos_id: str


# ==========================
# VAULT
# ==========================

class VaultUnlockRequest(BaseModel):

    vault_password: str

    question_id: str

    security_answer: str


class VaultTokenResponse(BaseModel):

    session_token: str

    expires_in_seconds: int