"""
Application-wide constants. Everything configurable lives in app.config.
"""

API_V1_PREFIX = "/api/v1"

# Default TTL for cache entries when a rule does not specify one (seconds)
CACHE_TTL_DEFAULT = 3600


class UserRole:
    """User role constants."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


# Request-log attribution. ``api_logs.service`` names the application a row
# belongs to; this service's own middleware writes SELF_SERVICE, monitored
# applications (e.g. Esone) ship their rows through POST /ingest/requests.
SELF_SERVICE = "api-optimizer"
DIRECTION_INBOUND = "inbound"    # a request the service served
DIRECTION_OUTBOUND = "outbound"  # a call the service made to another host
DIRECTIONS = (DIRECTION_INBOUND, DIRECTION_OUTBOUND)


# Redis key prefixes
CACHE_KEY_RULE_PREFIX = "rule:"          # cached HTTP responses
CACHE_KEY_CHAT_PREFIX = "chat:"          # exact-match LLM responses
CACHE_KEY_RULES_LIST = "cache:enabled_rules"
CACHE_RULES_LIST_TTL = 10

# HTTP headers
HEADER_X_CORRELATION_ID = "X-Correlation-ID"
