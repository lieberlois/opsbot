import inspect
import logging
from abc import ABC, abstractmethod
from ntpath import basename, splitext
from typing import List

from ..config import get_config_value


class OpsbotPlugin(ABC):

    def __init__(self, opsbot):
        from ..opsbot import OpsBot
        self._opsbot: OpsBot = opsbot
        self.logger = logging.getLogger(self.plugin_name())

    @classmethod
    def type(cls):
        return inspect.getmodule(cls.__base__).__package__.split('.')[-1]

    @classmethod
    def plugin_name(cls):
        return splitext(basename(inspect.getfile(cls)))[0]

    @staticmethod
    def required_configs() -> List[str]:
        return []

    def read_config_value(self, key):
        return get_config_value(self._config_key(key))

    @classmethod
    @abstractmethod
    def _config_key(cls, key):
        pass
