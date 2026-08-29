import logging
import sys
import re
from datetime import datetime
from typing import Any, Dict

SENSITIVE_PATTERNS = [
    re.compile(r'(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*([^\s,]+)', re.IGNORECASE)
]

def sanitize_log_message(message: str) -> str:
    """Redacts sensitive credentials and tokens from log output."""
    sanitized = str(message)
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r'\1: [REDACTED]', sanitized)
    return sanitized

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        service = getattr(record, 'service', 'ReflowAPI')
        msg = sanitize_log_message(record.getMessage())
        
        # Standard structured terminal format
        return f"[{timestamp}] [{record.levelname:<5}] [{service}] {msg}"

def get_logger(service_name: str = "ReflowAPI") -> logging.Logger:
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = get_logger("Reflow")
