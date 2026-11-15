from typing import Any, Literal

from pydantic import BaseModel


class OptionOut(BaseModel):
    value: str
    label: str
    disabled: bool = False
    note: str | None = None
    exclusive: bool = False


class QuestionOut(BaseModel):
    id: str
    title: str
    kind: Literal["single", "multi"]
    helper: str | None = None
    options: list[OptionOut]


class DraftOut(BaseModel):
    status: Literal["in_progress", "completed"]
    answers: dict[str, Any]


class QuizOut(BaseModel):
    questions: list[QuestionOut]
    draft: DraftOut | None


class AnswerIn(BaseModel):
    question_id: str
    value: str | list[str]


class PreviewChapter(BaseModel):
    title: str
    theme: str
    blurb: str
    lesson_count: int


class PreviewOut(BaseModel):
    headline: str
    specialization_label: str
    stage_label: str
    stage_line: str
    goal_label: str
    channel_label: str
    milestones: list[str]
    chapters: list[PreviewChapter]
    first_lesson_title: str
    first_lesson_minutes: int
    total_lessons: int


class ClaimOut(BaseModel):
    redirect: str
