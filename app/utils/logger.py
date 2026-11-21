"""
Structured (JSON) logging to stdout.

Every record carries a ``correlation_id`` field so one request can be
followed across middleware, services, and background tasks. The id is set
by CorrelationIdMiddleware and passed through ``extra={...}``; records that
have none get "N/A" so the field is always present for log parsers.
"""
import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.config import settings


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "N/A"
        return True


def configure_logging() -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s", timestamp=True)
    )
    handler.addFilter(_CorrelationIdFilter())
    root.addHandler(handler)
    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
