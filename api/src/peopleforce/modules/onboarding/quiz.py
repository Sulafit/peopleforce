"""The seven-question personalization quiz and the deterministic profile derived from it.

No AI here: the profile is a direct mapping of explicit answers.
"""

from dataclasses import dataclass
from typing import Any, Literal

from adaptix import Retort

from peopleforce.core.errors import AppError


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    disabled: bool = False
    note: str | None = None
    exclusive: bool = False  # multi-select: choosing it clears the others


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    kind: Literal["single", "multi"]
    options: tuple[Option, ...]
    helper: str | None = None

    def option(self, value: str) -> Option | None:
        return next((o for o in self.options if o.value == value), None)


QUESTIONS: tuple[Question, ...] = (
    Question(
        id="domain",
        title="What skill do you want to freelance with?",
        kind="single",
        options=(
            Option("software_development", "Software Development"),
            Option("design", "Design", disabled=True, note="Coming soon"),
            Option("marketing", "Marketing", disabled=True, note="Coming soon"),
            Option("writing", "Writing", disabled=True, note="Coming soon"),
        ),
    ),
    Question(
        id="specialization",
        title="What kind of software do you build?",
        kind="single",
        options=(
            Option("websites", "Websites"),
            Option("web_apps", "Web applications"),
            Option("mobile_apps", "Mobile applications"),
            Option("backend", "Backend / APIs"),
            Option("automation", "Automation"),
            Option("not_sure", "Not sure"),
        ),
    ),
    Question(
        id="experience_level",
        title="How experienced are you?",
        kind="single",
        options=(
            Option("learning", "Currently learning"),
            Option("under_1_year", "Less than 1 year"),
            Option("1_3_years", "1–3 years"),
            Option("over_3_years", "More than 3 years"),
        ),
    ),
    Question(
        id="freelance_stage",
        title="Have you freelanced before?",
        kind="single",
        options=(
            Option("never", "Never"),
            Option("tried_no_clients", "Tried, but no clients"),
            Option("few_projects", "Completed 1–2 projects"),
            Option("recurring_clients", "Already have recurring clients"),
        ),
    ),
    Question(
        id="existing_assets",
        title="What do you already have?",
        kind="multi",
        helper="Pick all that apply.",
        options=(
            Option("portfolio_website", "A portfolio"),
            Option("work_samples", "Work samples"),
            Option("upwork_profile", "An Upwork profile"),
            Option("fiverr_profile", "A Fiverr profile"),
            Option("linkedin_presence", "A LinkedIn presence"),
            Option("none", "None of these yet", exclusive=True),
        ),
    ),
    Question(
        id="acquisition_channel",
        title="Where do you want to find clients?",
        kind="single",
        options=(
            Option("upwork", "Upwork"),
            Option("fiverr", "Fiverr"),
            Option("linkedin", "LinkedIn"),
            Option("direct", "Direct clients"),
            Option("not_sure", "Not sure"),
        ),
    ),
    Question(
        id="primary_goal",
        title="What's your main goal?",
        kind="single",
        options=(
            Option("first_client", "Get my first client"),
            Option("more_clients", "Get more clients"),
            Option("higher_paying", "Find higher-paying projects"),
            Option("side_business", "Build a side business"),
        ),
    ),
)

QUESTIONS_BY_ID = {q.id: q for q in QUESTIONS}


@dataclass(frozen=True)
class PersonalizationProfile:
    domain: str
    specialization: str
    experience_level: str
    freelance_stage: str
    existing_assets: list[str]
    acquisition_channel: str
    primary_goal: str


_retort = Retort()


def load_profile(data: dict[str, Any]) -> PersonalizationProfile:
    return _retort.load(data, PersonalizationProfile)


def dump_profile(profile: PersonalizationProfile) -> dict[str, Any]:
    return _retort.dump(profile)


def validate_answer(question_id: str, value: Any) -> str | list[str]:
    """Return the normalized answer or raise AppError('invalid_answer')."""
    question = QUESTIONS_BY_ID.get(question_id)
    if question is None:
        raise AppError("invalid_answer", "Unknown question.", 422, {"question_id": question_id})

    def bad(message: str) -> AppError:
        return AppError("invalid_answer", message, 422, {"question_id": question_id})

    if question.kind == "single":
        if not isinstance(value, str):
            raise bad("Choose one option.")
        option = question.option(value)
        if option is None:
            raise bad("Choose one of the listed options.")
        if option.disabled:
            raise bad(f"{option.label} is not available yet.")
        return value

    if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
        raise bad("Choose at least one option.")
    unique = list(dict.fromkeys(value))
    options = [question.option(v) for v in unique]
    if any(o is None or o.disabled for o in options):
        raise bad("Choose from the listed options.")
    if len(unique) > 1 and any(o.exclusive for o in options if o):
        raise bad("“None” cannot be combined with other options.")
    return unique


def build_profile(answers: dict[str, Any]) -> PersonalizationProfile:
    """All seven answers are required; each is re-validated so stored drafts cannot bypass the rules."""
    missing = [q.id for q in QUESTIONS if q.id not in answers]
    if missing:
        raise AppError("quiz_incomplete", "Answer every question first.", 422, {"missing": missing})
    normalized = {q.id: validate_answer(q.id, answers[q.id]) for q in QUESTIONS}
    return load_profile(normalized)


def label(question_id: str, value: str) -> str:
    option = QUESTIONS_BY_ID[question_id].option(value)
    return option.label if option else value


# ---------- Personalized copy (deterministic) ----------

ROLE = {
    "websites": "website developer",
    "web_apps": "web application developer",
    "mobile_apps": "mobile developer",
    "backend": "backend developer",
    "automation": "automation developer",
    "not_sure": "software developer",
}

STAGE_LINE = {
    "never": "You're starting from zero, so the path begins with the basics clients look for.",
    "tried_no_clients": (
        "You've tried before without landing a client. The path focuses on a clearer offer first."
    ),
    "few_projects": "You've finished a project or two. The path helps you turn that into repeatable proof.",
    "recurring_clients": "You already have clients. The path sharpens your positioning to reach better ones.",
}

GOAL_LINE = {
    "first_client": "Goal: get your first client.",
    "more_clients": "Goal: get more clients.",
    "higher_paying": "Goal: find higher-paying projects.",
    "side_business": "Goal: build a side business.",
}

CHANNEL_MILESTONE = {
    "upwork": "Prepare your Upwork profile",
    "fiverr": "Prepare your Fiverr gig",
    "linkedin": "Prepare your LinkedIn presence",
    "direct": "Prepare your pitch for direct clients",
    "not_sure": "Prepare marketplace profiles",
}


def role_label(profile: PersonalizationProfile) -> str:
    return ROLE.get(profile.specialization, "software developer")


def milestones(profile: PersonalizationProfile) -> list[str]:
    return [
        "Define your freelance offer",
        "Demonstrate your work",
        "Build your professional presence",
        CHANNEL_MILESTONE.get(profile.acquisition_channel, "Prepare marketplace profiles"),
        "Start approaching clients",
    ]


# ---------- Journey preview copy (deterministic, from explicit answers only) ----------

STAGE_PHRASE = {
    "never": "never freelanced",
    "tried_no_clients": "tried, no clients yet",
    "few_projects": "a project or two",
    "recurring_clients": "a few steady clients",
}

STAGE_TODAY = {
    "never": "Never freelanced before",
    "tried_no_clients": "Tried freelancing, no clients yet",
    "few_projects": "One or two freelance projects done",
    "recurring_clients": "Recurring clients, ready for better ones",
}

MAKES = {
    "websites": "websites",
    "web_apps": "web apps",
    "mobile_apps": "mobile apps",
    "backend": "backends and APIs",
    "automation": "automations",
    "not_sure": "software",
}


def preview_headline(profile: PersonalizationProfile) -> str:
    return f"From “{STAGE_PHRASE[profile.freelance_stage]}” to client-ready"


def preview_subline(profile: PersonalizationProfile, stops: int) -> str:
    makes = MAKES.get(profile.specialization, "software")
    return f"That is the trip your {stops} stops are built for, planned around the {makes} you already make."


def today_from_answers(profile: PersonalizationProfile) -> list[str]:
    """Where the learner stands today, in their own answers. Nothing is inferred beyond them."""
    has = set(profile.existing_assets)
    early = profile.freelance_stage in ("never", "tried_no_clients")
    lines = [STAGE_TODAY[profile.freelance_stage]]
    if "upwork_profile" in has:
        lines.append("An Upwork profile, no work from it yet" if early else "An Upwork profile")
    if "fiverr_profile" in has:
        lines.append("A Fiverr profile, no orders from it yet" if early else "A Fiverr profile")
    if "linkedin_presence" in has:
        lines.append("A LinkedIn presence")
    if "work_samples" in has:
        lines.append("Work samples" if "portfolio_website" in has else "Work samples nobody has seen")
    lines.append("A portfolio website" if "portfolio_website" in has else "No portfolio page")
    return lines
