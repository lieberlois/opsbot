from opsbot.logging_setup import configure_logging
from .opsbot import OpsBot

if __name__ == "__main__":
    configure_logging()
    opsbot = OpsBot()
    opsbot.run(port=5000, debug=False)
