"""
Schemas for request-log ingestion from monitored services.

A monitored application (Esone) batches a record per request it served and
per call it made, and ships them to ``POST /api/v1/ingest/requests``. The
shape mirrors ``api_logs``; nothing here carries request or response bodies.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import DIRECTION_INBOUND, DIRECTIONS

SERVICE_NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{0,49}$"
END_USER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9:_.@-]*$"


class IngestedRequest(BaseModel):
    """One request as observed by the monitored service."""

    service: str = Field(pattern=SERVICE_NAME_PATTERN, description="Monitored service name, e.g. 'esone'")
    direction: str = Field(default=DIRECTION_INBOUND)
    method: str = Field(min_length=1, max_length=10)
    endpoint: str = Field(min_length=1, max_length=500)
    path: Optional[str] = Field(default=None, max_length=500)
    status_code: int = Field(ge=100, le=599)
    response_time_ms: float = Field(ge=0)
    client_ip: str = Field(default="unknown", min_length=1, max_length=45)
    correlation_id: str = Field(default="", max_length=36)
    request_size_bytes: int = Field(default=0, ge=0)
    response_size_bytes: int = Field(default=0, ge=0)
    query_params: Optional[str] = Field(default=None, max_length=2000)
    error_message: Optional[str] = Field(default=None, max_length=500)
    upstream_host: Optional[str] = Field(default=None, max_length=255)
    # Signed-in person the request was made for ("esone:7"): an opaque reference, never a name or email.
    end_user: Optional[str] = Field(default=None, max_length=100, pattern=END_USER_PATTERN)
    # True when the monitored service answered from a cache (for Esone: the
    # answer came from the Optimizer's semantic cache instead of a crawl).
    cache_hit: bool = False
    # When the request happened on the monitored service; defaults to now.
    occurred_at: Optional[datetime] = None

    @field_validator("direction")
    @classmethod
    def _known_direction(cls, value: str) -> str:
        if value not in DIRECTIONS:
            raise ValueError(f"direction must be one of {', '.join(DIRECTIONS)}")
        return value

    @field_validator("method")
    @classmethod
    def _upper_method(cls, value: str) -> str:
        return value.strip().upper()


class IngestBatch(BaseModel):
    records: List[IngestedRequest] = Field(min_length=1, max_length=500)


class IngestResult(BaseModel):
    accepted: int
