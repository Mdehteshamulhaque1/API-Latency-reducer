"""
Custom exceptions for the application.
Provides structured error handling throughout the app.
"""
from typing import Any, Dict, Optional


class APIException(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "API_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(APIException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class ResourceNotFoundError(APIException):
    """Raised when a resource is not found."""

    def __init__(self, resource_name: str, resource_id: Any = None):
        message = f"{resource_name} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource_name, "id": resource_id},
        )


class ResourceAlreadyExistsError(APIException):
    """Raised when trying to create a duplicate resource."""

    def __init__(self, resource_name: str, field: str, value: Any):
        super().__init__(
            message=f"{resource_name} with {field}='{value}' already exists",
            status_code=409,
            error_code="RESOURCE_ALREADY_EXISTS",
            details={"resource": resource_name, "field": field, "value": value},
        )


class ValidationError(APIException):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class RateLimitError(APIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60, details: Optional[Dict] = None):
        error_details = details or {}
        error_details["retry_after"] = retry_after
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=error_details,
        )


class DatabaseError(APIException):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database error", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )


class CacheError(APIException):
    """Raised when cache operations fail."""

    def __init__(self, message: str = "Cache operation failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CACHE_ERROR",
            details=details,
        )


class ExternalServiceError(APIException):
    """Raised when external service calls fail."""

    def __init__(self, service_name: str, message: str = None, details: Optional[Dict] = None):
        msg = message or f"External service '{service_name}' error"
        error_details = details or {}
        error_details["service"] = service_name
        super().__init__(
            message=msg,
            status_code=503,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
        )
