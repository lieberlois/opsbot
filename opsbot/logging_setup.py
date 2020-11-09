import json
import logging
import threading
import os
import traceback
from datetime import datetime
from logging.config import dictConfig
from distutils.util import strtobool
context_data = threading.local()


def configure_logging():
    if bool(strtobool(os.environ.get('OPSBOT_LOCAL', 'False'))):
        formatter = 'text'
    else:
        formatter = 'json'

    dictConfig({
        'version': 1,
        'formatters': {
            'json': {
                '()': 'opsbot.logging_setup.JsonFormatter'
            },
            'text': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': formatter,
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    })
    for handler in logging.root.handlers:
        handler.addFilter(HealthCheckFilter())


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        try:
            return 'GET /health' not in record.msg
        except:
            return True


class JsonFormatter(logging.Formatter):

    def __init__(self):
        logging.Formatter.__init__(self)
        self.version = '0.0.1'

    def format(self, record):
        try:
            message = record.msg % record.args
        except:
            message = str(record.msg)
        entry = dict(
            timestamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            level=record.levelname,
            logger=record.name,
            message=message,
            thread=record.threadName,
            app_name="opsbot",
            app_version=self.version,
        )
        entry['class'] = record.pathname
        if record.exc_info:
            entry['exception'] = ''.join(traceback.format_exception(*record.exc_info))
        return json.dumps(entry)
