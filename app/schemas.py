import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class MessageOut(BaseModel):
    message: str


class ProjectCreateFromLink(BaseModel):
    url: str
    platform: str
    user_instruction: Optional[str] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    status: str
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None
    user_instruction: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HighlightOut(BaseModel):
    id: uuid.UUID
    start_seconds: float
    end_seconds: float
    label: str
    score: float
    confidence: Optional[float] = None
    selected: bool
    matches_instruction: Optional[bool] = None
    instruction_reasoning: Optional[str] = None

    class Config:
        from_attributes = True


class ClipOut(BaseModel):
    id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    output_path: Optional[str] = None

    class Config:
        from_attributes = True


class PlatformConnectionOut(BaseModel):
    id: uuid.UUID
    platform: str
    external_username: Optional[str] = None
    connected_at: datetime

    class Config:
        from_attributes = True


class PlanOptionOut(BaseModel):
    plan: str
    cycle: str
    price_usd: float
    minutes_included: int


class BillingStatusOut(BaseModel):
    plan: str
    billing_cycle: Optional[str] = None
    is_trial: bool
    trial_days_remaining: int
    minutes_included: int
    minutes_used_this_period: float
    minutes_rollover_balance: float
    minutes_remaining: float
    has_payment_method: bool


class CheckoutRequest(BaseModel):
    plan: str
    cycle: str


class PaygCheckoutRequest(BaseModel):
    amount_usd: float


class CheckoutSessionOut(BaseModel):
    checkout_url: str


class PortalSessionOut(BaseModel):
    portal_url: str
