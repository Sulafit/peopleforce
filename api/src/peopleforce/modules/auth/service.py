"""Passwordless sign-in.

Challenge state machine:  issued -> consumed      (POST /verify, atomic, single use)
                          issued -> expired       (time)
Opening the emailed link (GET page + POST /inspect) never changes state, so mail scanners that
prefetch links cannot burn it. Only an explicit POST /verify consumes the token and creates a session.
"""

import uuid
from datetime import timedelta

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from peopleforce.core.config import Settings
from peopleforce.core.errors import AppError
from peopleforce.core.security import hash_token, mask_email, new_token, normalize_email, utcnow
from peopleforce.infrastructure.analytics.base import Analytics
from peopleforce.infrastructure.email.senders import EmailDeliveryError, EmailSender
from peopleforce.modules.auth.models import MagicLinkChallenge, Session, User
from peopleforce.modules.auth.schemas import (
    CurrentUser,
    MagicLinkInspectOut,
    MagicLinkRequestOut,
)
from peopleforce.modules.curriculum.service import CurriculumService
from peopleforce.modules.onboarding.service import OnboardingService

log = structlog.get_logger()

JOURNEY_PATH = "/journey"


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        email: EmailSender,
        onboarding: OnboardingService,
        curriculum: CurriculumService,
        analytics: Analytics,
    ) -> None:
        self._session = session
        self._settings = settings
        self._email = email
        self._onboarding = onboarding
        self._curriculum = curriculum
        self._analytics = analytics

    # ---------- request ----------

    async def request_magic_link(
        self, email: str, onboarding_token: str | None, ip: str | None
    ) -> MagicLinkRequestOut:
        email = normalize_email(email)
        await self._enforce_rate_limits(email, ip)

        # Bind the finished quiz to this challenge server-side. The link itself carries only the token.
        draft = await self._onboarding.find_draft(onboarding_token)
        draft_id = draft.id if draft and draft.status == "completed" else None

        token = new_token()
        challenge = MagicLinkChallenge(
            email=email,
            token_hash=hash_token(token),
            onboarding_draft_id=draft_id,
            request_ip=ip,
            expires_at=utcnow() + timedelta(minutes=self._settings.magic_link_ttl_minutes),
        )
        self._session.add(challenge)
        await self._session.commit()

        link = f"{self._settings.public_base_url.rstrip('/')}/auth/verify?token={token}"
        try:
            await self._email.send_magic_link(email, link, self._settings.magic_link_ttl_minutes)
        except EmailDeliveryError as exc:
            log.error("magic_link_delivery_failed", error=str(exc))
            await self._session.delete(challenge)  # do not count a link that never left against the user
            await self._session.commit()
            raise AppError(
                "email_delivery_failed", "We could not send the email. Please try again in a moment.", 503
            ) from exc

        return MagicLinkRequestOut(
            email_masked=mask_email(email),
            expires_in_minutes=self._settings.magic_link_ttl_minutes,
            resend_after_seconds=self._settings.magic_link_min_interval_seconds,
            dev_link=link if self._settings.expose_dev_magic_link else None,
        )

    async def _enforce_rate_limits(self, email: str, ip: str | None) -> None:
        # `created_at` is written by the database clock, so every comparison here uses that clock too.
        hour_ago = func.now() - timedelta(hours=1)
        interval = self._settings.magic_link_min_interval_seconds

        seconds_since_last = await self._session.scalar(
            select(func.extract("epoch", func.now() - func.max(MagicLinkChallenge.created_at))).where(
                MagicLinkChallenge.email == email
            )
        )
        if seconds_since_last is not None and float(seconds_since_last) < interval:
            raise self._rate_limited(max(int(interval - float(seconds_since_last)), 1))

        per_email = await self._session.scalar(
            select(func.count())
            .select_from(MagicLinkChallenge)
            .where(MagicLinkChallenge.email == email, MagicLinkChallenge.created_at > hour_ago)
        )
        if (per_email or 0) >= self._settings.magic_link_max_per_email_per_hour:
            raise self._rate_limited(15 * 60)

        if ip:
            per_ip = await self._session.scalar(
                select(func.count())
                .select_from(MagicLinkChallenge)
                .where(MagicLinkChallenge.request_ip == ip, MagicLinkChallenge.created_at > hour_ago)
            )
            if (per_ip or 0) >= self._settings.magic_link_max_per_ip_per_hour:
                raise self._rate_limited(15 * 60)

    @staticmethod
    def _rate_limited(retry_after: int) -> AppError:
        return AppError(
            "rate_limited",
            "Too many sign-in emails requested. Please wait before trying again.",
            429,
            {"retry_after_seconds": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # ---------- inspect (never consumes) ----------

    async def inspect(self, token: str) -> MagicLinkInspectOut:
        challenge = await self._session.scalar(
            select(MagicLinkChallenge).where(MagicLinkChallenge.token_hash == hash_token(token))
        )
        if challenge is None:
            return MagicLinkInspectOut(status="invalid")
        if challenge.consumed_at is not None:
            return MagicLinkInspectOut(status="used")
        if challenge.expires_at <= utcnow():
            return MagicLinkInspectOut(status="expired")
        return MagicLinkInspectOut(status="valid", email_masked=mask_email(challenge.email))

    # ---------- verify (consumes, creates session, links quiz) ----------

    async def verify(self, token: str, user_agent: str | None) -> tuple[str, bool]:
        """Consume the challenge and sign the user in. Returns (session_token, is_new_user).

        One transaction: consume + user upsert + draft claim + profile + session all commit together,
        so a failure anywhere leaves the link unused and retryable.
        """
        token_hash = hash_token(token)
        now = utcnow()
        consumed = (
            await self._session.execute(
                update(MagicLinkChallenge)
                .where(
                    MagicLinkChallenge.token_hash == token_hash,
                    MagicLinkChallenge.consumed_at.is_(None),
                    MagicLinkChallenge.expires_at > now,
                )
                .values(consumed_at=now)
                .returning(MagicLinkChallenge.email, MagicLinkChallenge.onboarding_draft_id)
            )
        ).first()
        if consumed is None:
            state = await self.inspect(token)
            await self._session.rollback()
            if state.status == "used":
                raise AppError("link_used", "This sign-in link was already used. Request a new one.", 410)
            if state.status == "expired":
                raise AppError("link_expired", "This sign-in link has expired. Request a new one.", 410)
            raise AppError("link_invalid", "This sign-in link is not valid. Request a new one.", 400)

        user, is_new = await self._get_or_create_user(consumed.email)
        user.last_login_at = now

        draft_linked = False
        if consumed.onboarding_draft_id is not None:
            path = await self._curriculum.get_path()
            draft_linked = await self._onboarding.claim(consumed.onboarding_draft_id, user.id, path.id)

        session_token = new_token()
        self._session.add(
            Session(
                user_id=user.id,
                token_hash=hash_token(session_token),
                user_agent=(user_agent or "")[:400] or None,
                expires_at=now + timedelta(days=self._settings.session_ttl_days),
            )
        )
        await self._session.commit()

        self._analytics.capture(
            str(user.id), "authentication_completed", {"is_new_user": is_new, "draft_linked": draft_linked}
        )
        return session_token, is_new

    async def _get_or_create_user(self, email: str) -> tuple[User, bool]:
        # ON CONFLICT DO NOTHING + re-select: two concurrent first sign-ins still yield one account.
        inserted = (
            await self._session.execute(
                insert(User)
                .values(id=uuid.uuid4(), email=email)
                .on_conflict_do_nothing(index_elements=[User.email])
                .returning(User.id)
            )
        ).first()
        user = await self._session.scalar(select(User).where(User.email == email))
        assert user is not None
        return user, inserted is not None

    # ---------- sessions ----------

    async def resolve_session(self, session_token: str | None) -> CurrentUser | None:
        if not session_token:
            return None
        row = (
            await self._session.execute(
                select(User.id, User.email)
                .join(Session, Session.user_id == User.id)
                .where(
                    Session.token_hash == hash_token(session_token),
                    Session.revoked_at.is_(None),
                    Session.expires_at > utcnow(),
                )
            )
        ).first()
        return CurrentUser(id=row.id, email=row.email) if row else None

    async def logout(self, session_token: str | None) -> None:
        if not session_token:
            return
        await self._session.execute(
            update(Session)
            .where(Session.token_hash == hash_token(session_token), Session.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
        await self._session.commit()
