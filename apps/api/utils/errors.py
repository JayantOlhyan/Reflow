from enum import Enum
from typing import Dict, Any, Optional

class ErrorCategory(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    MEDIA_ERROR = "MEDIA_ERROR"
    AI_ERROR = "AI_ERROR"
    PLATFORM_ERROR = "PLATFORM_ERROR"
    PLUGIN_ERROR = "PLUGIN_ERROR"
    GOVERNANCE_ERROR = "GOVERNANCE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class ErrorCode(str, Enum):
    MEDIA_PROBE_FAILED = "MEDIA_PROBE_FAILED"
    MEDIA_TRANSCODE_FAILED = "MEDIA_TRANSCODE_FAILED"
    PLATFORM_TOKEN_EXPIRED = "PLATFORM_TOKEN_EXPIRED"
    PLATFORM_RATE_LIMIT = "PLATFORM_RATE_LIMIT"
    PLATFORM_PUBLISH_FAILED = "PLATFORM_PUBLISH_FAILED"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_API_KEY_INVALID = "AI_API_KEY_INVALID"
    STORAGE_WRITE_FAILED = "STORAGE_WRITE_FAILED"
    STORAGE_READ_FAILED = "STORAGE_READ_FAILED"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
    STALE_JOB_TIMEOUT = "STALE_JOB_TIMEOUT"
    JOB_MAX_RETRIES_EXCEEDED = "JOB_MAX_RETRIES_EXCEEDED"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    DEPENDENCY_UNHEALTHY = "DEPENDENCY_UNHEALTHY"

class ReflowBaseException(Exception):
    """
    Standardized Reflow Exception carrying error category, error code,
    correlation context, and secret-redacted debugging details.
    """
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL_ERROR,
        error_code: Optional[ErrorCode] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        job_id: Optional[str] = None,
        content_id: Optional[str] = None,
        publication_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.error_code = error_code
        self.details = details or {}
        self.request_id = request_id
        self.job_id = job_id
        self.content_id = content_id
        self.publication_id = publication_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "category": self.category.value,
            "error_code": self.error_code.value if self.error_code else None,
            "details": self.details,
            "request_id": self.request_id,
            "job_id": self.job_id,
            "content_id": self.content_id,
            "publication_id": self.publication_id
        }
