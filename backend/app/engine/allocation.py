"""Resource allocation maths (pure Python, no database code).

A staff member's load on a given day is the sum of allocation_percent for every
allocation that covers that day. Nobody may be booked above 100% on any day.
Utilisation is the load on the reference day (normally today).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

MAX_LOAD = 100


@dataclass(frozen=True)
class Booking:
    percent: int
    start: date
    end: date
    allocation_id: int | None = None


def overlaps(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end


def load_on(bookings: Iterable[Booking], day: date) -> int:
    """Total percent booked on one day."""
    return sum(b.percent for b in bookings if b.start <= day <= b.end)


def peak_load(bookings: Iterable[Booking], start: date, end: date) -> tuple[int, date | None]:
    """Highest total load on any day in [start, end], and the first day it happens.

    Load only changes on a booking's start day or the day after its end, so it
    is enough to check those days (a sweep), not every day in the range.
    """
    inside = [b for b in bookings if overlaps(b.start, b.end, start, end)]
    if not inside:
        return 0, None
    days = {start}
    for b in inside:
        if start <= b.start <= end:
            days.add(b.start)
        after = b.end + timedelta(days=1)
        if start <= after <= end:
            days.add(after)
    best, best_day = 0, None
    for d in sorted(days):
        load = load_on(inside, d)
        if load > best:
            best, best_day = load, d
    return best, best_day


def check_new_booking(existing: Iterable[Booking], new: Booking, ignore_id: int | None = None) -> None:
    """Raise ValueError if adding `new` would put anyone above 100% on any day."""
    if new.end < new.start:
        raise ValueError("End date cannot be before the start date")
    if not 1 <= new.percent <= MAX_LOAD:
        raise ValueError("Allocation must be between 1% and 100%")
    others = [b for b in existing if ignore_id is None or b.allocation_id != ignore_id]
    combined = [*others, new]
    peak, day = peak_load(combined, new.start, new.end)
    if peak > MAX_LOAD:
        already = peak - new.percent
        raise ValueError(
            f"This would book the person at {peak}% on {day:%d %b %Y} "
            f"(already {already}% allocated). The most you can add for these dates is {MAX_LOAD - already}%."
        )


def utilisation_band(percent: int) -> str:
    """Label used on screen and in the dashboard chart."""
    if percent <= 0:
        return "bench"
    if percent < 50:
        return "light"
    if percent < 90:
        return "healthy"
    return "full"
