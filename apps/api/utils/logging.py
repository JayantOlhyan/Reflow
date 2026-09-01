import logging
import sys
import re
from datetime import datetime

SENSITIVE_PATTERNS = [
    (re.compile(r'(api[_-]?key|token|secret|password|authorization|access_token|refresh_token)\s*[:=]\s*([^\s,\'\"]+)', re.IGNORECASE), r'\1: [REDACTED]'),
    (re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE), r'Bearer [REDACTED]'),
    (re.compile(r'AIzaSy[A-Za-z0-9_\-]{33}'), r'[REDACTED]'),
    (re.compile(r'sk-[A-Za-z0-9_\-]{20,}'), r'[REDACTED]'),
    (re.compile(r'client_secret=[^\s&]+', re.IGNORECASE), r'client_secret=[REDACTED]')
]

def sanitize_log_message(message: str) -> str:
    """Redacts sensitive credentials and tokens from log output."""
    sanitized = str(message)
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        service = getattr(record, 'service', 'ReflowAPI')
        msg = sanitize_log_message(record.getMessage())
        req_id = getattr(record, 'request_id', '')
        req_part = f" [{req_id}]" if req_id else ""
        return f"[{timestamp}] [{record.levelname:<5}] [{service}]{req_part} {msg}"

def get_logger(service_name: str = "ReflowAPI") -> logging.Logger:
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(RedactingFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = get_logger("Reflow")
