"""Calendar logic — Mon/Thu shift with NSE holiday awareness."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path


def load_holidays(holidays_path: Path) -> set:
    with open(holidays_path) as f:
        data = json.load(f)
    return {date.fromisoformat(d) for d in data["holidays"]}


def is_trading_day(d: date, holidays: set) -> bool:
    return d.weekday() < 5 and d not in holidays


def shift_to_trading_day(d: date, holidays: set, direction: str = "forward") -> date:
    """Walk forward (or backward) until d is a weekday and not a holiday."""
    step = timedelta(days=1 if direction == "forward" else -1)
    while not is_trading_day(d, holidays):
        d += step
    return d


def monday_of_week(d: date, holidays: set) -> date:
    """Monday of the week containing d, holiday-shifted forward within the week."""
    monday = d - timedelta(days=d.weekday())
    return shift_to_trading_day(monday, holidays, "forward")


def thursday_of_week(d: date, holidays: set) -> date:
    """Thursday of the week containing d, holiday-shifted backward within the week."""
    thursday = d - timedelta(days=d.weekday()) + timedelta(days=3)
    return shift_to_trading_day(thursday, holidays, "backward")


def compute_tranche_dates(day0: date, day_offset: int, holidays: set):
    """Return (redemption_date, deployment_date) for a tranche.
    Day 0 has no redemption (funds enter the account); deployment lands on day0 itself.
    """
    if day_offset == 0:
        return None, day0
    target = day0 + timedelta(days=day_offset)
    return monday_of_week(target, holidays), thursday_of_week(target, holidays)


def to_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    return d
