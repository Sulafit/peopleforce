"""Pure progression rules. No I/O, so they are trivially testable and UI-independent."""

from typing import Literal

from peopleforce.modules.actions.handlers import ActionState
from peopleforce.modules.curriculum.schemas import Lesson

LessonStatus = Literal["done", "current", "locked"]
ProgressStatus = Literal["not_started", "in_progress", "reward_pending", "completed"]


def lesson_statuses(lesson_ids: list[str], progress: dict[str, str]) -> dict[str, LessonStatus]:
    """Sequential unlocking: completed lessons are done, the first unfinished one is current.

    A lesson whose reward is pending is still `current`: it is not completed until the reward is paid.
    """
    statuses: dict[str, LessonStatus] = {}
    current_found = False
    for lesson_id in lesson_ids:
        if progress.get(lesson_id) == "completed":
            statuses[lesson_id] = "done"
        elif not current_found:
            statuses[lesson_id] = "current"
            current_found = True
        else:
            statuses[lesson_id] = "locked"
    return statuses


def missing_required_actions(lesson: Lesson, states: dict[str, ActionState]) -> list[str]:
    if lesson.content is None:
        return []
    return [
        a.key for a in lesson.content.actions if a.required and not states.get(a.key, ActionState()).completed
    ]


def unmet_dependencies(lesson: Lesson, action_key: str, states: dict[str, ActionState]) -> list[str]:
    action = lesson.action(action_key)
    if action is None:
        return []
    requires = list(action.depends_on)
    source = getattr(action, "source_action_key", None)
    if source and source not in requires:
        requires.append(source)
    return [key for key in requires if not states.get(key, ActionState()).completed]


def is_stale(lesson: Lesson, action_key: str, states: dict[str, ActionState]) -> bool:
    """True when an action's source was resubmitted after the action last ran (e.g. unsaved edits)."""
    action = lesson.action(action_key)
    source_key = getattr(action, "source_action_key", None)
    state = states.get(action_key)
    source = states.get(source_key) if source_key else None
    if not state or not source or not state.updated_at or not source.updated_at:
        return False
    return source.updated_at > state.updated_at
