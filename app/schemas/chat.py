"""
Schemas for the LLM chat gateway.
"""
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message sent to the LLM provider."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1, max_length=32000)


class ChatUsage(BaseModel):
    """Token accounting returned by the LLM provider."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class ChatRequest(BaseModel):
    """Request body for the chat completion endpoint."""

    messages: list[ChatMessage] = Field(..., min_length=1, max_length=50)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class ChatResponse(BaseModel):
    """Chat completion response returned to the caller."""

    id: str
    model: str
    served_model: str | None = None
    fallback_used: bool = False
    content: str
    finish_reason: str | None = None
    usage: ChatUsage = Field(default_factory=ChatUsage)
    latency_ms: float = Field(default=0.0, ge=0)
    cached: bool = False
    created: int | None = None
