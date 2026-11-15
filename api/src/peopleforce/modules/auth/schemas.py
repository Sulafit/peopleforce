import uuid
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from peopleforce.modules.freelancer.schemas import ProfileOut


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str


class MagicLinkRequestIn(BaseModel):
    email: EmailStr


class MagicLinkRequestOut(BaseModel):
    status: Literal["sent"] = "sent"
    email_masked: str
    expires_in_minutes: int
    resend_after_seconds: int
    # Present only in non-production with the console email provider (no real email is sent).
    dev_link: str | None = None


class TokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class MagicLinkInspectOut(BaseModel):
    status: Literal["valid", "expired", "used", "invalid"]
    email_masked: str | None = None


class VerifyOut(BaseModel):
    redirect: str
    is_new_user: bool


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    profile: ProfileOut | None
    # True when the account exists but the quiz was never attached to it.
    onboarding_required: bool
