from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import structlog
from dishka import Provider, Scope, provide
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from peopleforce.core.config import Settings
from peopleforce.core.database import create_engine, create_sessionmaker
from peopleforce.core.errors import unauthorized
from peopleforce.infrastructure.ai.prompts import PromptStore
from peopleforce.infrastructure.ai.providers import AnthropicProvider, GeminiProvider, LlmProvider
from peopleforce.infrastructure.analytics.base import Analytics, NoopAnalytics, PostHogAnalytics
from peopleforce.infrastructure.cms.sanity import SanityContentSource
from peopleforce.infrastructure.email.senders import ConsoleEmailSender, EmailSender, ResendEmailSender
from peopleforce.modules.ai.service import AiService
from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.auth.service import AuthService
from peopleforce.modules.curriculum.service import SEED_DIR, CurriculumService, LocalContentSource
from peopleforce.modules.freelancer.drafts import AssetDraftService
from peopleforce.modules.freelancer.service import FreelancerService
from peopleforce.modules.gamification.daily import DailyService
from peopleforce.modules.gamification.service import GamificationService
from peopleforce.modules.onboarding.service import OnboardingService
from peopleforce.modules.progression.service import ProgressionService
from peopleforce.modules.tours.service import TourService

log = structlog.get_logger()


@dataclass(frozen=True)
class AiRuntime:
    """The configured model provider (None when AI is switched off)."""

    provider: LlmProvider | None


class InfrastructureProvider(Provider):
    """Process-wide adapters. Tests replace individual factories with an overriding provider."""

    scope = Scope.APP

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide
    def settings(self) -> Settings:
        return self._settings

    @provide
    async def engine(self, settings: Settings) -> AsyncIterator[AsyncEngine]:
        engine = create_engine(settings.database_url)
        yield engine
        await engine.dispose()

    @provide
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_sessionmaker(engine)

    @provide
    def email_sender(self, settings: Settings) -> EmailSender:
        if settings.email_provider == "resend":
            if not settings.resend_api_key:
                raise RuntimeError("EMAIL_PROVIDER=resend requires RESEND_API_KEY")
            return ResendEmailSender(settings.resend_api_key, settings.email_from)
        if settings.is_production:
            log.warning("console_email_in_production", hint="set EMAIL_PROVIDER=resend")
        return ConsoleEmailSender()

    @provide
    def analytics(self, settings: Settings) -> Iterator[Analytics]:
        analytics: Analytics = (
            PostHogAnalytics(settings.posthog_api_key, settings.posthog_host)
            if settings.posthog_api_key
            else NoopAnalytics()
        )
        yield analytics
        analytics.shutdown()

    @provide
    def curriculum(self, settings: Settings) -> CurriculumService:
        local = LocalContentSource(Path(settings.content_dir) if settings.content_dir else SEED_DIR)
        if settings.content_source == "sanity":
            if not settings.sanity_project_id:
                raise RuntimeError("CONTENT_SOURCE=sanity requires SANITY_PROJECT_ID")
            source = SanityContentSource(
                settings.sanity_project_id,
                settings.sanity_dataset,
                settings.sanity_api_version,
                settings.sanity_token,
            )
            return CurriculumService(source, fallback=local, ttl_seconds=settings.content_cache_ttl_seconds)
        return CurriculumService(local, fallback=None, ttl_seconds=settings.content_cache_ttl_seconds)

    @provide
    def ai_runtime(self, settings: Settings) -> AiRuntime:
        if settings.llm_provider == "gemini":
            if not settings.gemini_api_key:
                raise RuntimeError("LLM_PROVIDER=gemini requires GEMINI_API_KEY")
            return AiRuntime(GeminiProvider(settings.llm_model, settings.gemini_api_key))
        if settings.llm_provider == "anthropic":
            return AiRuntime(AnthropicProvider(settings.llm_model))
        return AiRuntime(None)

    @provide
    def prompt_store(self, settings: Settings) -> Iterator[PromptStore]:
        store = PromptStore(
            settings.langfuse_public_key,
            settings.langfuse_secret_key,
            settings.langfuse_host,
            environment=settings.app_env,
        )
        yield store
        store.shutdown()


class RequestProvider(Provider):
    """Per-request graph: one DB session shared by every service handling the request."""

    scope = Scope.REQUEST

    @provide
    async def session(self, maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
        # Services commit explicitly; anything left uncommitted is rolled back when the session closes.
        async with maker() as session:
            yield session

    @provide
    def ai_service(
        self,
        session: AsyncSession,
        settings: Settings,
        runtime: AiRuntime,
        prompts: PromptStore,
        freelancer: FreelancerService,
    ) -> AiService:
        return AiService(session, settings, runtime.provider, prompts, freelancer)

    freelancer = provide(FreelancerService)
    onboarding = provide(OnboardingService)
    gamification = provide(GamificationService)
    tours = provide(TourService)
    auth = provide(AuthService)
    progression = provide(ProgressionService)
    asset_drafts = provide(AssetDraftService)
    daily = provide(DailyService)

    @provide
    async def current_user(self, request: Request, auth: AuthService, settings: Settings) -> CurrentUser:
        user = await auth.resolve_session(request.cookies.get(settings.session_cookie_name))
        if user is None:
            raise unauthorized()
        return user
