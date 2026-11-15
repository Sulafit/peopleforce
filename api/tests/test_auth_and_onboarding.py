from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .conftest import ANSWERS, Harness, request_link, sign_in, take_quiz


async def execute(harness: Harness, sql: str) -> None:
    engine = create_async_engine(harness.settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(text(sql))
    await engine.dispose()


async def test_quiz_resumes_after_refresh_and_validates_answers(harness: Harness):
    client = harness.client()
    quiz = (await client.get("/api/v1/onboarding/quiz")).json()
    assert len(quiz["questions"]) == 7
    assert quiz["draft"] is None

    await client.put(
        "/api/v1/onboarding/answers", json={"question_id": "domain", "value": "software_development"}
    )
    resumed = (await client.get("/api/v1/onboarding/quiz")).json()
    assert resumed["draft"] == {"status": "in_progress", "answers": {"domain": "software_development"}}

    disabled = await client.put(
        "/api/v1/onboarding/answers", json={"question_id": "domain", "value": "design"}
    )
    assert disabled.status_code == 422
    mixed = await client.put(
        "/api/v1/onboarding/answers",
        json={"question_id": "existing_assets", "value": ["none", "upwork_profile"]},
    )
    assert mixed.status_code == 422
    unknown = await client.put("/api/v1/onboarding/answers", json={"question_id": "salary", "value": "x"})
    assert unknown.status_code == 422

    incomplete = await client.post("/api/v1/onboarding/complete")
    assert incomplete.json()["error"]["code"] == "quiz_incomplete"
    assert (await client.get("/api/v1/onboarding/preview")).status_code == 409

    # Another browser has no access to this draft.
    assert (await harness.client().get("/api/v1/onboarding/quiz")).json()["draft"] is None


async def test_link_opened_on_another_device_still_links_the_quiz(harness: Harness):
    laptop = harness.client()
    await take_quiz(laptop)
    token = await request_link(harness, laptop, "dev@example.com")
    assert "specialization" not in harness.email.links["dev@example.com"][-1]  # nothing but the token

    phone = harness.client()
    assert (await phone.post("/api/v1/auth/magic-link/verify", json={"token": token})).status_code == 200
    me = (await phone.get("/api/v1/me")).json()
    assert me["profile"]["specialization"] == ANSWERS["specialization"]
    assert (await laptop.get("/api/v1/me")).status_code == 401  # the session belongs to the phone


async def test_link_is_single_use_and_scanner_safe(harness: Harness):
    client = harness.client()
    await take_quiz(client)
    token = await request_link(harness, client, "dev@example.com")

    # A mail scanner that opens the link (page GET + inspect) any number of times consumes nothing.
    for _ in range(3):
        state = (await harness.client().post("/api/v1/auth/magic-link/inspect", json={"token": token})).json()
        assert state == {"status": "valid", "email_masked": "de*@example.com"}

    assert (await client.post("/api/v1/auth/magic-link/verify", json={"token": token})).status_code == 200
    reused = await harness.client().post("/api/v1/auth/magic-link/verify", json={"token": token})
    assert reused.status_code == 410
    assert reused.json()["error"]["code"] == "link_used"
    assert (await client.post("/api/v1/auth/magic-link/inspect", json={"token": token})).json()[
        "status"
    ] == "used"

    bogus = await client.post("/api/v1/auth/magic-link/verify", json={"token": "x" * 43})
    assert bogus.json()["error"]["code"] == "link_invalid"


async def test_expired_link_is_rejected(harness: Harness):
    client = harness.client()
    token = await request_link(harness, client, "dev@example.com")
    await execute(harness, "UPDATE magic_link_challenges SET expires_at = now() - interval '1 minute'")
    expired = await client.post("/api/v1/auth/magic-link/verify", json={"token": token})
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "link_expired"
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_draft_cannot_be_claimed_twice_or_by_someone_else(harness: Harness):
    client = harness.client()
    await take_quiz(client)
    first = await request_link(harness, client, "one@example.com")
    second = await request_link(harness, client, "two@example.com")

    assert (
        await harness.client().post("/api/v1/auth/magic-link/verify", json={"token": first})
    ).status_code == 200
    other = harness.client()
    assert (await other.post("/api/v1/auth/magic-link/verify", json={"token": second})).status_code == 200
    # The second account signs in, but the draft already belongs to the first.
    me = (await other.get("/api/v1/me")).json()
    assert me["onboarding_required"] is True
    assert (await other.get("/api/v1/journey")).json()["error"]["code"] == "onboarding_required"

    # It can take the quiz while signed in and attach it directly.
    await take_quiz(other)
    assert (await other.post("/api/v1/onboarding/claim")).json() == {"redirect": "/journey"}
    assert (await other.get("/api/v1/journey")).status_code == 200


async def test_same_email_never_creates_two_accounts(harness: Harness):
    first = harness.client()
    await take_quiz(first)
    await sign_in(harness, first, "Dev@Example.com")
    second = harness.client()
    await sign_in(harness, second, "dev@example.com")
    assert (await first.get("/api/v1/me")).json()["id"] == (await second.get("/api/v1/me")).json()["id"]


async def test_magic_link_rate_limit(harness: Harness):
    client = harness.client()
    for _ in range(harness.settings.magic_link_max_per_email_per_hour):
        assert (
            await client.post("/api/v1/auth/magic-link", json={"email": "dev@example.com"})
        ).status_code == 202
    limited = await client.post("/api/v1/auth/magic-link", json={"email": "dev@example.com"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert "retry-after" in limited.headers
    assert (await client.post("/api/v1/auth/magic-link", json={"email": "not-an-email"})).status_code == 422


async def test_email_outage_is_recoverable(harness: Harness):
    client = harness.client()
    harness.email.fail = True
    down = await client.post("/api/v1/auth/magic-link", json={"email": "dev@example.com"})
    assert down.status_code == 503
    assert down.json()["error"]["code"] == "email_delivery_failed"
    harness.email.fail = False
    assert (
        await client.post("/api/v1/auth/magic-link", json={"email": "dev@example.com"})
    ).status_code == 202


async def test_cross_origin_writes_are_rejected(harness: Harness):
    client = harness.client()
    evil = await client.post(
        "/api/v1/auth/magic-link",
        json={"email": "dev@example.com"},
        headers={"origin": "https://evil.example"},
    )
    assert evil.status_code == 403
    assert (await client.get("/api/v1/health")).json() == {"status": "ok", "database": "up"}
