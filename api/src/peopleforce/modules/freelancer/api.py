import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from peopleforce.modules.auth.schemas import CurrentUser
from peopleforce.modules.freelancer.drafts import AssetDraftService
from peopleforce.modules.freelancer.schemas import AssetOut, AssetUpdateIn, GenerateDraftOut

router = APIRouter(prefix="/assets", tags=["assets"], route_class=DishkaRoute)


@router.get("", response_model=list[AssetOut])
async def list_assets(user: FromDishka[CurrentUser], service: FromDishka[AssetDraftService]):
    return await service.list_assets(user)


@router.post("/platform-draft", response_model=GenerateDraftOut)
async def generate_platform_draft(user: FromDishka[CurrentUser], service: FromDishka[AssetDraftService]):
    """Generate (or regenerate) a draft for the learner's preferred platform from their saved assets."""
    return await service.generate_platform_draft(user)


@router.patch("/{asset_id}", response_model=AssetOut)
async def update_draft(
    asset_id: uuid.UUID,
    body: AssetUpdateIn,
    user: FromDishka[CurrentUser],
    service: FromDishka[AssetDraftService],
):
    return await service.update_draft(user, asset_id, body.title, body.body)


@router.post("/{asset_id}/approve", response_model=AssetOut)
async def approve_draft(
    asset_id: uuid.UUID, user: FromDishka[CurrentUser], service: FromDishka[AssetDraftService]
):
    return await service.approve(user, asset_id)
