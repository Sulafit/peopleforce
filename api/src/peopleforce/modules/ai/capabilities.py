"""Typed AI capability registry.

Content (CMS) refers to a capability by name only. Everything that decides what the model is asked,
and what shape must come back, lives here in code.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


class Improvement(BaseModel):
    issue: str
    suggestion: str


class WritingFeedback(BaseModel):
    summary: str
    strengths: list[str] = Field(max_length=3)
    improvements: list[Improvement] = Field(max_length=3)
    clarity_score: int = Field(ge=1, le=5)
    specificity_score: int = Field(ge=1, le=5)
    suggested_one_liner: str


class ResumeCriterion(BaseModel):
    key: Literal["language", "length", "structure", "results", "relevance", "red_flags"]
    status: Literal["pass", "improve", "fix"]
    note: str


class ResumeReview(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    criteria: list[ResumeCriterion] = Field(min_length=6, max_length=6)
    top_issues: list[str] = Field(max_length=3)


class PlatformDraft(BaseModel):
    title: str
    body: str
    notes: list[str] = Field(max_length=3)


@dataclass(frozen=True)
class Capability:
    name: str
    kind: Literal["feedback", "generation"]
    prompt_name: str
    output_model: type[BaseModel]
    # Name of the trace in Langfuse. Verb first, never changes per run: evaluators and dashboards key on it.
    trace_name: str
    # Which saved assets the model may see. Empty means none.
    context_asset_types: tuple[str, ...] = ()
    prompt_label: str = "production"
    max_tokens: int = 4000
    timeout_seconds: float | None = None  # None: use the configured default


CAPABILITIES: dict[str, Capability] = {
    c.name: c
    for c in (
        Capability(
            name="freelance_offer_feedback",
            kind="feedback",
            prompt_name="freelance_offer_feedback",
            output_model=WritingFeedback,
            trace_name="review-freelance-offer",
        ),
        Capability(
            name="professional_bio_feedback",
            kind="feedback",
            prompt_name="professional_bio_feedback",
            output_model=WritingFeedback,
            trace_name="review-professional-bio",
            context_asset_types=("freelancer_offer",),
        ),
        Capability(
            name="resume_review",
            kind="feedback",
            prompt_name="resume_review",
            output_model=ResumeReview,
            trace_name="review-resume",
        ),
        Capability(
            name="generate_platform_draft",
            kind="generation",
            prompt_name="generate_platform_draft",
            output_model=PlatformDraft,
            trace_name="generate-platform-draft",
            context_asset_types=("freelancer_offer", "professional_bio"),
        ),
    )
}


@dataclass(frozen=True)
class Platform:
    key: str
    asset_type: str
    label: str
    requirements: str


# Format limits are the platforms' published limits at the time of writing; recheck before launch.
PLATFORMS: dict[str, Platform] = {
    "upwork": Platform(
        key="upwork",
        asset_type="upwork_profile_draft",
        label="Upwork profile",
        requirements=(
            "title: a professional title of at most 70 characters. "
            "body: a profile overview of 120-200 words; the first two lines must say who the freelancer "
            "helps and what they build, because only those lines show in search results."
        ),
    ),
    "fiverr": Platform(
        key="fiverr",
        asset_type="fiverr_gig_draft",
        label="Fiverr gig",
        requirements=(
            "title: a gig title that starts with 'I will' and is at most 80 characters. "
            "body: a gig description of 100-180 words covering what the buyer gets, who it is for, "
            "and what the freelancer needs from the buyer to start."
        ),
    ),
    "linkedin": Platform(
        key="linkedin",
        asset_type="linkedin_post_draft",
        label="LinkedIn post",
        requirements=(
            "title: a LinkedIn headline of at most 220 characters. "
            "body: a first LinkedIn post of 80-150 words announcing that the freelancer is available, "
            "what they build and for whom, ending with one clear way to get in touch."
        ),
    ),
}


def platform_for_channel(channel: str) -> Platform:
    """Direct clients and 'not sure' start with LinkedIn, the one channel that needs no marketplace."""
    return PLATFORMS.get(channel, PLATFORMS["linkedin"])
