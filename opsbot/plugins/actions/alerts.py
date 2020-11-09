import json
from datetime import datetime, timedelta
from typing import List

import requests

from . import Command
from ...plugins.actions import ActionPlugin
from ...utils.time_utils import next_workday, is_today_a_workday, now


class AlertsActionPlugin(ActionPlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self.add_scheduled_job(self.daily_next, 'cron', id='daily_next', day_of_week='mon-fri', hour=8, minute=0)
        self.add_scheduled_job(self.daily_preview, 'cron', id='daily_preview', day_of_week='mon-fri', hour=17, minute=0)
        self._alertmanager_url = self.read_config_value('base_url')

    def get_commands(self) -> List[Command]:
        return [Command(r"alerts", self.reply_alerts, "alerts: Gib eine Liste der aktuellen Alerts aus")]

    @staticmethod
    def required_configs():
        return ['base_url']

    def reply_alerts(self, activity, mentions):
        self.inform_alerts(reply_to=activity)

    def daily_next(self):
        """Called each morning by scheduler to announce for the day"""
        if not is_today_a_workday():
            return
        self.inform_alerts()

    def daily_preview(self):
        """Called each evening by scheduler to announce for the next day"""
        if not is_today_a_workday():
            return
        next_day = next_workday()
        days = (next_day - now().date()).days - 1
        duration = 13 + days * 24
        try:
            self.silence_non_critical_alerts(duration=duration)
        except Exception as ex:
            self.logger.info(ex)

    def silence_non_critical_alerts(self, duration, start_offset=1):
        start = datetime.utcnow() + timedelta(hours=start_offset)
        end = start + timedelta(hours=duration)
        start_ts = start.isoformat() + "Z"
        end_ts = end.isoformat() + "Z"
        silence = {"id": "", "createdBy": "bot", "comment": "nightly silence", "startsAt": start_ts, "endsAt": end_ts,
                   "matchers": [{"name": "critical", "value": "no", "isRegex": False}]}
        response = requests.post(self._alertmanager_url + "silences", data=json.dumps(silence))
        if not response.ok:
            self.logger.info(response)
            self.logger.info(response.text)

    def inform_alerts(self, reply_to=None):
        self.logger.info("Inform alerts")
        try:
            alerts = self.get_list_of_alerts()
            unique_alerts = list(set(alerts))
            self.logger.info(alerts)
            if len(unique_alerts) > 3:
                text = "Es gibt jede Menge aktive Alerts in Prometheus (so viele, dass ich sie hier nicht aufzähle)."
            elif len(unique_alerts) > 0:
                text = "Es gibt aktive Alerts in Prometheus: %s " % ', '.join(unique_alerts)
            else:
                self.logger.info("No alerts. Not sending")
                return
            person_today = self.call_plugin_method('operations', 'current', default='general')
            text = f"<at>{person_today}</at> {text}."
            if reply_to:
                self.send_reply(text, mentions=[person_today], reply_to=reply_to)
            else:
                self.send_message(text, mentions=[person_today])
        except Exception as ex:
            self.send_error_response("Failed to retrieve alerts", ex, reply_to)

    def get_list_of_alerts(self):
        response = requests.get(self._alertmanager_url + "alerts?silenced=false&inhibited=false")
        if not response.ok:
            self.logger.info(response)
            self.logger.info(response.text)
            return []
        data = response.json()["data"]
        return [a["labels"]["alertname"] for a in data]
