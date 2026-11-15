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


class PreviewStop(BaseModel):
    title: str
    theme: str


class PreviewOut(BaseModel):
    headline: str
    subline: str
    # "Today, from your answers": statements that restate the quiz answers.
    today: list[str]
    # The chapters as numbered stops, and the rounded time to walk them.
    stops: list[PreviewStop]
    hours: int
    # "After your journey": one concrete thing per chapter.
    kit: list[str]
    first_lesson_title: str
    first_lesson_minutes: int


class ClaimOut(BaseModel):
    redirect: str
