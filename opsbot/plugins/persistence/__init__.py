from abc import abstractmethod
from typing import Dict

from .. import OpsbotPlugin


class PersistencePlugin(OpsbotPlugin):

    @abstractmethod
    def read_state(self) -> Dict:
        pass

    @abstractmethod
    def persist_state(self, state):
        pass

    @classmethod
    def _config_key(cls, key):
        return f"{cls.type()}.{key}"
