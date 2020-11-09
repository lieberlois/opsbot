import re
from datetime import datetime
from typing import List

from . import Command
from ...config import get_config_value
from ...plugins.actions import ActionPlugin
from ...utils.cyclic_list import CyclicList
from ...utils.time_utils import is_it_late, is_today_a_workday, next_workday, now, next_workday_string, DATE_FORMAT

OPERATIONS_CHANNEL_TYPE = "operations"


def format_gender(name):
    return "die" if name in get_config_value('woman', []) else "der"


class OperationsActionPlugin(ActionPlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self._members = CyclicList([], dynamic=True)
        self._members.load_state(self.read_variable("members", dict()))
        self._vacations = self.read_variable("vacations", list())
        self._user_override = self.read_variable("override", None)
        self._sayings_responsible_today = CyclicList(self.read_config_value('quotes'))
        self._sayings_responsible_today.load_state(self.read_variable("sayings_responsible_today", dict()))
        self._override_user = self.read_config_value('override_user')
        self._how_to_link = self.read_config_value('how_to_link')
        self.add_scheduled_job(self.daily_next, 'cron', id='daily_next', day_of_week='mon-fri', hour=8, minute=0)
        self.add_scheduled_job(self.daily_preview, 'cron', id='daily_preview', day_of_week='mon-fri', hour=17, minute=0)

    def get_commands(self) -> List[Command]:
        return [
            Command(r"((register)|(add))", self.register, "register @user: Person in die Rotation mit aufnehmen"),
            Command(r"((unregister)|(remove))", self.unregister, "unregister @user: Person aus der Rotation entfernen"),
            Command(r"((next)|(weiter))", self.next, "next / weiter [@user]: Rotation weiterschalten, wenn Person angegeben auf diese Person"),
            Command(r"((heute)|(current)|(today)|(who)|(wer))", self.print_current, "heute / today / wer: Gibt aus wer heute Betriebsverantwortlicher ist"),
            Command(r"((morgen)|(tomorrow))", self.print_tomorrow, "morgen / tomorrow: Gibt aus wer am naechsten Werktag Betriebsverantwortlicher sein wird"),
            Command(r"(shibboleet)|(shiboleet)|(shibolet)", self.override, "shibboleet: Selbsterklärend ;-)"),
            Command(r".*[uU]rlaub.*", self.add_vacation,
                    "'Urlaub am dd.mm.yyyy', 'Urlaub von dd.mm.yyyy bis dd.mm.yyyy' oder 'Urlaub dd.mm.yyyy - dd.mm.yyyy' [@user]: Trägt Urlaub ein, optional für eine andere Person"),
        ]

    @staticmethod
    def required_configs():
        return ['quotes']

    def register(self, activity, mentions):
        if not mentions:
            mentions = [activity.from_property.name]
        for mention in mentions:
            if self._members.add_element(mention):
                self.send_reply("<at>%(name)s</at> Willkommen in der Rotation" % dict(name=mention), reply_to=activity, mentions=[mention])
            else:
                self.send_reply("<at>%(name)s</at> Dich kenne ich schon" % dict(name=mention), reply_to=activity, mentions=[mention])
        self.save_user_config()

    def unregister(self, activity, mentions):
        if not mentions:
            mention = activity.from_property.name
            self.send_reply("<at>%(name)s</at> Feigling. So einfach kommst du mir nicht aus" % dict(name=mention), reply_to=activity, mentions=[mention])
            return
        for mention in mentions:
            self._members.remove_element(mention)
            self.send_reply("<at>%(name)s</at> Du bist frei" % dict(name=mention), reply_to=activity, mentions=[mention])
        self.save_user_config()

    def override(self, activity, mentions):
        """Command @OpsBot shiboleet"""
        if not self._override_user or activity.from_property.name != self._override_user:
            self.send_reply("Du hast hier nichts zu sagen!", reply_to=activity)
            return
        if is_it_late():
            self._user_override = "tomorrow"
            self.send_reply("Aye, aye. <at>%s</at> Du bist vom Haken." % self._members.peek(), reply_to=activity, mentions=[self._members.peek()])
        else:
            self._user_override = "today"
            self.send_reply("Captain auf der Brücke! <at>%s</at> Du bist vom Haken." % self._members.get(), reply_to=activity, mentions=[self._members.get()])
        self.save_user_config()

    def next(self, activity, mentions):
        """Command @OpsBot weiter|next"""
        its_late = is_it_late()
        if mentions:
            member = self._members.goto(mentions[0])
            if not member:
                self.send_reply("Dieser User ist mir nicht bekannt", reply_to=activity)
                return
            if its_late:
                self._members.previous()
        else:
            if its_late:
                self._members.next()
                self.select_next_tomorrow()
            else:
                self.select_next_today()

        if its_late:
            self.inform_tomorrow(reply_to=activity)
        else:
            self.inform_today(reply_to=activity)
        self.save_user_config()

    def current(self):
        if self._user_override == "today" and self._override_user:
            return self._override_user
        return self._members.get()

    def _operator_text(self):
        if self._how_to_link:
            return f'<a href="{self._how_to_link}">Betriebsverantwortliche</a>'
        else:
            return "Betriebsverantwortliche"

    def print_current(self, activity, mentions):
        member = self.current()
        msg = f'Hey <at>{member}</at> Du bist heute {format_gender(member)} {self._operator_text()}.'

        self.send_reply(msg, reply_to=activity, mentions=[member])

    def daily_next(self):
        """Called each morning by scheduler to announce for the day"""
        if not is_today_a_workday():
            return
        if self._user_override == "tomorrow":
            self._user_override = "today"
        self.select_next_today()
        self.inform_today()
        self.save_user_config()

    def daily_preview(self):
        """Called each evening by scheduler to announce for the next day"""
        if not is_today_a_workday():
            return
        if self._user_override == "today":
            self._user_override = None
        self.select_next_tomorrow()
        self.inform_tomorrow()
        self.save_user_config()

    def print_tomorrow(self, activity, mention):
        self.inform_tomorrow(activity)

    def inform_today(self, reply_to=None):
        if self._user_override == "today" and self._override_user:
            member = self._override_user
        else:
            member = self._members.get()
        msg = f'Hey <at>{member}</at> Du bist heute {format_gender(member)} {self._operator_text()}. {self._sayings_responsible_today.next()}'
        if reply_to:
            self.send_reply(msg, mentions=[member], reply_to=reply_to)
        else:
            self.send_message(msg, mentions=[member], channel_type=OPERATIONS_CHANNEL_TYPE)

    def inform_tomorrow(self, reply_to=None):
        if self._user_override == "tomorrow" and self._override_user:
            member = self._override_user
        else:
            member = self._members.peek()
        tomorrow = next_workday_string()
        msg = f'Hey <at>{member}</at> Du wirst {tomorrow} {format_gender(member)} {self._operator_text()} sein.'
        if reply_to:
            self.send_reply(msg, mentions=[member], reply_to=reply_to)
        else:
            self.send_message(msg, mentions=[member], channel_type=OPERATIONS_CHANNEL_TYPE)

    def add_vacation(self, activity, mentions):
        if mentions:
            name = mentions[0]
        else:
            name = activity.from_property.name
        text = activity.text
        try:
            r_1 = re.compile(r".*[uU]rlaub am (\d{1,2}\.\d{1,2}\.\d{4}).*")
            r_2 = re.compile(r".*[uU]rlaub vo[nm] (\d{1,2}\.\d{1,2}\.\d{4}) bis (\d{1,2}\.\d{1,2}\.\d{4}).*")
            r_3 = re.compile(r".*[uU]rlaub (\d{1,2}\.\d{1,2}\.\d{4}) - (\d{1,2}\.\d{1,2}\.\d{4}).*")
            if r_1.match(text):
                from_string = r_1.match(text).groups()[0]
                to_string = from_string
            elif r_2.match(text):
                groups = r_2.match(text).groups()
                from_string = groups[0]
                to_string = groups[1]
            elif r_3.match(text):
                groups = r_3.match(text).groups()
                from_string = groups[0]
                to_string = groups[1]
            else:
                self.send_reply(
                    "Ich habe dich nicht verstanden. Ich verstehe die folgenden Formate: 'Urlaub am dd.mm.yyyy', 'Urlaub von dd.mm.yyyy bis dd.mm.yyyy' oder 'Urlaub dd.mm.yyyy - dd.mm.yyyy'",
                    reply_to=activity, mentions=[name])
                return
            self._vacations.append((name, from_string, to_string))
            self.send_reply("Alles klar.", reply_to=activity)
            self.save_user_config()
        except Exception as ex:
            self.logger.info(ex)
            self.send_reply(
                "Ich habe dich nicht verstanden. Ich verstehe die folgenden Formate: 'Urlaub am dd.mm.yyyy', 'Urlaub von dd.mm.yyyy bis dd.mm.yyyy' oder 'Urlaub dd.mm.yyyy - dd.mm.yyyy'",
                reply_to=activity, mentions=[])

    def select_next_today(self):
        date_obj = now().date()
        n = 0
        max_n = self._members.size()
        ok = False
        while not ok and n < max_n:
            ok = True
            member = self._members.next()
            for vacation in self._vacations:
                if vacation[0] != member:
                    continue
                date_from = datetime.strptime(vacation[1], DATE_FORMAT).date()
                date_to = datetime.strptime(vacation[2], DATE_FORMAT).date()
                if date_from <= date_obj <= date_to:
                    ok = False
            n += 1
        return member

    def select_next_tomorrow(self):
        date_obj = next_workday()
        n = 1
        max_n = self._members.size()
        ok = False
        member = self._members.peek()
        while not ok and n < max_n:
            ok = True
            member = self._members.peek()
            for vacation in self._vacations:
                if vacation[0] != member:
                    continue
                date_from = datetime.strptime(vacation[1], DATE_FORMAT).date()
                date_to = datetime.strptime(vacation[2], DATE_FORMAT).date()
                if date_from <= date_obj <= date_to:
                    ok = False
                    continue
            n += 1
            if not ok:
                member = self._members.next()
        return member

    def save_user_config(self):
        self.save_variable("sayings_responsible_today", self._sayings_responsible_today.get_state())
        self.save_variable("members", self._members.get_state())
        self.save_variable("vacations", self._vacations)
        self.save_variable("override", self._user_override)
