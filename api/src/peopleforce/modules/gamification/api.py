from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.gamification.daily import DailyService
from peopleforce.modules.progression.schemas import (
    DailyOut,
    DailySubmitIn,
    DailySubmitOut,
    ProfilePageOut,
    TimezoneIn,
)
from peopleforce.modules.progression.service import ProgressionService

router = APIRouter(tags=["gamification"], route_class=DishkaRoute)


@router.get("/daily", response_model=DailyOut)
async def get_daily(user: FromDishka[CurrentUser], service: FromDishka[DailyService]):
    """Today's challenge (by the learner's local day) and the current streak."""
    return await service.today(user)


@router.post("/daily/submit", response_model=DailySubmitOut)
async def submit_daily(body: DailySubmitIn, user: FromDishka[CurrentUser], service: FromDishka[DailyService]):
    """Answer today's challenge. XP is paid once per day; repeating the call pays nothing more."""
    return await service.submit(user, body.payload)


@router.get("/profile", response_model=ProfilePageOut)
async def get_profile_page(user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]):
    """Everything the profile page shows: rank ladder, streak, achievements, saved assets."""
    return await service.profile_page(user)


@router.put("/me/timezone", status_code=204)
async def set_timezone(
    body: TimezoneIn, user: FromDishka[CurrentUser], service: FromDishka[ProgressionService]
):
    """Store the browser's IANA time zone; it decides when the learner's day starts."""
    await service.set_timezone(user, body.timezone)
