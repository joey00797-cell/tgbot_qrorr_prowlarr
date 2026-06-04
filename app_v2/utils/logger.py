import logging
import sys
from datetime import datetime, timezone, timedelta
KYIV_TZ = timezone(timedelta(hours=3))
class KyivFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=KYIV_TZ)
        return dt.strftime(datefmt or '%d.%m %H:%M:%S')
    def format(self, record):
        mapping = {
            'DEBUG': 'DEB ',
            'INFO': 'INFO',
            'WARNING': 'WARN',
            'ERROR': 'ERR ',
            'CRITICAL': 'CRIT'
        }
        record.levelname = mapping.get(record.levelname, record.levelname[:4])
        return super().format(record)
def setup_logger(debug: bool = False):
    formatter = KyivFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%d.%m %H:%M:%S'
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiogram.event').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
