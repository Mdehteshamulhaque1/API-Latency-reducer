"""
AI layer: guardrails, the performance assistant, and the RAG pipeline.

Everything under ``app.ai`` is built on top of the existing LLM gateway
(``app.services.chat.ChatService``) and fails soft: a problem in this
package produces a controlled error for the AI feature only and never
affects caching, rate limiting, or analytics.
"""
