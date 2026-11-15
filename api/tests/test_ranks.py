from datetime import UTC, date, datetime, timedelta

from peopleforce.modules.gamification.ranks import compute_streak, local_day, rank_for
from peopleforce.modules.gamification.schemas import rank_out

TODAY = date(2026, 11, 15)


def days(*offsets: int) -> set[date]:
    return {TODAY - timedelta(days=offset) for offset in offsets}


def test_streak_counts_consecutive_days_and_survives_until_end_of_today():
    assert compute_streak(set(), TODAY).current == 0
    assert compute_streak(days(0), TODAY).current == 1
    assert compute_streak(days(0, 1, 2), TODAY).current == 3
    # Not active yet today: yesterday's streak is still alive.
    alive = compute_streak(days(1, 2), TODAY)
    assert (alive.current, alive.active_today) == (2, False)
    # A missed day breaks it; the longest run is remembered.
    broken = compute_streak(days(2, 3, 4, 5), TODAY)
    assert (broken.current, broken.longest) == (0, 4)
    assert compute_streak(days(0, 2, 3, 4), TODAY).current == 1


def test_day_boundary_follows_the_learners_time_zone():
    late_evening_utc = datetime(2026, 11, 16, 3, 30, tzinfo=UTC)
    assert local_day(late_evening_utc, "America/Los_Angeles") == date(2026, 11, 15)
    assert local_day(late_evening_utc, "UTC") == date(2026, 11, 16)
    assert local_day(late_evening_utc, "Not/AZone") == date(2026, 11, 16)


def test_ranks():
    assert rank_for(0).title == "Newcomer"
    assert rank_for(39).number == 1 and rank_for(40).number == 2
    halfway = rank_out(80)
    assert (halfway.title, halfway.next_title, halfway.xp_into, halfway.xp_span) == (
        "Explorer",
        "Builder",
        40,
        80,
    )
    assert halfway.progress == 0.5
    top = rank_out(5000)
    assert top.next_title is None and top.progress == 1.0
