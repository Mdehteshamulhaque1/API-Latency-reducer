"""
Structured logging configuration.
"""
import json
import logging
import sys
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from app.config import settings


class CorrelationIdFilter(logging.Filter):
    """
    Adds correlation ID from context to log records.
    """
    def __init__(self):
        super().__init__()
        self._correlation_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = getattr(record, 'correlation_id', 'N/A')
        return True

    @property
    def correlation_id(self):
        return self._correlation_id

    @correlation_id.setter
    def correlation_id(self, value):
        self._correlation_id = value


def configure_logging():
    """Configure structured logging for the application."""
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # JSON formatter
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s',
        timestamp=True,
    )
    
    # Console handler with JSON logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    root_logger.addFilter(correlation_filter)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
