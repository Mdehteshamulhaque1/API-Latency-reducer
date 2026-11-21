"""
Semantic retrieval: embed the query, find the nearest chunks, hydrate them.

Only chunks whose document still exists in SQL (and is ``ready``) are
returned, so a half-deleted document can never leak into an answer.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag.embeddings import get_embedding_client
from app.ai.rag.store import get_vector_store
from app.config import settings
from app.models import Document

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    document_id: int
    filename: str
    position: int
    text: str
    similarity: float
    flagged: bool = False


class RetrievalService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        document_id: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        top_k = top_k or settings.rag_top_k
        min_similarity = settings.rag_min_similarity if min_similarity is None else min_similarity

        query = query.strip()
        if not query:
            return []

        vectors = await get_embedding_client().embed([query])
        hits = await get_vector_store().query(vectors[0], top_k=top_k, document_id=document_id)
        if not hits:
            return []

        wanted_ids = {int(hit.metadata.get("document_id", -1)) for hit in hits}
        rows = await self.session.execute(
            select(Document).where(Document.id.in_(wanted_ids), Document.status == "ready")
        )
        documents = {doc.id: doc for doc in rows.scalars().all()}

        results: List[RetrievedChunk] = []
        for hit in hits:
            if hit.similarity < min_similarity:
                continue
            document = documents.get(int(hit.metadata.get("document_id", -1)))
            if document is None:
                continue
            results.append(
                RetrievedChunk(
                    document_id=document.id,
                    filename=document.filename,
                    position=int(hit.metadata.get("position", 0)),
                    text=hit.text,
                    similarity=hit.similarity,
                    flagged=document.flagged,
                )
            )
        return results
