import logging
import sys
import re
from datetime import datetime

SENSITIVE_PATTERNS = [
    (re.compile(r'Bearer\s+\S+', re.IGNORECASE), r'Bearer [REDACTED]'),
    (re.compile(r'(api[_-]?key|token|secret|password|access_token|refresh_token)\s*[:=]\s*([^\s,\'\"]+)', re.IGNORECASE), r'\1: [REDACTED]'),
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

def redact_sensitive_dict(data: dict) -> dict:
    """Redacts authorization headers and key dictionary fields."""
    redacted = {}
    for k, v in data.items():
        lk = str(k).lower()
        if any(sec in lk for sec in ["authorization", "api-key", "apikey", "secret", "token", "password"]):
            redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        service = getattr(record, 'service', 'ReflowAPI')
        msg = sanitize_log_message(record.getMessage())
        
        req_id = getattr(record, 'request_id', '')
        job_id = getattr(record, 'job_id', '')
        content_id = getattr(record, 'content_id', '')
        
        ids_part = ""
        if req_id or job_id or content_id:
            parts = []
            if req_id: parts.append(f"req:{req_id}")
            if job_id: parts.append(f"job:{job_id}")
            if content_id: parts.append(f"content:{content_id}")
            ids_part = f" [{', '.join(parts)}]"
            
        return f"[{timestamp}] [{record.levelname:<5}] [{service}]{ids_part} {msg}"

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
