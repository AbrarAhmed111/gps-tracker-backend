from datetime import datetime
from dateutil import parser as date_parser
import pytz


def parse_datetime(value: str, tz: str = "UTC") -> datetime:
    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        tzinfo = pytz.timezone(tz)
        return tzinfo.localize(dt)
    return dt

