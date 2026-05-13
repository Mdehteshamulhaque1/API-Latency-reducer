"""
Correlation ID middleware for request tracking.
"""
import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.constants import HEADER_X_CORRELATION_ID

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Adds correlation ID to requests for tracing.
    """

    async def dispatch(self, request: Request, call_next):
        """Add correlation ID to request."""
        
        # Get correlation ID from header or create new one
        correlation_id = request.headers.get(
            HEADER_X_CORRELATION_ID,
            str(uuid.uuid4())
        )
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[HEADER_X_CORRELATION_ID] = correlation_id
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={"correlation_id": correlation_id}
        )
        
        return response
