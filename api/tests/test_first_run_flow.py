"""The non-negotiable journey: quiz -> preview -> magic link -> journey -> lesson -> avatar -> XP."""

import asyncio

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from peopleforce.modules.gamification.models import XpEvent

from .conftest import OFFER, Harness, finish_first_lesson, onboard, sign_in, take_quiz

LESSON = "define-your-offer"
NEXT = "spot-a-strong-offer"


async def xp_rows(harness: Harness) -> int:
    engine = create_async_engine(harness.settings.database_url)
    async with engine.connect() as connection:
        count = await connection.scalar(select(func.count()).select_from(XpEvent))
    await engine.dispose()
    return count or 0


async def test_full_first_run_journey(harness: Harness):
    client = harness.client()

    preview = await take_quiz(client)
    assert preview["headline"] == "Your path from backend developer to independent freelancer"
    assert preview["milestones"][3] == "Prepare your Upwork profile"

    assert (await client.get("/api/v1/me")).status_code == 401

    verified = await sign_in(harness, client, "dev@example.com")
    assert verified == {"redirect": "/journey", "is_new_user": True}

    me = (await client.get("/api/v1/me")).json()
    assert me["onboarding_required"] is False
    assert me["profile"]["specialization"] == "backend"
    assert me["profile"]["avatar_key"] is None

    journey = (await client.get("/api/v1/journey")).json()
    assert journey["tour"] == {"stage": "journey_intro", "status": "active"}
    assert journey["current_lesson_id"] == LESSON
    assert journey["xp_total"] == 0
    first, second = journey["chapters"][0]["lessons"][:2]
    assert (first["status"], second["status"], first["started"]) == ("current", "locked", False)

    lesson = (await client.post(f"/api/v1/journey/lessons/{LESSON}/start")).json()
    assert lesson["tour"]["stage"] == "first_lesson_started"
    assert lesson["completable"] is False
    # Personalized example for a backend developer, and no quiz answers leaked anywhere.
    draft = next(a for a in lesson["actions"] if a["key"] == "offer-draft")
    assert draft["config"]["fields"][0]["example"] == "APIs and integrations between business tools"

    completed = await finish_first_lesson(client)
    assert completed["status"] == "reward_pending"
    assert completed["reward"] is None
    assert completed["tour"]["stage"] == "avatar_selection"
    assert await xp_rows(harness) == 0  # no XP before the avatar

    journey = (await client.get("/api/v1/journey")).json()
    assert journey["pending_reward_lesson_id"] == LESSON
    assert journey["chapters"][0]["lessons"][1]["status"] == "locked"

    avatar = (await client.put("/api/v1/me/avatar", json={"avatar_key": "fox"})).json()
    assert avatar["reward"]["xp_awarded"] == 40
    assert avatar["reward"]["xp_total"] == 40
    assert avatar["reward"]["next_lesson"]["id"] == NEXT
    assert {a["key"] for a in avatar["reward"]["achievements"]} == {"first-step"}
    assert avatar["tour"]["stage"] == "first_reward_claimed"

    journey = (await client.get("/api/v1/journey")).json()
    assert journey["xp_total"] == 40
    assert journey["current_lesson_id"] == NEXT
    assert journey["pending_reward_lesson_id"] is None
    assert journey["last_reward"]["xp_awarded"] == 40  # celebration survives a refresh
    assert journey["profile"]["avatar_key"] == "fox"
    earned = {a["key"] for a in journey["achievements"] if a["earned"]}
    assert earned == {"first-step", "identity-created"}

    tour = (await client.post("/api/v1/tour/events", json={"event": "reward_acknowledged"})).json()
    assert tour["stage"] == "next_lesson_prompt"
    tour = (await client.post("/api/v1/tour/events", json={"event": "next_prompt_acknowledged"})).json()
    assert tour == {"stage": "completed", "status": "completed"}

    # Returning user: nothing repeats.
    await client.post("/api/v1/auth/logout")
    assert (await client.get("/api/v1/journey")).status_code == 401
    again = await sign_in(harness, client, "dev@example.com")
    assert again["is_new_user"] is False
    journey = (await client.get("/api/v1/journey")).json()
    assert journey["tour"]["status"] == "completed"
    assert journey["xp_total"] == 40
    assert journey["last_reward"] is None


async def test_xp_is_paid_once_under_repeats_and_concurrency(harness: Harness):
    client = await onboard(harness)
    await finish_first_lesson(client)

    results = await asyncio.gather(
        *[client.put("/api/v1/me/avatar", json={"avatar_key": "owl"}) for _ in range(5)]
    )
    assert all(r.status_code == 200 for r in results)
    assert sum(1 for r in results if r.json()["reward"]) == 1
    assert await xp_rows(harness) == 1

    repeats = await asyncio.gather(
        *[client.post(f"/api/v1/journey/lessons/{LESSON}/complete") for _ in range(5)]
    )
    assert all(r.status_code == 200 and r.json()["already_completed"] for r in repeats)
    assert await xp_rows(harness) == 1
    assert (await client.get("/api/v1/journey")).json()["xp_total"] == 40


async def test_interrupted_before_avatar_resumes_after_relogin(harness: Harness):
    client = await onboard(harness)
    await finish_first_lesson(client)
    await client.post("/api/v1/auth/logout")

    other_device = harness.client()
    await sign_in(harness, other_device, "dev@example.com")
    journey = (await other_device.get("/api/v1/journey")).json()
    assert journey["pending_reward_lesson_id"] == LESSON
    assert journey["tour"]["stage"] == "avatar_selection"

    # The saved work is intact.
    lesson = (await other_device.get(f"/api/v1/journey/lessons/{LESSON}")).json()
    assert lesson["progress_status"] == "reward_pending"
    draft = next(a for a in lesson["actions"] if a["key"] == "offer-draft")
    assert draft["state"]["payload"] == OFFER

    avatar = (await other_device.put("/api/v1/me/avatar", json={"avatar_key": "cat"})).json()
    assert avatar["reward"]["xp_awarded"] == 40


async def test_skipping_the_tour_blocks_nothing(harness: Harness):
    client = await onboard(harness)
    await client.get("/api/v1/journey")
    tour = (await client.post("/api/v1/tour/events", json={"event": "skip"})).json()
    assert tour["status"] == "skipped"

    assert (await finish_first_lesson(client))["status"] == "reward_pending"
    avatar = (await client.put("/api/v1/me/avatar", json={"avatar_key": "bear"})).json()
    assert avatar["reward"]["xp_awarded"] == 40
    assert avatar["tour"]["status"] == "skipped"

    replay = (await client.post("/api/v1/tour/events", json={"event": "replay"})).json()
    assert replay == {"stage": "next_lesson_prompt", "status": "active"}


async def test_later_lessons_pay_immediately_and_unlock_in_order(harness: Harness):
    client = await onboard(harness)

    # Locked until the first lesson is completed (reward included).
    assert (await client.get(f"/api/v1/journey/lessons/{NEXT}")).status_code == 403
    assert (await client.post(f"/api/v1/journey/lessons/{NEXT}/start")).status_code == 403
    await finish_first_lesson(client)
    assert (await client.get(f"/api/v1/journey/lessons/{NEXT}")).status_code == 403
    await client.put("/api/v1/me/avatar", json={"avatar_key": "fox"})

    base = f"/api/v1/journey/lessons/{NEXT}"
    lesson = (await client.post(f"{base}/start")).json()
    quiz = next(a for a in lesson["actions"] if a["key"] == "offer-quiz")
    assert "correct_option_id" not in str(quiz["config"])  # answers never reach the client

    incomplete = await client.post(f"{base}/complete")
    assert incomplete.status_code == 409
    assert incomplete.json()["error"]["code"] == "lesson_incomplete"

    failed = (
        await client.post(
            f"{base}/actions/offer-quiz", json={"payload": {"answers": {"q1": "a", "q2": "a", "q3": "b"}}}
        )
    ).json()
    assert failed["action"]["state"]["completed"] is False
    passed = (
        await client.post(
            f"{base}/actions/offer-quiz", json={"payload": {"answers": {"q1": "b", "q2": "c", "q3": "a"}}}
        )
    ).json()
    assert passed["action"]["state"]["result"]["passed"] is True
    done = (await client.post(f"{base}/actions/one-service", json={"payload": {}})).json()
    assert done["completable"] is True

    completed = (await client.post(f"{base}/complete")).json()
    assert completed["status"] == "completed"
    assert completed["reward"]["xp_awarded"] == 30
    assert completed["reward"]["xp_total"] == 70
    assert completed["reward"]["next_lesson"]["id"] == "write-your-bio"


async def test_invalid_submission_is_rejected_with_field_errors(harness: Harness):
    client = await onboard(harness)
    base = f"/api/v1/journey/lessons/{LESSON}"
    await client.post(f"{base}/start")
    response = await client.post(
        f"{base}/actions/offer-draft", json={"payload": {"values": {"what-you-build": "x"}}}
    )
    assert response.status_code == 422
    fields = response.json()["error"]["details"]["fields"]
    assert set(fields) == {"what-you-build", "who-needs-it", "problem-solved", "relevant-experience"}

    # Saving the asset needs a valid draft first.
    blocked = await client.post(f"{base}/actions/save-offer", json={"payload": {}})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "dependency_not_met"
    assert (await client.put("/api/v1/me/avatar", json={"avatar_key": "dragon"})).status_code == 422


async def test_ai_failure_keeps_the_submission_and_the_lesson_completable(harness: Harness):
    client = await onboard(harness)
    base = f"/api/v1/journey/lessons/{LESSON}"
    await client.post(f"{base}/start")
    await client.post(f"{base}/actions/offer-draft", json={"payload": OFFER})

    harness.llm.fail = True
    failed = await client.post(f"{base}/actions/offer-feedback", json={"payload": {}})
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "ai_unavailable"

    lesson = (await client.get(f"/api/v1/journey/lessons/{LESSON}")).json()
    draft = next(a for a in lesson["actions"] if a["key"] == "offer-draft")
    assert draft["state"]["payload"] == OFFER

    harness.llm.fail = False
    ok = (await client.post(f"{base}/actions/offer-feedback", json={"payload": {}})).json()
    assert ok["action"]["state"]["result"]["feedback"]["clarity_score"] == 4
    # The model saw the learner's answers and labels, never the email.
    assert "dev@example.com" not in harness.llm.calls[-1]["user"]
    assert "Backend / APIs" in harness.llm.calls[-1]["user"]

    await client.post(f"{base}/actions/save-offer", json={"payload": {}})
    assert (await client.post(f"{base}/complete")).json()["status"] == "reward_pending"

    engine = create_async_engine(harness.settings.database_url)
    async with engine.connect() as connection:
        statuses = (
            (await connection.execute(text("SELECT status FROM ai_generations ORDER BY created_at")))
            .scalars()
            .all()
        )
    await engine.dispose()
    assert statuses == ["failed", "succeeded"]


async def test_platform_draft_is_a_draft_until_approved(harness: Harness):
    client = await onboard(harness)
    early = await client.post("/api/v1/assets/platform-draft")
    assert early.json()["error"]["code"] == "offer_required"

    await finish_first_lesson(client)
    draft = (await client.post("/api/v1/assets/platform-draft")).json()
    assert draft["platform_label"] == "Upwork profile"
    assert (draft["asset"]["status"], draft["asset"]["origin"]) == ("draft", "ai")

    approved = (await client.post(f"/api/v1/assets/{draft['asset']['id']}/approve")).json()
    assert approved["status"] == "approved"

    stranger = await onboard(harness, "other@example.com")
    assert (await stranger.post(f"/api/v1/assets/{draft['asset']['id']}/approve")).status_code == 404


async def test_daily_challenge_pays_once_and_feeds_streak_and_rank(harness: Harness):
    client = await onboard(harness)
    assert (await client.put("/api/v1/me/timezone", json={"timezone": "America/Chicago"})).status_code == 204
    assert (await client.put("/api/v1/me/timezone", json={"timezone": "Mars/Olympus"})).status_code == 422

    daily = (await client.get("/api/v1/daily")).json()
    assert daily["completed"] is False
    assert (daily["streak"]["current"], daily["streak"]["active_today"]) == (0, False)
    challenge = daily["challenge"]
    # The same challenge comes back on every request for the day.
    assert (await client.get("/api/v1/daily")).json()["challenge"]["key"] == challenge["key"]

    # Daily challenges are real-world tasks with a self-reported count ("write to 5 clients").
    assert challenge["action"]["type"] == "external_task"
    target = challenge["action"]["config"]["target_count"]
    xp = challenge["xp"]
    assert (
        await client.post("/api/v1/daily/submit", json={"payload": {"count": target + 1}})
    ).status_code == 422
    assert (await client.post("/api/v1/daily/submit", json={"payload": {"count": "many"}})).status_code == 422

    # Partial progress is saved and pays nothing yet.
    if target > 1:
        part = (await client.post("/api/v1/daily/submit", json={"payload": {"count": target - 1}})).json()
        assert (part["daily"]["completed"], part["xp_awarded"]) == (False, 0)
        saved = (await client.get("/api/v1/daily")).json()
        assert saved["challenge"]["action"]["state"]["payload"] == {"count": target - 1}
        assert saved["streak"]["current"] == 0

    done = (await client.post("/api/v1/daily/submit", json={"payload": {"count": target}})).json()
    assert done["daily"]["completed"] and done["xp_awarded"] == xp and done["xp_total"] == xp
    assert done["daily"]["streak"]["current"] == 1 and done["daily"]["streak"]["active_today"] is True

    again = await asyncio.gather(
        *[client.post("/api/v1/daily/submit", json={"payload": {"count": target}}) for _ in range(4)]
    )
    assert all(r.status_code == 200 and r.json()["xp_awarded"] == 0 for r in again)
    assert await xp_rows(harness) == 1

    # Lesson XP on top moves the learner up a rank (daily XP + 40 >= 40).
    await finish_first_lesson(client)
    reward = (await client.put("/api/v1/me/avatar", json={"avatar_key": "fox"})).json()["reward"]
    assert reward["rank_up"] is True and reward["rank"]["title"] == "Explorer"

    journey = (await client.get("/api/v1/journey")).json()
    assert journey["rank"]["number"] == 2 and journey["streak"]["current"] == 1
    assert journey["more_coming"]

    page = (await client.get("/api/v1/profile")).json()
    assert page["xp_total"] == xp + 40
    assert [r["title"] for r in page["ranks"] if r["reached"]] == ["Newcomer", "Explorer"]
    assert {a["asset_type"] for a in page["assets"]} == {"freelancer_offer"}
    assert len(page["streak"]["week"]) == 7 and page["streak"]["week"][-1]["active"] is True
