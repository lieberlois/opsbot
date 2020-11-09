import atexit
import re

from apscheduler.schedulers.background import BackgroundScheduler

from .teams import TeamsBot


class OpsBot(TeamsBot):
    def __init__(self):
        super(OpsBot, self).__init__("opsbot")
        self._scheduler = self._init_scheduler()
        self._init_hooks()
        self.plugins.init_action_plugins()

    def _init_hooks(self):
        self.register_messagehook_regex(r".*help.*", self.help)
        self.register_messagehook_regex(r"init", self.init_message)
        self.register_messagehook_regex(r"channel register.*", self.register_channel)
        self.register_messagehook_regex(r"channel unregister.*", self.unregister_channel)

    def register_channel(self, activity, mentions):
        pattern = re.compile(r".*channel register\s+(\w+)\s*")
        try:
            channel_type = pattern.match(activity.text).groups()[0]
            self._conversation_channels[channel_type] = activity.conversation.id.split(";")[0]
            self.send_reply(f"Nachrichten vom Typ '{channel_type}' werden ab jetzt in diesen Channel gepostet.", activity)
            self._save_system_config()
        except:
            self.send_reply("Ich habe dich nicht verstanden", activity)

    def unregister_channel(self, activity, mentions):
        pattern = re.compile(r".*channel unregister\s+(\w+)\s*")
        try:
            channel_type = pattern.match(activity.text).groups()[0]
            if channel_type in self._conversation_channels:
                del self._conversation_channels[channel_type]
                self.send_reply(f"Nachrichten vom Typ '{channel_type}' werden ab jetzt in den Default Channel gepostet.", activity)
                self._save_system_config()
            else:
                self.send_reply(f"Für Nachrichten Typ '{channel_type}' ist kein Channel registriert.", activity)
        except:
            self.send_reply("Ich habe dich nicht verstanden", activity)

    def help(self, activity, mentions):
        help_text = """
Ich verstehe die folgenden Kommandos:
* register channel XX: Den aktuellen Kanal für Nachrichten vom Typ XX konfigurieren.
* unregister channel XX: Die Kanalzuordnung für Typ XX entfernen.
"""
        for _, plugin in self.plugins.actions().items():
            for command in plugin.get_commands():
                if command.help_text:
                    help_text += f"* {command.help_text}\n"
        help_text += f"* help: Gibt diese Hilfe aus"
        self.send_reply(help_text, activity)

    def _init_scheduler(self):
        scheduler = BackgroundScheduler()
        scheduler.start()
        atexit.register(scheduler.shutdown)
        return scheduler

    def init_message(self, activity, mentions):
        self._update_bot_infos(activity)
        self.send_reply("Hallo zusammen. Ich bin der OpsBot.", reply_to=activity)

    def save_plugin_variable(self, plugin_type, plugin_name, key, value):
        def init_key_if_missing(_dict, _key):
            if _key not in _dict:
                _dict[_key] = dict()

        if self.read_plugin_variable(plugin_type, plugin_name, key) != value:
            init_key_if_missing(self._config, 'plugins')
            init_key_if_missing(self._config['plugins'], plugin_type)
            init_key_if_missing(self._config['plugins'][plugin_type], plugin_name)
            self._config['plugins'][plugin_type][plugin_name][key] = value
            self._save_system_config()

    def read_plugin_variable(self, plugin_type, plugin_name, key):
        try:
            return self._config['plugins'][plugin_type][plugin_name][key]
        except KeyError:
            return None
