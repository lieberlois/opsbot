import os
from pathlib import Path

CORE_PLUGINS = ["help"]

OPSBOT_CONFIG_FILE_ENV = "OPSBOT_CONFIG_FILE"
OPSBOT_CONFIG_FILE_DEFAULT = f"{os.getcwd()}/opsbot_config.yaml"

APP_DIR = Path(__file__).parent.parent
ROOT_DIR = APP_DIR.parent
