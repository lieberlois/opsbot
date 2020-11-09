from datetime import timedelta, datetime

import holidays
import pytz

from ..config import get_config_value

DATE_FORMAT = "%d.%m.%Y"

TIMEZONE = pytz.timezone(get_config_value('timezone', default="Europe/Berlin"))

WEEKDAYS = {
    1: "Montag",
    2: "Dienstag",
    3: "Mittwoch",
    4: "Donnerstag",
    5: "Freitag",
    6: "Samstag",
    7: "Sonntag",
}
HOLIDAYS = holidays.CountryHoliday('DE', prov="BY", state=None)


def now():
    return datetime.now(tz=TIMEZONE)


def is_day_a_workday(date_obj):
    return date_obj.isoweekday() < 6 and date_obj.date() not in HOLIDAYS


def is_today_a_workday():
    return is_day_a_workday(now())


def next_workday():
    next_day = now() + timedelta(days=1)
    while not is_day_a_workday(next_day):
        next_day = next_day + timedelta(days=1)
    return next_day.date()


def next_workday_string():
    tomorrow = now() + timedelta(days=1)
    if is_day_a_workday(tomorrow):
        return "morgen"
    next_day = tomorrow
    while not is_day_a_workday(next_day):
        next_day = next_day + timedelta(days=1)
    return "am " + WEEKDAYS[next_day.isoweekday()]


def is_it_late():
    return now().hour >= 17 or now().isoweekday() >= 6

