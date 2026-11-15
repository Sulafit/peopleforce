import copy
import json
from typing import Any

import pytest

from peopleforce.core.errors import AppError
from peopleforce.infrastructure.cms.sanity import normalize
from peopleforce.modules.curriculum.service import SEED_DIR, CurriculumService, LocalContentSource, parse_path
from peopleforce.modules.progression.engine import lesson_statuses


def seed() -> dict[str, Any]:
    return json.loads((SEED_DIR / "software-development.json").read_text())


def test_seed_content_is_valid_and_first_chapter_is_playable():
    path = parse_path(seed())
    assert [lesson.playable for lesson in path.chapters[0].lessons] == [True, True, True]
    assert path.first_lesson_id == "define-your-offer"


def test_a_broken_lesson_becomes_unplayable_instead_of_breaking_the_path():
    raw = seed()
    lesson = raw["chapters"][0]["lessons"][0]
    lesson["content"]["actions"][2]["source_action_key"] = "missing"
    lesson["content"]["blocks"].append({"type": "run_python", "key": "x", "code": "import os"})
    path = parse_path(raw)
    assert path.lessons[0].playable is False
    assert path.lessons[0].content_error
    assert path.lessons[1].playable is True


def test_unimplemented_completion_strategy_is_not_playable():
    raw = seed()
    raw["chapters"][0]["lessons"][0]["content"]["actions"][2]["completion"] = "asset_published"
    assert parse_path(raw).lessons[0].playable is False


def test_lesson_version_changes_with_content():
    raw = seed()
    before = parse_path(raw).lessons[0].version
    edited = copy.deepcopy(raw)
    edited["chapters"][0]["lessons"][0]["content"]["blocks"][0]["body"] += " Edited."
    assert parse_path(edited).lessons[0].version != before
    assert parse_path(raw).lessons[0].version == before


def test_sequential_unlocking():
    ids = ["a", "b", "c"]
    assert lesson_statuses(ids, {}) == {"a": "current", "b": "locked", "c": "locked"}
    assert lesson_statuses(ids, {"a": "reward_pending"}) == {"a": "current", "b": "locked", "c": "locked"}
    assert lesson_statuses(ids, {"a": "completed", "b": "in_progress"}) == {
        "a": "done",
        "b": "current",
        "c": "locked",
    }
    assert lesson_statuses(ids, dict.fromkeys(ids, "completed")) == dict.fromkeys(ids, "done")


class FlakySource:
    name = "flaky"

    def __init__(self) -> None:
        self.fail = False

    async def fetch_path(self, domain: str):
        if self.fail:
            raise ConnectionError("cms down")
        return seed()


async def test_cms_outage_serves_last_good_copy_then_seed_fallback():
    source = FlakySource()
    service = CurriculumService(source, fallback=LocalContentSource(), ttl_seconds=0)
    assert (await service.get_path()).id == "software-development-freelancer"
    source.fail = True
    assert (await service.get_path()).id == "software-development-freelancer"  # stale copy

    cold = CurriculumService(source, fallback=LocalContentSource(), ttl_seconds=0)
    assert (await cold.get_path()).id == "software-development-freelancer"  # bundled seed

    with pytest.raises(AppError) as error:
        await CurriculumService(source, fallback=None, ttl_seconds=0).get_path()
    assert error.value.code == "content_unavailable"


def test_sanity_result_is_normalized_into_the_api_shape():
    """A GROQ result (Studio type names, nulls, key/value rows) parses into a playable lesson."""
    raw = {
        "id": "p",
        "domain": "software-development",
        "title": "Path",
        "avatars": ["fox"],
        "achievements": None,
        "chapters": [
            {
                "id": "c",
                "theme": "yellow",
                "tier": "Basics",
                "title": "C",
                "blurb": "B",
                "lessons": [
                    {
                        "id": "l",
                        "title": "L",
                        "minutes": 5,
                        "xp": 10,
                        "summary": "S",
                        "output": "O",
                        "parts": None,
                        "content": {
                            "blocks": [
                                {
                                    "type": "calloutBlock",
                                    "key": "tip",
                                    "body": "Default",
                                    "tone": None,
                                    "title": None,
                                    "body_by_specialization": [{"key": "backend", "value": "For backend"}],
                                },
                                {
                                    "type": "quizBlock",
                                    "key": "check",
                                    "action_keys": ["quiz", "draft", "save"],
                                },
                            ],
                            "actions": [
                                {
                                    "type": "quizAction",
                                    "key": "quiz",
                                    "title": "Q",
                                    "passing_score": None,
                                    "questions": [
                                        {
                                            "id": "q1",
                                            "prompt": "?",
                                            "correct_option_id": "a",
                                            "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                                        }
                                    ],
                                },
                                {
                                    "type": "textSubmissionAction",
                                    "key": "draft",
                                    "title": "D",
                                    "fields": [
                                        {
                                            "name": "text",
                                            "label": "Text",
                                            "min_length": None,
                                            "examples": [{"key": "default", "value": "Example"}],
                                        }
                                    ],
                                },
                                {
                                    "type": "saveAssetAction",
                                    "key": "save",
                                    "title": "S",
                                    "asset_type": "freelancer_offer",
                                    "source_action_key": "draft",
                                },
                            ],
                        },
                    }
                ],
            }
        ],
    }
    lesson = parse_path(normalize(raw)).lessons[0]
    assert lesson.playable, lesson.content_error
    assert [b.type for b in lesson.content.blocks] == ["callout", "quiz"]
    assert lesson.content.blocks[0].body_by_specialization == {"backend": "For backend"}
    assert [a.type for a in lesson.content.actions] == ["quiz", "text_submission", "save_asset"]
    assert lesson.content.actions[1].fields[0].examples == {"default": "Example"}


def test_sanity_daily_challenges_and_teaser_are_normalized():
    raw = seed()
    raw["more_coming"] = "Soon"
    raw["daily_challenges"] = [
        {
            "key": "d1",
            "title": "Daily",
            "xp": 10,
            "intro": None,
            "action": {
                "type": "quizAction",
                "key": "d1",
                "title": "Pick",
                "passing_score": None,
                "questions": [
                    {
                        "id": "q",
                        "prompt": "?",
                        "correct_option_id": "a",
                        "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                    }
                ],
            },
        }
    ]
    path = parse_path(normalize(raw))
    assert path.daily_challenges[0].action.type == "quiz"
    assert path.more_coming == "Soon"


def test_daily_challenge_cannot_use_lesson_only_actions():
    raw = seed()
    raw["daily_challenges"] = [
        {
            "key": "d",
            "title": "T",
            "action": {
                "type": "save_asset",
                "key": "d",
                "title": "S",
                "asset_type": "x",
                "source_action_key": "y",
            },
        }
    ]
    with pytest.raises(Exception):  # noqa: B017 - any validation error is fine here
        parse_path(raw)
