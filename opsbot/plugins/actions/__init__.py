from abc import abstractmethod
from collections import Callable
from dataclasses import dataclass
from typing import Optional, List

from .. import OpsbotPlugin
from ...utils.time_utils import TIMEZONE


@dataclass
class Command:
    command_regexp: Optional[str]  # If None the hook is used for unknown commands. Used in sayings plugin.
    function: Callable
    help_text: Optional[str]


class ActionPlugin(OpsbotPlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        for hook in self.get_commands():
            if hook.command_regexp:
                opsbot.register_messagehook_regex(hook.command_regexp, hook.function)
            else:
                opsbot.register_messagehook_unknown(hook.function)

    @abstractmethod
    def get_commands(self) -> List[Command]:
        pass

    @classmethod
    def _config_key(cls, key):
        return f"{cls.type()}.{cls.plugin_name()}.{key}"

    def call_plugin_method(self, plugin_name, method_name, default=None):
        try:
            return getattr(self._opsbot.plugins.actions()[plugin_name], method_name)()
        except:
            return default

    def send_error_response(self, msg, ex=None, reply_to=None):
        if ex:
            msg = f"{msg}: {str(ex)}"
            self.logger.exception(msg)
        else:
            self.logger.error(msg)
        if reply_to:
            self.send_reply(msg, reply_to=reply_to)
        else:
            self.send_message(msg)

    def add_scheduled_job(self, func, trigger, id, **trigger_args):
        self._opsbot._scheduler.add_job(func, trigger, timezone=TIMEZONE, id=f"{self.plugin_name()}_{id}", **trigger_args)

    def send_reply(self, reply, reply_to, mentions=None):
        self._opsbot.send_reply(reply, reply_to, mentions)

    def send_message(self, msg, channel_type=None, mentions=None):
        self._opsbot.send_message(msg, mentions=mentions, channel_type=channel_type)

    def register_messagehook_regex(self, regex, message_func):
        self._opsbot.register_messagehook_regex(regex, message_func)

    def register_messagehook_unknown(self, message_func):
        self._opsbot.register_messagehook_unknown(message_func)

    def register_messagehook_func(self, matcher_func, message_func):
        self._opsbot.register_messagehook_func(matcher_func, message_func)

    def save_variable(self, key, value):
        self._opsbot.save_plugin_variable(self.type(), self.plugin_name(), key, value)

    def read_variable(self, key, default=None):
        val = self._opsbot.read_plugin_variable(self.type(), self.plugin_name(), key)
        if val:
            return val
        else:
            return default
