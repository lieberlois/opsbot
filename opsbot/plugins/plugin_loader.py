import importlib
import logging
import pkgutil
import sys
from inspect import isclass, isabstract
from typing import Dict, Type

from . import OpsbotPlugin
from .actions import ActionPlugin
from .persistence import PersistencePlugin
from ..config import get_config_value
from ..config.constants import APP_DIR

logger = logging.getLogger()


def _find_plugin_class_in_module(module, base_class):
    for i in dir(module):
        attribute = getattr(module, i)
        if isclass(attribute) and issubclass(attribute, base_class) and attribute != base_class:
            if not isabstract(attribute):
                return attribute
            else:
                raise PluginAbstractException(f"{attribute} does not implement all abstract methods.")
    raise PluginNotFoundException(f"No class extending '{base_class.__name__}' found in module '{module}'")


def _find_plugin_classes(plugin_type, base_class):
    path = f"{APP_DIR}/plugins/{plugin_type}"
    packages = pkgutil.iter_modules(path=[path])
    modules = [importlib.import_module(f"opsbot.plugins.{plugin_type}.{name}") for (_, name, _) in packages]
    types = []
    for module in modules:
        try:
            types.append(_find_plugin_class_in_module(module, base_class))
        except Exception as e:
            logger.warning(f"Plugin could not be loaded: {str(e)}")
    return types


def _find_external_plugin_modules(path):
    sys.path.append(path)
    packages = pkgutil.iter_modules(path=[path])
    return [importlib.import_module(name) for (_, name, _) in packages]


def _are_required_configs_set(cls: Type[OpsbotPlugin], level):
    required_vars = [cls._config_key(c) for c in cls.required_configs()]
    for required in required_vars:
        if not get_config_value(required):
            logger.log(level, f"{cls.__base__.__name__} '{cls.plugin_name()}' requires configurations: {required_vars}")
            return False
    return True


class PluginLoader(object):

    def __init__(self, opsbot):
        self._opsbot = opsbot
        self._action_classes = _find_plugin_classes('actions', ActionPlugin)
        persistence_classes = _find_plugin_classes('persistence', PersistencePlugin)

        external_plugin_path = get_config_value('additional_plugin_dir')
        if external_plugin_path:
            external_modules = _find_external_plugin_modules(external_plugin_path)
            for external_module in external_modules:
                try:
                    try:
                        self._action_classes.append(_find_plugin_class_in_module(external_module, ActionPlugin))
                        continue
                    except PluginNotFoundException:
                        pass
                    try:
                        persistence_classes.append(_find_plugin_class_in_module(external_module, PersistencePlugin))
                        continue
                    except PluginNotFoundException:
                        pass
                    logger.warning(f"Plugin could not be loaded. Has unknown type")
                except Exception as e:
                    logger.warning(f"Plugin could not be loaded: {str(e)}")

        self._persistence = self._init_persistence_plugin(persistence_classes)
        self._action_plugins = dict()

    def _init_persistence_plugin(self, persistence_classes):
        persistence_plugin_name = get_config_value('persistence.plugin', fail_if_missing=True)
        for persistence_class in persistence_classes:
            if persistence_class.plugin_name() == persistence_plugin_name:
                if not _are_required_configs_set(persistence_class, logging.CRITICAL):
                    exit(-1)
                persistence_plugin = persistence_class(self._opsbot)
                logger.info(f"Initialized persistence plugin '{persistence_class.plugin_name()}'")
                return persistence_plugin
        logger.critical(f"Persistence plugin '{persistence_plugin_name}' not found.")
        exit(-1)

    def init_action_plugins(self):
        actions = dict()
        for action_class in self._action_classes:
            if action_class.plugin_name() not in get_config_value('deactivate_plugins', []):
                if _are_required_configs_set(action_class, logging.WARNING):
                    actions[action_class.plugin_name()] = action_class(self._opsbot)
                    logger.info(f"Initialized action plugin '{action_class.plugin_name()}'")
        self._action_plugins = actions

    def persistence(self) -> PersistencePlugin:
        return self._persistence

    def actions(self) -> Dict[str, ActionPlugin]:
        return self._action_plugins


class PluginNotFoundException(Exception):
    pass


class PluginAbstractException(Exception):
    pass
