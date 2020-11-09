from typing import List

from opsbot.plugins.actions import ActionPlugin, Command


class MyCustomActionPlugin(ActionPlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self.add_scheduled_job(self._scheduled, 'cron', id='some_id', day_of_week='mon-fri', hour=8, minute=0)

    def get_commands(self) -> List[Command]:
        return [
            Command(r"((MyCommand)|(mycommand))", self._response, "mycommand: My custom command")
        ]

    def _response(self, activity, mentions):
        self.send_reply(f"Send response to the thread the command was issued.", activity)

    def _scheduled(self, activity, mentions):
        self.send_message(f"Send message to a channel. Either a named channel or the default one", channel_type='myChannelType')
