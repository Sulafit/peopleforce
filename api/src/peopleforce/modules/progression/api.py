from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, UploadFile

from peopleforce.core.errors import AppError
from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.progression.schemas import (
    ActionSubmitIn,
    ActionSubmitOut,
    AvatarIn,
    AvatarOut,
    CompleteOut,
    JourneyOut,
    LessonOut,
    TourEventIn,
    TourOut,
)
from peopleforce.modules.progression.service import ProgressionService

router = APIRouter(tags=["journey"], route_class=DishkaRoute)


@router.get("/journey", response_model=JourneyOut)
async def get_journey(user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]):
    """Everything the journey map renders: chapters, lesson states, XP, tour stage."""
    return await service.journey(user)


@router.get("/journey/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(lesson_id: str, user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]):
    return await service.lesson(user, lesson_id)


@router.post("/journey/lessons/{lesson_id}/start", response_model=LessonOut)
async def start_lesson(
    lesson_id: str, user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]
):
    return await service.start_lesson(user, lesson_id)


@router.post("/journey/lessons/{lesson_id}/actions/{action_key}", response_model=ActionSubmitOut)
async def submit_action(
    lesson_id: str,
    action_key: str,
    body: ActionSubmitIn,
    user: FromDishka[CurrentUser],
    service: FromDishka[ProgressionService],
):
    # The document text is only ever produced by the upload endpoint below, never taken from the client.
    payload = {key: value for key, value in body.payload.items() if key != "document_text"}
    return await service.submit_action(user, lesson_id, action_key, payload)


@router.post("/journey/lessons/{lesson_id}/actions/{action_key}/document", response_model=ActionSubmitOut)
async def submit_document(
    lesson_id: str,
    action_key: str,
    file: UploadFile,
    user: FromDishka[CurrentUser],
    service: FromDishka[ProgressionService],
):
    """Upload a PDF for a document-review action. Only its text is read; the file is not kept."""
    data = await file.read(6 * 1024 * 1024)
    if await file.read(1):
        raise AppError("file_too_large", "The file is too large.", 413)
    return await service.submit_document(user, lesson_id, action_key, file.filename or "document.pdf", data)


@router.post("/journey/lessons/{lesson_id}/complete", response_model=CompleteOut)
async def complete_lesson(
    lesson_id: str, user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]
):
    """Idempotent. Pays the reward, or parks it until an avatar is chosen (first lesson only)."""
    return await service.complete_lesson(user, lesson_id)


@router.put("/me/avatar", response_model=AvatarOut)
async def select_avatar(
    body: AvatarIn, user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]
):
    """Save the avatar and pay any reward that was waiting for it, in one transaction."""
    return await service.select_avatar(user, body.avatar_key)


@router.post("/tour/events", response_model=TourOut)
async def tour_event(
    body: TourEventIn, user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]
):
    return await service.tour_event(user, body.event)
