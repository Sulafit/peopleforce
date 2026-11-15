from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response

from peopleforce.core.config import Settings
from peopleforce.modules.auth.schemas import (
    CurrentUser,
    MagicLinkInspectOut,
    MagicLinkRequestIn,
    MagicLinkRequestOut,
    MeOut,
    TokenIn,
    VerifyOut,
)
from peopleforce.modules.auth.service import JOURNEY_PATH, AuthService
from peopleforce.modules.freelancer.schemas import profile_out
from peopleforce.modules.freelancer.service import FreelancerService
from peopleforce.modules.onboarding.api import clear_onboarding_cookie

router = APIRouter(tags=["auth"], route_class=DishkaRoute)


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


@router.post("/auth/magic-link", response_model=MagicLinkRequestOut, status_code=202)
async def request_magic_link(
    body: MagicLinkRequestIn,
    request: Request,
    settings: FromDishka[Settings],
    service: FromDishka[AuthService],
):
    """Email a single-use sign-in link. The finished quiz in this browser is bound to it server-side.

    The response is the same whether or not an account exists for the address.
    """
    return await service.request_magic_link(
        body.email, request.cookies.get(settings.onboarding_cookie_name), client_ip(request)
    )


@router.post("/auth/magic-link/inspect", response_model=MagicLinkInspectOut)
async def inspect_magic_link(body: TokenIn, service: FromDishka[AuthService]):
    """Report whether a link can still be used. Never consumes it (safe for prefetching scanners)."""
    return await service.inspect(body.token)


@router.post("/auth/magic-link/verify", response_model=VerifyOut)
async def verify_magic_link(
    body: TokenIn,
    request: Request,
    response: Response,
    settings: FromDishka[Settings],
    service: FromDishka[AuthService],
):
    """Consume the link (once), create the session cookie and attach the quiz to the account."""
    session_token, is_new = await service.verify(body.token, request.headers.get("user-agent"))
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    clear_onboarding_cookie(response, settings)
    # The destination is fixed server-side: no caller-supplied redirect, so no open redirect.
    return VerifyOut(redirect=JOURNEY_PATH, is_new_user=is_new)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request, response: Response, settings: FromDishka[Settings], service: FromDishka[AuthService]
):
    await service.logout(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = 204


@router.get("/me", response_model=MeOut)
async def me(user: FromDishka[CurrentUser], freelancer: FromDishka[FreelancerService]):
    profile = await freelancer.get_profile(user.id)
    return MeOut(
        id=user.id,
        email=user.email,
        profile=profile_out(profile) if profile else None,
        onboarding_required=profile is None,
    )
