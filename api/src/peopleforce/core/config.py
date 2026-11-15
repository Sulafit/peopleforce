from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Values come from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # Public origin of the web app. Magic links point here and unsafe requests must come from it.
    public_base_url: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://peopleforce:peopleforce@localhost:5433/peopleforce"

    # Sessions and magic links
    session_cookie_name: str = "pf_session"
    onboarding_cookie_name: str = "pf_onb"
    session_ttl_days: int = 30
    magic_link_ttl_minutes: int = 15
    magic_link_min_interval_seconds: int = 30
    magic_link_max_per_email_per_hour: int = 5
    magic_link_max_per_ip_per_hour: int = 30
    onboarding_draft_ttl_days: int = 14

    # Email
    email_provider: Literal["console", "resend"] = "console"
    resend_api_key: str = ""
    email_from: str = "PeopleForce <onboarding@resend.dev>"

    # Content
    content_source: Literal["local", "sanity"] = "local"
    content_cache_ttl_seconds: int = 60
    sanity_project_id: str = ""
    sanity_dataset: str = "production"
    sanity_api_version: str = "2025-02-19"
    sanity_token: str = ""
    # Directory with seed content (<domain>.json). Empty: the `content/` folder next to `src/`.
    content_dir: str = ""

    # AI
    llm_provider: Literal["none", "gemini", "anthropic"] = "none"
    # Model id for the chosen provider, e.g. gemini-3.5-flash-lite or claude-haiku-5-5.
    llm_model: str = "gemini-3.5-flash-lite"
    gemini_api_key: str = ""
    llm_timeout_seconds: float = 45.0
    ai_daily_limit_per_user: int = 30

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )

    # Analytics
    posthog_api_key: str = ""
    posthog_host: str = "https://eu.i.posthog.com"

    # Extra origins allowed to send unsafe requests (comma separated). The public origin is always allowed.
    extra_allowed_origins: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cookie_secure(self) -> bool:
        return self.public_base_url.startswith("https://")

    @property
    def allowed_origins(self) -> set[str]:
        origins = {self.public_base_url.rstrip("/")}
        origins.update(o.strip().rstrip("/") for o in self.extra_allowed_origins.split(",") if o.strip())
        return origins

    @property
    def expose_dev_magic_link(self) -> bool:
        """Only when no real email leaves the machine: lets a developer finish the flow without an inbox."""
        return self.app_env != "production" and self.email_provider == "console"


@lru_cache
def get_settings() -> Settings:
    return Settings()
