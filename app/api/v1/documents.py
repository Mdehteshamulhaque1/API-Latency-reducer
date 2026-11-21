"""
Knowledge base routes.

/documents            upload (admin, operator), list, get, delete (admin, operator)
/knowledge-base       semantic search and grounded question answering (any role)
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails.events import CATEGORY_UPLOAD_REJECTED, record_event
from app.ai.rag.answer import RAGAnswerService
from app.ai.rag.extract import SUPPORTED_EXTENSIONS, UnsupportedDocumentError
from app.ai.rag.ingest import IngestionService
from app.ai.rag.retrieval import RetrievalService
from app.ai.rag.store import get_vector_store
from app.config import settings
from app.core.exceptions import APIException
from app.core.security import get_current_user, verify_role
from app.database.db import get_session
from app.schemas.documents import (
    AskRequest,
    AskResponse,
    DocumentItem,
    DocumentList,
    SearchRequest,
    SearchResponse,
    SourceChunk,
)

logger = logging.getLogger(__name__)

documents_router = APIRouter(prefix="/documents", tags=["Knowledge Base"])
knowledge_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


def _item(document) -> DocumentItem:
    return DocumentItem.model_validate(document, from_attributes=True)


@documents_router.post("", response_model=DocumentItem, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_role(["admin", "operator"])),
    session: AsyncSession = Depends(get_session),
):
    """Upload a PDF, TXT, or Markdown file and index it for search."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    user_id = int(current_user.get("sub"))
    correlation_id = getattr(request.state, "correlation_id", None)

    try:
        document = await IngestionService(session).ingest(
            filename=file.filename or "upload",
            data=data,
            owner_id=user_id,
            correlation_id=correlation_id,
        )
    except UnsupportedDocumentError as exc:
        await record_event(
            category=CATEGORY_UPLOAD_REJECTED, severity="low", feature="documents",
            detail=str(exc)[:200], user_id=user_id, correlation_id=correlation_id,
        )
        status = 413 if "limit is" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))
    except APIException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return _item(document)


@documents_router.get("", response_model=DocumentList)
async def list_documents(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    documents = await IngestionService(session).list()
    vector_entries = None
    try:
        vector_entries = await get_vector_store().count()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vector store count failed: %s", exc)
    return DocumentList(
        items=[_item(d) for d in documents],
        total=len(documents),
        vector_entries=vector_entries,
        max_upload_mb=settings.max_upload_mb,
        supported_types=sorted(SUPPORTED_EXTENSIONS),
    )


@documents_router.get("/{document_id}", response_model=DocumentItem)
async def get_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        return _item(await IngestionService(session).get(document_id))
    except APIException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@documents_router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: dict = Depends(verify_role(["admin", "operator"])),
    session: AsyncSession = Depends(get_session),
):
    try:
        await IngestionService(session).delete(document_id)
    except APIException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return {"message": "Document deleted"}


@knowledge_router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(
    payload: SearchRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Natural-language search: returns the most similar chunks with scores."""
    results = await RetrievalService(session).search(
        payload.query,
        top_k=payload.top_k,
        min_similarity=payload.min_similarity,
        document_id=payload.document_id,
    )
    return SearchResponse(
        query=payload.query,
        results=[SourceChunk(**vars(chunk)) for chunk in results],
    )


@knowledge_router.post("/ask", response_model=AskResponse)
async def ask_knowledge_base(
    payload: AskRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Answer a question from the uploaded documents, with sources."""
    result = await RAGAnswerService(session).ask(
        payload.question,
        top_k=payload.top_k,
        user_id=int(current_user.get("sub")),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return AskResponse(
        question=payload.question,
        answer=result.answer,
        insufficient_context=result.insufficient_context,
        sources=[SourceChunk(**vars(chunk)) for chunk in result.sources],
        grounding_score=result.grounding_score,
        model=result.model,
        cached=result.cached,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
        latency_ms=result.latency_ms,
    )
