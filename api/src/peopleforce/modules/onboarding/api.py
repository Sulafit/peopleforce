from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response

from peopleforce.core.config import Settings
from peopleforce.core.errors import AppError
from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.curriculum.service import CurriculumService
from peopleforce.modules.onboarding import quiz
from peopleforce.modules.onboarding.models import OnboardingDraft
from peopleforce.modules.onboarding.schemas import (
    AnswerIn,
    ClaimOut,
    DraftOut,
    OptionOut,
    PreviewOut,
    QuestionOut,
    QuizOut,
)
from peopleforce.modules.onboarding.service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"], route_class=DishkaRoute)

QUESTIONS_OUT = [
    QuestionOut(
        id=q.id,
        title=q.title,
        kind=q.kind,
        helper=q.helper,
        options=[OptionOut(**vars(o)) for o in q.options],
    )
    for q in quiz.QUESTIONS
]


def _draft_out(draft: OnboardingDraft | None) -> DraftOut | None:
    if draft is None:
        return None
    return DraftOut(status=draft.status, answers=draft.answers)  # type: ignore[arg-type]


def set_onboarding_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.onboarding_cookie_name,
        token,
        max_age=settings.onboarding_draft_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_onboarding_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.onboarding_cookie_name, path="/")


@router.get("/quiz", response_model=QuizOut)
async def get_quiz(request: Request, settings: FromDishka[Settings], service: FromDishka[OnboardingService]):
    """The seven questions plus any answers already saved for this browser (resume after refresh)."""
    draft = await service.find_draft(request.cookies.get(settings.onboarding_cookie_name))
    return QuizOut(questions=QUESTIONS_OUT, draft=_draft_out(draft))


@router.put("/answers", response_model=DraftOut)
async def save_answer(
    body: AnswerIn,
    request: Request,
    response: Response,
    settings: FromDishka[Settings],
    service: FromDishka[OnboardingService],
):
    draft, issued = await service.save_answer(
        request.cookies.get(settings.onboarding_cookie_name), body.question_id, body.value
    )
    if issued:
        set_onboarding_cookie(response, settings, issued)
    return _draft_out(draft)


@router.post("/complete", response_model=PreviewOut)
async def complete_quiz(
    request: Request,
    settings: FromDishka[Settings],
    service: FromDishka[OnboardingService],
    curriculum: FromDishka[CurriculumService],
):
    draft = await service.complete(request.cookies.get(settings.onboarding_cookie_name))
    return service.preview(draft, await curriculum.get_path())


@router.get("/preview", response_model=PreviewOut)
async def get_preview(
    request: Request,
    settings: FromDishka[Settings],
    service: FromDishka[OnboardingService],
    curriculum: FromDishka[CurriculumService],
):
    draft = await service.require_completed(request.cookies.get(settings.onboarding_cookie_name))
    return service.preview(draft, await curriculum.get_path())


@router.post("/claim", response_model=ClaimOut)
async def claim_for_signed_in_user(
    request: Request,
    response: Response,
    user: FromDishka[CurrentUser],
    settings: FromDishka[Settings],
    service: FromDishka[OnboardingService],
    curriculum: FromDishka[CurriculumService],
):
    """Attach the finished quiz to the signed-in account (no email round trip needed)."""
    draft = await service.require_completed(request.cookies.get(settings.onboarding_cookie_name))
    path = await curriculum.get_path()
    if not await service.claim_and_commit(draft.id, user.id, path.id):
        raise AppError("draft_not_found", "Your answers were not found. Please start the quiz again.", 404)
    clear_onboarding_cookie(response, settings)
    return ClaimOut(redirect="/journey")
