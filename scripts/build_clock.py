"""Explicit reproducible build clock; publishing/discovery still use real time."""
import datetime as dt
import os

def now():
    value=os.environ.get('SOURCE_DATE_EPOCH')
    return dt.datetime.fromtimestamp(int(value),dt.timezone.utc) if value else dt.datetime.now(dt.timezone.utc)
