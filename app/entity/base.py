"""Small helpers shared by all entity classes."""
from datetime import datetime, date

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"


def now_str():
    """Current date-time as stored in the database."""
    return datetime.now().strftime(DATETIME_FMT)


def today_str():
    return date.today().strftime(DATE_FMT)
