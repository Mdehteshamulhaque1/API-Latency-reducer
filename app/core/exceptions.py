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
