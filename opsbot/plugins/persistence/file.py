import os
from typing import Dict

import oyaml

from . import PersistencePlugin


class FilePersistencePlugin(PersistencePlugin):

    def __init__(self, opsbot):
        super().__init__(opsbot)
        self._path = self.read_config_value('path')

    @staticmethod
    def required_configs():
        return ['path']

    def read_state(self) -> Dict:
        if os.path.exists(self._path):
            self.logger.info(f"Load state from file '{self._path}'")
            with open(self._path, 'r') as f:
                return oyaml.load(f, Loader=oyaml.Loader)
        else:
            self.logger.warning(f"State file '{self._path}' not found")
            return dict()

    def persist_state(self, state):
        self.logger.info(f"Write state to file '{self._path}'")
        with open(self._path, 'w') as f:
            oyaml.dump(state, f, indent=4)
