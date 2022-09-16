from typing import List
import logging

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from ...utils.time_utils import DATE_FORMAT, now, today_date
from . import ActionPlugin, Command

logger = logging.getLogger()

REMINDERS_CHANNEL_TYPE = "reminders"

UNITS = {
    "d": "days",
    "w": "weeks",
    "m": "months",
    "y": "years"
}

def _build_mentions_message(mentions: List[str]) -> str:
    msg = ""
    for mention in mentions:
        msg += f"<at>{mention}</at> "

    return msg

def _parse_date(datestring: str, format: str = DATE_FORMAT) -> date:
    return datetime.strptime(datestring, format).date()


def _calculate_reminder_date(event_date: date, datestring: str) -> date:
    # Datestring has the format "<amount>[D|W|M|Y]"
    unit_str = datestring[-1]
    duration_str = datestring[:-1]

    return event_date - relativedelta(**{UNITS[unit_str.lower()]: int(duration_str)})
    

def _should_remind(check_date: date, notification_dates: List[date]) -> bool:
    return check_date in notification_dates


def _calculate_dates_to_check(latest_reminder_date: date) -> List[date]:
    today = today_date()

    # Always check for today
    if latest_reminder_date == today:
        return [today]

    # Check for each day between latest and today
    dates_to_check = []
    while latest_reminder_date < today:
        latest_reminder_date += timedelta(days=1)
        dates_to_check.append(latest_reminder_date)
    
    return dates_to_check


class RemindersActionPlugin(ActionPlugin):

    def get_commands(self) -> List[Command]:
        return []

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self._events = self.read_config_value("events")
        self.add_scheduled_job(self._remind_events, 'cron', id='remind_events', day_of_week='mon-fri', hour=8, minute=0)

        # For debugging:
        self.add_scheduled_job(self._remind_events, 'cron', id='debug', day_of_week='*', hour='*', minute='*')
        
        self._latest_reminder_run = _parse_date(
            self.read_variable("latest_reminder_run", default=str(today_date())),
            "%Y-%m-%d"
        )

    @staticmethod
    def required_configs() -> List[str]:
        return ['events']

    def _remind_events(self):
        dates_to_check = _calculate_dates_to_check(self._latest_reminder_run)
        logger.info(f"Checking {len(dates_to_check)} dates")
        
        for event in self._events:
            # Parse event data
            event_date: date = _parse_date(event.get("event_date"))
            title: str = event.get("title", "Kein Titel")
            description: str = event.get("description", "Keine Beschreibung")
            mentions: List[str] = event.get('mentions', [])
            notifications: List[str] = event.get("notifications", [])
            
            # Calculate possible notification dates
            notification_dates = [
                _calculate_reminder_date(event_date, datestring) for datestring in notifications
            ]
            
            # Always notify when the event is today
            notification_dates.append(event_date)

            # Check each event for necessary notifications
            for date in dates_to_check:
                if _should_remind(date, notification_dates):
                    message = _build_mentions_message(mentions) + f"Erinnerung: {title} - {description} ({event_date.strftime(DATE_FORMAT)})"

                    self.send_message(
                        message, 
                        mentions=mentions, 
                        channel_type=REMINDERS_CHANNEL_TYPE
                    )
                    break

        # Store the latest reminder run via the persistence plugin
        self._latest_reminder_run = now().date()
        self.save_variable("latest_reminder_run", str(self._latest_reminder_run))