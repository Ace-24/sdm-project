"""Shared date-period rules for the daily / weekly / monthly reports (#50 and Platform Reports)."""
import calendar
from datetime import date, datetime, timedelta
from app.constants import PERIOD_TYPES


def validatePeriod(periodType, refDate):
    """Returns the date if the period type is valid and the date is not in the future, otherwise None."""
    if periodType not in PERIOD_TYPES or not refDate:
        return None
    try:
        day = datetime.strptime(refDate, "%Y-%m-%d").date() if isinstance(refDate, str) else refDate
    except ValueError:
        return None
    return day if day <= date.today() else None


def calculateDateRange(periodType, day):
    """Daily = that day, Weekly = Monday to Sunday, Monthly = the whole month."""
    if periodType == "Daily":
        return day, day
    if periodType == "Weekly":
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6)
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)
