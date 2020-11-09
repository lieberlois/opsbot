from typing import List

from . import ActionPlugin, Command
from ...utils.cyclic_list import CyclicList


class SayingsActionPlugin(ActionPlugin):

    def get_commands(self) -> List[Command]:
        return [Command(None, self._unknown, None)]

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self._sayings_unknown_command = CyclicList(self.read_config_value('insults'))
        self._sayings_unknown_command.load_state(self.read_variable("sayings_state"))

    @staticmethod
    def required_configs() -> List[str]:
        return ['insults']

    def _unknown(self, activity, mentions):
        self.logger.info(f"Unknown command: '{activity.text}', mentions: {mentions}")
        insult = self._sayings_unknown_command.next()
        self.save_variable("sayings_state", self._sayings_unknown_command.get_state())
        self.send_reply(insult, activity)
