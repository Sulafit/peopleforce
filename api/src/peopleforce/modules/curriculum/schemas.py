"""Typed content model.

Content is authored in Sanity (or the local seed file) and treated as untrusted input: everything is
parsed through these models before use. Behaviour is never read from content; content only *selects*
among behaviours the backend implements (block types, action types, completion strategies, triggers).
"""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Key = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")]
Theme = Literal["yellow", "blue", "violet", "green", "orange", "pink"]

CompletionStrategy = Literal[
    "manual_confirmation",
    "valid_submission",
    "quiz_passing_score",
    "ai_feedback_received",
    "user_approved_submission",
    "asset_exists",
    "asset_published",
    "self_reported_count",
    "document_checked",
]

# Strategies that have a handler today. Lessons using anything else are reported as not playable.
IMPLEMENTED_STRATEGIES: frozenset[str] = frozenset(
    {
        "manual_confirmation",
        "valid_submission",
        "quiz_passing_score",
        "ai_feedback_received",
        "asset_exists",
        "self_reported_count",
        "document_checked",
    }
)


class ContentModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


# ---------- Blocks ----------


class MarkdownBlock(ContentModel):
    type: Literal["markdown"]
    key: Key
    title: str | None = None
    body: str


class YouTubeBlock(ContentModel):
    type: Literal["youtube"]
    key: Key
    title: str
    video_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{11}$")]
    # "In this video": a few lines on what the learner will see.
    points: list[str] = Field(default_factory=list, max_length=6)


class CalloutBlock(ContentModel):
    type: Literal["callout"]
    key: Key
    tone: Literal["info", "tip", "warning"] = "info"
    title: str | None = None
    body: str
    # Optional per-specialization replacement for `body` (keys are quiz specialization values).
    body_by_specialization: dict[str, str] = Field(default_factory=dict)


class ResourceLink(ContentModel):
    label: str
    url: Annotated[str, Field(pattern=r"^https://")]
    description: str | None = None


class ResourcesBlock(ContentModel):
    type: Literal["resources"]
    key: Key
    title: str | None = None
    links: list[ResourceLink]


class ActionGroupBlock(ContentModel):
    """Places one or more actions (by key) in the lesson flow. Also used for quiz and AI feedback."""

    type: Literal["action_group", "quiz", "ai_feedback"]
    key: Key
    title: str | None = None
    intro: str | None = None
    action_keys: list[Key] = Field(min_length=1)


Block = Annotated[
    MarkdownBlock | YouTubeBlock | CalloutBlock | ResourcesBlock | ActionGroupBlock,
    Field(discriminator="type"),
]


# ---------- Actions ----------


class ActionBase(ContentModel):
    key: Key
    title: str
    instructions: str | None = None
    required: bool = True
    depends_on: list[Key] = Field(default_factory=list)


class AcknowledgeAction(ActionBase):
    type: Literal["acknowledge"]
    confirm_label: str = "Got it"
    completion: Literal["manual_confirmation"] = "manual_confirmation"


class TextField(ContentModel):
    name: Key
    label: str
    help: str | None = None
    placeholder: str | None = None
    multiline: bool = True
    min_length: int = Field(default=1, ge=0, le=5000)
    max_length: int = Field(default=600, ge=1, le=5000)
    # Example answers keyed by quiz specialization; "default" is the fallback.
    examples: dict[str, str] = Field(default_factory=dict)
    # The answer must contain at least one number (results with numbers, e.g. in a case study).
    require_digit: bool = False

    @model_validator(mode="after")
    def _bounds(self) -> "TextField":
        if self.min_length > self.max_length:
            raise ValueError("min_length cannot exceed max_length")
        return self


class TextSubmissionAction(ActionBase):
    type: Literal["text_submission"]
    fields: list[TextField] = Field(min_length=1)
    submit_label: str = "Save draft"
    completion: Literal["valid_submission"] = "valid_submission"


class QuizOption(ContentModel):
    id: Key
    label: str


class QuizQuestion(ContentModel):
    id: Key
    prompt: str
    options: list[QuizOption] = Field(min_length=2)
    correct_option_id: Key
    explanation: str | None = None

    @model_validator(mode="after")
    def _correct_exists(self) -> "QuizQuestion":
        if self.correct_option_id not in {o.id for o in self.options}:
            raise ValueError("correct_option_id must be one of the options")
        return self


class QuizAction(ActionBase):
    type: Literal["quiz"]
    questions: list[QuizQuestion] = Field(min_length=1)
    passing_score: float = Field(default=0.7, gt=0, le=1)
    completion: Literal["quiz_passing_score"] = "quiz_passing_score"


class AiReviewAction(ActionBase):
    type: Literal["ai_review"]
    # Name in the backend capability registry. Prompts live in Langfuse / local files, not in content.
    capability: Key
    source_action_key: Key
    required: bool = False
    submit_label: str = "Get feedback"
    completion: Literal["ai_feedback_received"] = "ai_feedback_received"


class SaveAssetAction(ActionBase):
    type: Literal["save_asset"]
    asset_type: Key
    source_action_key: Key
    submit_label: str = "Save to my profile"
    completion: Literal["asset_exists", "asset_published"] = "asset_exists"


class ExternalTaskAction(ActionBase):
    """Something done outside the app a set number of times ("write to 5 clients").

    The learner reports their own count; the app cannot verify it and does not pretend to.
    """

    type: Literal["external_task"]
    target_count: int = Field(ge=1, le=20)
    # What one unit is, e.g. "message sent". Shown as "3 of 5".
    unit: str
    tips: list[str] = Field(default_factory=list, max_length=4)
    completion: Literal["self_reported_count"] = "self_reported_count"


class DocumentReviewAction(ActionBase):
    """The learner uploads a PDF (their résumé); the backend reads it and an AI capability scores it.

    Completed when the file is readable and looks like the expected document and, if `min_score` is
    set, the AI score reaches it. Without `min_score` the step never depends on AI being available.
    """

    type: Literal["document_review"]
    capability: Key
    min_score: int | None = Field(default=None, ge=0, le=100)
    # Saved to the profile as this asset type (a summary of the review, never the file itself).
    asset_type: Key | None = None
    submit_label: str = "Upload PDF"
    completion: Literal["document_checked"] = "document_checked"


Action = Annotated[
    AcknowledgeAction
    | TextSubmissionAction
    | QuizAction
    | AiReviewAction
    | SaveAssetAction
    | ExternalTaskAction
    | DocumentReviewAction,
    Field(discriminator="type"),
]


# ---------- Lessons, chapters, path ----------


class LessonPart(ContentModel):
    kind: Literal["Video", "Lesson", "Quiz", "Task", "Read", "Practice", "Create"]
    title: str
    minutes: int = Field(ge=1, le=240)


class LessonSummary(ContentModel):
    """What the journey map needs. Present for every lesson, including ones without playable content."""

    id: Key
    title: str
    minutes: int = Field(ge=1, le=600)
    xp: int = Field(ge=1, le=1000)
    summary: str
    parts: list[LessonPart] = Field(default_factory=list)
    output: str


class LessonContent(ContentModel):
    blocks: list[Block] = Field(min_length=1)
    actions: list[Action] = Field(default_factory=list)

    @model_validator(mode="after")
    def _references(self) -> "LessonContent":
        keys = [a.key for a in self.actions]
        if len(keys) != len(set(keys)):
            raise ValueError("action keys must be unique within a lesson")
        known = set(keys)
        by_key = {a.key: a for a in self.actions}
        placed: set[str] = set()
        for block in self.blocks:
            if isinstance(block, ActionGroupBlock):
                missing = set(block.action_keys) - known
                if missing:
                    raise ValueError(f"block {block.key} references unknown actions: {sorted(missing)}")
                placed.update(block.action_keys)
        for action in self.actions:
            refs = list(action.depends_on)
            source = getattr(action, "source_action_key", None)
            if source:
                refs.append(source)
            missing = set(refs) - known
            if missing:
                raise ValueError(f"action {action.key} references unknown actions: {sorted(missing)}")
            if action.key in refs:
                raise ValueError(f"action {action.key} cannot depend on itself")
            if source and not isinstance(by_key[source], TextSubmissionAction):
                raise ValueError(f"action {action.key}: source_action_key must be a text_submission")
            if action.required and action.key not in placed:
                raise ValueError(f"required action {action.key} is not placed in any block")
        return self

    @property
    def unsupported_strategies(self) -> list[str]:
        return sorted({a.completion for a in self.actions} - IMPLEMENTED_STRATEGIES)


class Lesson(LessonSummary):
    content: LessonContent | None = None
    # Why `content` is missing although the editor supplied some (validation message). Logged, not shown.
    content_error: str | None = None

    @property
    def playable(self) -> bool:
        return self.content is not None

    @property
    def version(self) -> str:
        """Content hash: changes whenever the published lesson changes."""
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def action(self, key: str) -> Action | None:
        if not self.content:
            return None
        return next((a for a in self.content.actions if a.key == key), None)


class Chapter(ContentModel):
    id: Key
    theme: Theme
    tier: str
    title: str
    blurb: str
    # What the learner has after this chapter; one line of the "client-ready kit" in the preview.
    outcome: str | None = None
    lessons: list[Lesson] = Field(min_length=1)


class LessonCompletedTrigger(ContentModel):
    type: Literal["lesson_completed"]
    lesson_id: Key


class LessonsCompletedCountTrigger(ContentModel):
    type: Literal["lessons_completed_count"]
    count: int = Field(ge=1)


class AssetCreatedTrigger(ContentModel):
    type: Literal["asset_created"]
    asset_type: Key


AchievementTrigger = Annotated[
    LessonCompletedTrigger | LessonsCompletedCountTrigger | AssetCreatedTrigger,
    Field(discriminator="type"),
]


class Achievement(ContentModel):
    key: Key
    title: str
    description: str
    trigger: AchievementTrigger


DailyAction = Annotated[
    AcknowledgeAction | TextSubmissionAction | QuizAction | ExternalTaskAction,
    Field(discriminator="type"),
]


class DailyChallenge(ContentModel):
    """A two-minute task. Reuses the action types that need no lesson context."""

    key: Key
    title: str
    intro: str | None = None
    xp: int = Field(default=10, ge=1, le=100)
    action: DailyAction


class LearningPath(ContentModel):
    id: Key
    domain: Key
    title: str
    chapters: list[Chapter] = Field(min_length=1)
    achievements: list[Achievement] = Field(default_factory=list)
    avatars: list[Key] = Field(min_length=1)
    daily_challenges: list[DailyChallenge] = Field(default_factory=list)
    # The path is open-ended: this line is shown after the last published level.
    more_coming: str | None = None

    @model_validator(mode="after")
    def _unique_ids(self) -> "LearningPath":
        ids = [lesson.id for chapter in self.chapters for lesson in chapter.lessons]
        if len(ids) != len(set(ids)):
            raise ValueError("lesson ids must be unique within a path")
        daily = [challenge.key for challenge in self.daily_challenges]
        if len(daily) != len(set(daily)):
            raise ValueError("daily challenge keys must be unique")
        return self

    @property
    def lessons(self) -> list[Lesson]:
        return [lesson for chapter in self.chapters for lesson in chapter.lessons]

    def lesson(self, lesson_id: str) -> Lesson | None:
        return next((lesson for lesson in self.lessons if lesson.id == lesson_id), None)

    @property
    def first_lesson_id(self) -> str:
        return self.chapters[0].lessons[0].id
