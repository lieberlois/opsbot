import logging
import os
import sys

import oyaml

from .constants import OPSBOT_CONFIG_FILE_ENV, OPSBOT_CONFIG_FILE_DEFAULT

logger = logging.getLogger()

_config = None


def _load_config():
    path = os.environ.get(OPSBOT_CONFIG_FILE_ENV, OPSBOT_CONFIG_FILE_DEFAULT)
    if not os.path.exists(path):
        logger.critical(f"Opsbot config file not found at path: '{path}'")
        sys.exit(-1)

    with open(path) as f:
        return oyaml.safe_load(f.read())


def _get_config_value_from_yaml(key):
    global _config
    if not _config:
        _config = _load_config()

    ptr = _config
    for var in key.split('.'):
        if ptr and var in ptr:
            ptr = ptr[var]
        else:
            return None
    return ptr


def _get_config_value_from_env(key):
    return os.environ.get(key.replace('.', '_').upper())


def get_config_value(key, default=None, fail_if_missing=False):
    """
    Retrieve a value from the opsbot config. Dict levels are dot separated in the key.
    :param key: the configuration key.
    :param default: Default value if key not found in config.
    :param fail_if_missing: If true and key is missing in config, log error and exit app.
    :return: the configured value or None.
    """
    value = _get_config_value_from_env(key)
    if not value:
        value = _get_config_value_from_yaml(key)
    if not value:
        value = default
    if not value and fail_if_missing:
        logger.critical(f"Required configuration '{key}' is missing.")
        exit(-1)
    return value
