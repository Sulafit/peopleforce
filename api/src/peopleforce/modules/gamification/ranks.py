"""XP ranks and streak arithmetic. Pure functions: no I/O, trivially testable.

Chapters on the map are called "levels", so the XP ladder is called "ranks" to keep the two apart.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Rank:
    number: int
    title: str
    min_xp: int


RANKS: tuple[Rank, ...] = (
    Rank(1, "Newcomer", 0),
    Rank(2, "Explorer", 40),
    Rank(3, "Builder", 120),
    Rank(4, "Specialist", 250),
    Rank(5, "Professional", 450),
    Rank(6, "Expert", 700),
    Rank(7, "Independent", 1000),
)


def rank_for(xp: int) -> Rank:
    return next(rank for rank in reversed(RANKS) if xp >= rank.min_xp)


def next_rank(rank: Rank) -> Rank | None:
    return RANKS[rank.number] if rank.number < len(RANKS) else None


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def local_day(now: datetime, timezone: str) -> date:
    """The learner's calendar day. An unknown zone falls back to UTC rather than failing."""
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    return now.astimezone(zone).date()


@dataclass(frozen=True)
class Streak:
    current: int
    longest: int
    active_today: bool


def compute_streak(days: set[date], today: date) -> Streak:
    """A streak is alive if the learner was active today or yesterday (today is still open)."""
    longest = 0
    for day in days:
        if day - timedelta(days=1) in days:
            continue  # not the start of a run
        length = 1
        while day + timedelta(days=length) in days:
            length += 1
        longest = max(longest, length)

    cursor = today if today in days else today - timedelta(days=1)
    current = 0
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    return Streak(current=current, longest=longest, active_today=today in days)
