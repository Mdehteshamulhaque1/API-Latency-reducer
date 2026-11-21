"""
Pydantic schemas for the knowledge base: documents, search, grounded answers.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    status: str
    error_message: Optional[str]
    chunk_count: int
    character_count: int
    flagged: bool
    flag_detail: Optional[str]
    embedding_model: Optional[str]
    owner_id: Optional[int]
    created_at: datetime


class DocumentList(BaseModel):
    items: List[DocumentItem]
    total: int
    vector_entries: Optional[int] = Field(default=None, description="Chunks in the vector store, None if unavailable")
    max_upload_mb: int
    supported_types: List[str]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: Optional[int] = None
    min_similarity: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SourceChunk(BaseModel):
    document_id: int
    filename: str
    position: int
    text: str
    similarity: float
    flagged: bool = False


class SearchResponse(BaseModel):
    query: str
    results: List[SourceChunk]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class AskResponse(BaseModel):
    question: str
    answer: str
    insufficient_context: bool
    sources: List[SourceChunk]
    grounding_score: float = Field(description="Share of answer sentences supported by the sources (lexical check)")
    model: Optional[str]
    cached: bool
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    latency_ms: float
