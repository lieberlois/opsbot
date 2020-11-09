import re
import traceback
from dataclasses import dataclass, field
from typing import List, Dict

import requests

from . import ActionPlugin, Command
from ...utils.time_utils import now, is_today_a_workday

COMMENTS_IN_BRACES = re.compile(r"\(.*\)")
COLOR_MARKER = re.compile(r"\{color[^}]*\}")

DEFECTS_CHANNEL_TYPE = "defects"


class JiraActionPlugin(ActionPlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self.add_scheduled_job(self.check_jira, 'cron', id='regular_check', day_of_week='mon-fri', hour="9-17", minute="*/10")
        self.add_scheduled_job(self.daily_next, 'cron', id='daily_next', day_of_week='mon-fri', hour=8, minute=0)
        self._jira_base_url = self.read_config_value('base_url')
        self._jira_auth = (self.read_config_value('username'), self.read_config_value('password'))
        self._jira_filter_id = self.read_config_value('defects.filter_id')
        self._link_defects = self.read_config_value('defects.link_defects')
        self._subtask_project_id = self.read_config_value('subtasks.project_id')
        self._subtask_issue_type = self.read_config_value('subtasks.issue_type')

    @staticmethod
    def required_configs() -> List[str]:
        return ['base_url', 'username', 'password']

    def get_commands(self) -> List[Command]:
        return [
            Command(r".*gen\s+subtasks.*", self.generate_subtasks, "gen subtasks XXX-XXXX: Liest Tasks aus dem JIRA-Ticket aus und erzeugt Subtasks"),
            Command(r".*show\s+tasks.*", self.collect_subtasks, "show tasks XXX-XXXX: Listet die im Jira-Ticket erkannten Tasks auf"),
            Command(r".*fix.*", self.fix_ticket, "fix XXX-XXXX: Behebe das Problem"),
            Command(r"defects", self.show_defects, "defects: Gibt aktuelle Defects aus"),
        ]

    def daily_next(self):
        """Called each morning by scheduler to announce for the day"""
        if not is_today_a_workday():
            return
        self.check_jira(daily=True)

    def generate_subtasks(self, activity, mentions):
        pattern = re.compile(r".*subtasks\s+(\S+).*")
        text = activity.text.lower().strip()
        if pattern.match(text):
            ticket_name = pattern.match(text).groups()[0]
        else:
            self.logger.info(f"Could not match: {text}")
            self.send_reply("%s ist keine gültige Ticket-Nummer." % text, activity)
            return
        if "-" not in ticket_name:
            self.send_reply("%s ist keine gültige Ticket-Nummer." % ticket_name, activity)
            return
        try:
            self.send_reply("Einen Moment...", activity)
            self.create_subtasks(ticket_name)
            self.send_reply("Subtasks sind angelegt. Viel Spaß beim Implementieren. Möge die Macht mit dir sein.", activity)
        except Exception as ex:
            traceback.print_exc()
            self.send_reply("Ein Problem ist aufgetreten: %s." % str(ex), activity)

    def collect_subtasks(self, activity, mentions):
        pattern = re.compile(r".*tasks\s+(\S+).*")
        if pattern.match(activity.text.lower()):
            ticket_name = pattern.match(activity.text.lower()).groups()[0]
        else:
            self.logger.info(f"Could not match: {activity.text.lower()}")
            self.send_reply(f"Could not match: {activity.text.lower()}", activity)
            return
        if "-" not in ticket_name:
            self.send_reply("%s ist keine gültige Ticket-Nummer." % ticket_name, activity)
            return
        try:
            ticket = self.retrieve_tasks_from_ticket(ticket_name)
            self.send_reply("Folgende Tasks kann ich im Ticket-Text finden: %s" % '  |  '.join(ticket.subtasks), activity)
        except Exception as ex:
            traceback.print_exc()
            self.send_reply("Ein Problem ist aufgetreten: %s." % str(ex), activity)

    def fix_ticket(self, activity, mentions):
        self.send_reply("Damn it, Jim. I'm a bot, not an engineer!", activity)

    def show_defects(self, activity, mentions):
        if not self.check_jira(True):
            self.send_reply("Derzeit keine Defects. Viel Spaß beim Arbeiten.", activity)

    def check_jira(self, daily=False):
        if not is_today_a_workday():
            return
        try:
            issues = self.check_filter()
            self.save_variable("last_check", now().timestamp())
            if not issues:
                self.save_variable("issues", issues)
                return False
            known_issues = self.read_variable("issues", [])
            inform_about = list()
            for issue in issues:
                known = issue["key"] in known_issues
                if not known:
                    inform_about.append(issue)
            if inform_about:
                self.inform_about_defects(inform_about)
            issue_list = [i["key"] for i in issues]
            self.save_variable("issues", issue_list)
            return True
        except Exception as ex:
            self.logger.exception("Error while checking JIRA")
            last_check = self.read_variable("last_check", 0)
            if now().timestamp() - last_check >= 60 * 60:
                self.report_error(str(ex))
                self.save_variable("last_check", now().timestamp())
        return True

    def check_filter(self):
        response = requests.get(f"{self._jira_base_url}/rest/api/2/filter/%s" % self._jira_filter_id, auth=self._jira_auth)
        response.raise_for_status()

        url = response.json()["searchUrl"]
        response = requests.get(url, auth=self._jira_auth)
        if response.ok:
            issues = response.json()["issues"]
            return [dict(key=i["key"], status=i.get("fields", dict()).get("status", dict()).get("name", "UNKNOWN"),
                         priority=i.get("fields", dict()).get("priority", dict()).get("name", "UNKNOWN")) for i in issues]

    def inform_about_defects(self, issues):
        for issue in issues:
            self.send_message(
                f'Neuer Defect {issue["key"]} <a href="{self._jira_base_url}/browse/{issue["key"]}">{self._jira_base_url}/browse/{issue["key"]}</a> mit Priority "{issue["priority"]}" im Status "{issue["status"]}".\r\n',
                channel_type=DEFECTS_CHANNEL_TYPE)

    def report_error(self, reason):
        person_today = self.call_plugin_method("operations", "current", default='general')
        self.send_message(
            f'<at>{person_today}</at> Ich konnte JIRA nicht prüfen. ({reason}). Bitte prüfe selbst ob es neue Defects gibt: <a href="{self._link_defects}">{self._link_defects}</a>',
            channel_type=DEFECTS_CHANNEL_TYPE, mentions=[person_today])

    def create_subtasks(self, ticket):
        ticket = self.retrieve_tasks_from_ticket(ticket)
        for task in ticket.subtasks:
            self.create_subtask(ticket, task)

    def create_subtask(self, ticket, text):
        data = dict(
            fields=dict(
                project=dict(id=self._subtask_project_id),
                summary=text,
                issuetype=dict(id=self._subtask_issue_type),
                parent=dict(key=ticket.key.upper()),
                components=ticket.components,
            )
        )
        print("Creating ticket for {} with summary '{}'".format(ticket.key, text))
        response = requests.post(f"{self._jira_base_url}/rest/api/2/issue/", json=data, auth=self._jira_auth)
        print(response.text, flush=True)
        if not response.ok:
            raise Exception("Failed to create subtask: {} {}".format(response.status_code, response.text))

    def retrieve_tasks_from_ticket(self, ticket):
        ticket = self.retrieve_ticket(ticket)
        tasks = list(extract_subtasks(ticket.text))
        ticket.subtasks = tasks
        return ticket

    def retrieve_ticket(self, ticket):
        response = requests.get(f"{self._jira_base_url}/rest/api/2/issue/" + ticket, auth=self._jira_auth)
        if not response.ok:
            print(response.text, flush=True)
            raise Exception("Failed to get ticket")
        data = response.json()
        if not "fields" in data:
            raise Exception("JIRA API response does not contain fields.")
        if not "description" in data["fields"]:
            raise Exception("JIRA API response does not contain ticket description field.")
        text = data["fields"]["description"]
        # assignee = data["fields"].get("assignee", dict()).get("key")
        jira_components = data["fields"].get("components", list())
        components = [dict(id=c["id"], name=c["name"]) for c in jira_components]
        return JiraTicket(ticket, text, "", components)


def extract_subtasks(text):
    if "h4. Tasks" not in text and "h1. Tasks" not in text:
        raise Exception("No tasks in ticket text found")
    text = text.replace("\r\n", "\n")
    if "h4. Tasks" in text:
        tasks_text = text.split("h4. Tasks")[1]
    else:
        tasks_text = text.split("h1. Tasks")[1]
    if "**" in tasks_text:
        current_main_task = ""
        found_subtask = True
        for line in tasks_text.split("\n"):
            line = line.strip()
            if line == "" or line[0] != "*":
                continue
            if line.startswith("h4.") or line.startswith("h1."):
                break
            list_prefix, task = line.split(" ", 1)
            task = task.strip()
            task = task.replace("*", "")
            if list_prefix == "*":
                if not found_subtask:
                    yield current_main_task
                current_main_task = task
                found_subtask = False
            elif list_prefix == "**":
                if current_main_task == "":
                    raise Exception("Task list did not start with first-level list item")
                found_subtask = True
                task = _clean_task(task)
                yield current_main_task + ": " + task
            elif list_prefix[0] == "*" and not found_subtask:
                raise Exception("No second-level list item after first-level list item")
        if current_main_task != "" and not found_subtask:
            yield current_main_task
    else:
        for line in tasks_text.split("\n"):
            line = line.strip()
            if line == "" or line[0] != "*":
                continue
            if line.startswith("h4.") or line.startswith("h1."):
                break
            line = line[1:].strip()
            line = _clean_task(line)
            yield line


def _clean_task(task):
    task = COMMENTS_IN_BRACES.sub("", task)
    task = COLOR_MARKER.sub("", task)
    task = task.replace("*", "")
    return task.strip()


@dataclass
class JiraTicket:
    key: str
    text: str
    assignee: str
    components: List[Dict]
    subtasks: List[str] = field(default_factory=list)
