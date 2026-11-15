from datetime import date

from pydantic import BaseModel

from peopleforce.modules.gamification.ranks import RANKS, Streak, next_rank, rank_for


class RankOut(BaseModel):
    number: int
    title: str
    min_xp: int
    next_title: str | None
    next_min_xp: int | None
    # XP earned inside the current rank and the size of that rank; 0..1 progress for the bar.
    xp_into: int
    xp_span: int | None
    progress: float


class RankStepOut(BaseModel):
    number: int
    title: str
    min_xp: int
    reached: bool
    current: bool


class StreakDayOut(BaseModel):
    day: date
    active: bool


class StreakOut(BaseModel):
    current: int
    longest: int
    active_today: bool
    week: list[StreakDayOut]


def rank_out(xp: int) -> RankOut:
    rank = rank_for(xp)
    upcoming = next_rank(rank)
    span = upcoming.min_xp - rank.min_xp if upcoming else None
    into = xp - rank.min_xp
    return RankOut(
        number=rank.number,
        title=rank.title,
        min_xp=rank.min_xp,
        next_title=upcoming.title if upcoming else None,
        next_min_xp=upcoming.min_xp if upcoming else None,
        xp_into=into,
        xp_span=span,
        progress=round(min(into / span, 1.0), 4) if span else 1.0,
    )


def rank_ladder(xp: int) -> list[RankStepOut]:
    current = rank_for(xp)
    return [
        RankStepOut(
            number=rank.number,
            title=rank.title,
            min_xp=rank.min_xp,
            reached=xp >= rank.min_xp,
            current=rank.number == current.number,
        )
        for rank in RANKS
    ]


def streak_out(streak: Streak, week: list[tuple[date, bool]]) -> StreakOut:
    return StreakOut(
        current=streak.current,
        longest=streak.longest,
        active_today=streak.active_today,
        week=[StreakDayOut(day=day, active=active) for day, active in week],
    )
