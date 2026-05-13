"""
Application-wide constants.
"""

# API Versions
API_V1_PREFIX = "/api/v1"
API_V2_PREFIX = "/api/v2"

# Cache Configuration
CACHE_TTL_DEFAULT = 3600  # 1 hour
CACHE_TTL_SHORT = 300    # 5 minutes
CACHE_TTL_LONG = 86400   # 24 hours
CACHE_TTL_NEVER = -1     # Never expire

# Rate Limiting
RATE_LIMIT_ANONYMOUS_REQUESTS = 100
RATE_LIMIT_ANONYMOUS_PERIOD = 3600

RATE_LIMIT_AUTHENTICATED_REQUESTS = 1000
RATE_LIMIT_AUTHENTICATED_PERIOD = 3600

# User Roles
class UserRole:
    """User role constants."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


# Cache Keys
CACHE_KEY_USER_PREFIX = "user:"
CACHE_KEY_RULE_PREFIX = "rule:"
CACHE_KEY_ANALYTICS_PREFIX = "analytics:"
CACHE_KEY_RATE_LIMIT_PREFIX = "rate_limit:"

# HTTP Headers
HEADER_X_REQUEST_ID = "X-Request-ID"
HEADER_X_CORRELATION_ID = "X-Correlation-ID"
HEADER_X_USER_ID = "X-User-ID"

# Error Messages
ERROR_UNAUTHORIZED = "Unauthorized"
ERROR_FORBIDDEN = "Forbidden"
ERROR_NOT_FOUND = "Resource not found"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded"
ERROR_INVALID_CREDENTIALS = "Invalid credentials"
ERROR_USER_ALREADY_EXISTS = "User already exists"
ERROR_DATABASE_ERROR = "Database error"

# Success Messages
SUCCESS_CREATED = "Resource created successfully"
SUCCESS_UPDATED = "Resource updated successfully"
SUCCESS_DELETED = "Resource deleted successfully"
