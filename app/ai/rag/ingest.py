"""
Document ingestion: validate -> hash -> extract -> scan -> chunk -> embed -> store.

Failure handling: if embedding or the vector store fails, the document row
is kept with ``status="failed"`` and a short error message so the user can
see what happened and retry by deleting and re-uploading. Nothing is left
half-written in the vector store because vectors are only added after every
chunk embedded successfully.
"""
import hashlib
import logging
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails.events import CATEGORY_DOCUMENT_FLAGGED, record_event
from app.ai.guardrails.injection import scan_text
from app.ai.rag.chunk import chunk_text
from app.ai.rag.embeddings import get_embedding_client
from app.ai.rag.extract import UnsupportedDocumentError, extract_text, validate_upload
from app.ai.rag.store import get_vector_store
from app.config import settings
from app.core.exceptions import ExternalServiceError, ResourceAlreadyExistsError, ResourceNotFoundError
from app.models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest(
        self,
        *,
        filename: str,
        data: bytes,
        owner_id: Optional[int],
        correlation_id: Optional[str] = None,
    ) -> Document:
        """Store one uploaded file as searchable chunks. Returns the Document row."""
        content_type = validate_upload(filename, len(data), settings.max_upload_mb * 1024 * 1024)

        content_hash = hashlib.sha256(data).hexdigest()
        existing = await self.session.execute(select(Document).where(Document.content_hash == content_hash))
        duplicate = existing.scalar_one_or_none()
        if duplicate is not None:
            raise ResourceAlreadyExistsError("Document", "content", duplicate.filename)

        extracted = extract_text(filename, data)
        chunks = chunk_text(extracted.text, settings.rag_chunk_size, settings.rag_chunk_overlap)
        if not chunks:
            raise UnsupportedDocumentError("The document produced no text chunks.")

        # Uploaded content is untrusted: note instruction-like text so the
        # security page can show it. The document is still indexed; the
        # answerer treats every chunk as data, never as instructions.
        scan = scan_text(extracted.text)
        flag_detail = ",".join(scan.matched)[:255] if scan.detected else None

        document = Document(
            owner_id=owner_id,
            filename=filename[:255],
            content_type=content_type,
            size_bytes=len(data),
            content_hash=content_hash,
            status="pending",
            character_count=len(extracted.text),
            chunk_count=len(chunks),
            flagged=scan.detected,
            flag_detail=flag_detail,
        )
        self.session.add(document)
        await self.session.flush()  # assigns document.id

        # The audit event is written with its own session AFTER this one
        # commits; writing it mid-transaction would wait on SQLite's lock.
        async def _flag_event() -> None:
            if scan.detected:
                await record_event(
                    category=CATEGORY_DOCUMENT_FLAGGED,
                    severity=scan.severity,
                    feature="documents",
                    detail=f"{filename[:120]}: {flag_detail}",
                    user_id=owner_id,
                    correlation_id=correlation_id,
                )

        embedder = get_embedding_client()
        try:
            vectors = await embedder.embed(chunks)
            ids = [f"{document.id}:{position}" for position in range(len(chunks))]
            await get_vector_store().add(
                ids=ids,
                embeddings=vectors,
                texts=chunks,
                metadatas=[
                    {"document_id": document.id, "position": position, "filename": document.filename}
                    for position in range(len(chunks))
                ],
            )
        except ExternalServiceError as exc:
            document.status = "failed"
            document.error_message = (exc.details or {}).get("reason", "embedding_failed")[:255]
            await self.session.commit()
            await _flag_event()
            logger.warning("Document %s ingestion failed: %s", document.id, document.error_message)
            raise
        except Exception as exc:  # noqa: BLE001
            document.status = "failed"
            document.error_message = f"vector_store:{type(exc).__name__}"[:255]
            await self.session.commit()
            await _flag_event()
            logger.error("Document %s vector store write failed: %s", document.id, exc)
            raise ExternalServiceError(
                "VectorStore", "Vector store is unavailable", details={"reason": "vector_store_unavailable"}
            ) from exc

        self.session.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    position=position,
                    text=text,
                    character_count=len(text),
                    vector_id=f"{document.id}:{position}",
                )
                for position, text in enumerate(chunks)
            ]
        )
        document.status = "ready"
        document.embedding_model = embedder.model
        await self.session.commit()
        await self.session.refresh(document)
        await _flag_event()
        logger.info(
            "Document ingested",
            extra={"document_id": document.id, "chunks": len(chunks), "flagged": scan.detected},
        )
        return document

    async def delete(self, document_id: int) -> None:
        """Remove the document, its chunks, and its vectors."""
        document = (
            await self.session.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if document is None:
            raise ResourceNotFoundError("Document", document_id)

        try:
            await get_vector_store().delete_document(document_id)
        except Exception as exc:  # noqa: BLE001
            # Vectors without a SQL row are never returned to users (hydration
            # filters them), so finish the deletion and log the leftover.
            logger.error("Vector cleanup failed for document %s: %s", document_id, exc)

        await self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        await self.session.delete(document)
        await self.session.commit()

    async def list(self, limit: int = 100) -> List[Document]:
        result = await self.session.execute(
            select(Document).order_by(Document.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, document_id: int) -> Document:
        document = (
            await self.session.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if document is None:
            raise ResourceNotFoundError("Document", document_id)
        return document
