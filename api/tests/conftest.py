"""Integration test harness: real PostgreSQL (schema built by Alembic), real app, fake email + LLM."""

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from alembic.config import Config
from dishka import Provider, Scope, provide
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from peopleforce.core.config import Settings
from peopleforce.di.providers import AiRuntime
from peopleforce.infrastructure.ai.providers import LlmError, LlmResult
from peopleforce.infrastructure.email.senders import EmailDeliveryError, EmailSender
from peopleforce.main import create_app
from peopleforce.models import Base

ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql+asyncpg://peopleforce:peopleforce@localhost:5433/postgres"
)
TEST_DB = "peopleforce_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"
ORIGIN = "http://testserver"


class CapturingEmail:
    def __init__(self) -> None:
        self.links: dict[str, list[str]] = {}
        self.fail = False

    async def send_magic_link(self, to: str, link: str, expires_minutes: int) -> None:
        if self.fail:
            raise EmailDeliveryError("simulated outage")
        self.links.setdefault(to, []).append(link)

    def token(self, email: str) -> str:
        return self.links[email.strip().lower()][-1].split("token=")[1]


class FakeLlm:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.fail = False
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(self, *, system, user, output_model: type[BaseModel], max_tokens, timeout):
        self.calls.append({"system": system, "user": user})
        if self.fail:
            raise LlmError("simulated provider outage")
        fields = output_model.model_fields
        if "clarity_score" in fields:
            feedback = output_model(
                summary="Clear start.",
                strengths=["Names a client"],
                improvements=[{"issue": "Vague result", "suggestion": "Say what changes."}],
                clarity_score=4,
                specificity_score=3,
                suggested_one_liner="I build tools for small teams so they can save time.",
            )
            return LlmResult(output=feedback, usage={"input_tokens": 120, "output_tokens": 80})
        draft = output_model(
            title="Draft title", body="Draft body [link to a project you built]", notes=["Check it"]
        )
        return LlmResult(output=draft)


class Harness:
    def __init__(self, app, email: CapturingEmail, llm: FakeLlm, settings: Settings) -> None:
        self.app = app
        self.email = email
        self.llm = llm
        self.settings = settings

    def client(self) -> AsyncClient:
        """A fresh browser: its own cookie jar."""
        return AsyncClient(transport=ASGITransport(app=self.app), base_url=ORIGIN, headers={"origin": ORIGIN})


@pytest.fixture(scope="session")
async def database() -> AsyncIterator[str]:
    admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        await connection.execute(text(f"CREATE DATABASE {TEST_DB}"))
    await admin.dispose()

    # Build the schema with the real migrations, so they are exercised on every run.
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_URL)
    import asyncio

    await asyncio.to_thread(command.upgrade, config, "head")
    yield TEST_URL


@pytest.fixture
async def harness(database: str) -> AsyncIterator[Harness]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=database,
        public_base_url=ORIGIN,
        magic_link_min_interval_seconds=0,
        llm_provider="none",
        email_provider="console",
        content_source="local",
    )
    email = CapturingEmail()
    llm = FakeLlm()

    class Overrides(Provider):
        scope = Scope.APP

        @provide(override=True)
        def email_sender(self) -> EmailSender:
            return email

        @provide(override=True)
        def ai_runtime(self) -> AiRuntime:
            return AiRuntime(llm)

    app = create_app(settings, overrides=[Overrides()])
    engine = create_async_engine(database)
    async with engine.begin() as connection:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()
    async with app.router.lifespan_context(app):
        yield Harness(app, email, llm, settings)


ANSWERS: dict[str, Any] = {
    "domain": "software_development",
    "specialization": "backend",
    "experience_level": "1_3_years",
    "freelance_stage": "never",
    "existing_assets": ["work_samples", "linkedin_presence"],
    "acquisition_channel": "upwork",
    "primary_goal": "first_client",
}

OFFER = {
    "values": {
        "what-you-build": "APIs and integrations between business tools",
        "who-needs-it": "Small product teams without a backend developer",
        "problem-solved": "Their app slows down or breaks as usage grows",
        "relevant-experience": "Built a practice inventory API with a public repository",
    }
}


async def take_quiz(client: AsyncClient, answers: dict[str, Any] | None = None) -> dict[str, Any]:
    for question_id, value in (answers or ANSWERS).items():
        response = await client.put(
            "/api/v1/onboarding/answers", json={"question_id": question_id, "value": value}
        )
        assert response.status_code == 200, response.text
    response = await client.post("/api/v1/onboarding/complete")
    assert response.status_code == 200, response.text
    return response.json()


async def request_link(harness: Harness, client: AsyncClient, email: str) -> str:
    response = await client.post("/api/v1/auth/magic-link", json={"email": email})
    assert response.status_code == 202, response.text
    return harness.email.token(email)


async def sign_in(harness: Harness, client: AsyncClient, email: str) -> dict[str, Any]:
    token = await request_link(harness, client, email)
    response = await client.post("/api/v1/auth/magic-link/verify", json={"token": token})
    assert response.status_code == 200, response.text
    return response.json()


async def onboard(harness: Harness, email: str = "dev@example.com") -> AsyncClient:
    """Quiz -> magic link -> signed-in client."""
    client = harness.client()
    await take_quiz(client)
    await sign_in(harness, client, email)
    return client


async def finish_first_lesson(client: AsyncClient, lesson_id: str = "define-your-offer") -> dict[str, Any]:
    base = f"/api/v1/journey/lessons/{lesson_id}"
    assert (await client.post(f"{base}/start")).status_code == 200
    assert (await client.post(f"{base}/actions/offer-draft", json={"payload": OFFER})).status_code == 200
    assert (await client.post(f"{base}/actions/save-offer", json={"payload": {}})).status_code == 200
    response = await client.post(f"{base}/complete")
    assert response.status_code == 200, response.text
    return response.json()
