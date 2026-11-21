"""
Single entry point for the LLM used by the AI features.

The assistant and the RAG answerer never talk to a provider directly; they
go through the existing gateway (``ChatService``) and therefore inherit its
exact-match cache, retries, fallback model, circuit breaker, metrics, and
cost estimation. Tests replace ``get_chat_service`` with a factory that
returns a service backed by a fake transport.
"""
from app.services.chat import ChatService


def get_chat_service() -> ChatService:
    return ChatService()
