"""
Vector store backed by ChromaDB (local, persistent, cosine similarity).

ChromaDB's client is synchronous, so every call is pushed to a worker thread
with ``asyncio.to_thread``; the event loop never blocks on disk I/O.

One collection, ``documents``, holds every chunk. Each entry stores the
vector, the chunk text (so search results need no second lookup), and
metadata used for filtering and deletion: ``document_id``, ``position``,
``filename``.
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"


@dataclass
class VectorHit:
    vector_id: str
    text: str
    similarity: float
    metadata: Dict


class VectorStore:
    """Thin async wrapper around one ChromaDB collection."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self._collection = None

    # ---- lifecycle ----------------------------------------------------
    def _get_collection(self):
        if self._collection is None:
            import chromadb  # imported lazily: heavy, and optional for non-RAG use

            os.makedirs(self.persist_dir, exist_ok=True)
            client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = client.get_or_create_collection(
                COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def ping(self) -> bool:
        try:
            await asyncio.to_thread(lambda: self._get_collection().count())
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Vector store unavailable: %s", exc)
            return False

    # ---- writes --------------------------------------------------------
    async def add(
        self,
        *,
        ids: List[str],
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict],
    ) -> None:
        if not ids:
            return

        def _add():
            self._get_collection().add(
                ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
            )

        await asyncio.to_thread(_add)

    async def delete_document(self, document_id: int) -> None:
        def _delete():
            self._get_collection().delete(where={"document_id": int(document_id)})

        await asyncio.to_thread(_delete)

    # ---- reads ---------------------------------------------------------
    async def query(
        self,
        embedding: List[float],
        *,
        top_k: int,
        document_id: Optional[int] = None,
    ) -> List[VectorHit]:
        def _query():
            collection = self._get_collection()
            if collection.count() == 0:
                return None
            kwargs = {
                "query_embeddings": [embedding],
                "n_results": max(1, min(top_k, collection.count())),
                "include": ["documents", "metadatas", "distances"],
            }
            if document_id is not None:
                kwargs["where"] = {"document_id": int(document_id)}
            return collection.query(**kwargs)

        raw = await asyncio.to_thread(_query)
        if not raw or not raw.get("ids") or not raw["ids"][0]:
            return []

        hits: List[VectorHit] = []
        for vector_id, text, metadata, distance in zip(
            raw["ids"][0], raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
        ):
            # Cosine distance = 1 - cosine similarity.
            hits.append(
                VectorHit(
                    vector_id=vector_id,
                    text=text or "",
                    similarity=round(max(0.0, 1.0 - float(distance)), 4),
                    metadata=metadata or {},
                )
            )
        return hits

    async def count(self) -> int:
        return await asyncio.to_thread(lambda: self._get_collection().count())


_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Process-wide store; tests swap it for one pointed at a temp directory."""
    global _store
    if _store is None or _store.persist_dir != settings.chroma_persist_dir:
        _store = VectorStore()
    return _store
