"""Project chatbot: answers questions about API Optimizer from project_knowledge.txt.

The knowledge file is the only source. With ESONE_GEMINI_API_KEY set, Gemini
phrases the answer from that file; without it (or when Gemini fails) the
closest section of the file is returned as is.
"""
from esone_api.chatbot.engine import (
    ANSWERED_BY_GEMINI,
    ANSWERED_BY_NOTES,
    ChatbotEngine,
    get_chatbot,
    load_sections,
    reset_chatbot,
)

__all__ = [
    "ANSWERED_BY_GEMINI",
    "ANSWERED_BY_NOTES",
    "ChatbotEngine",
    "get_chatbot",
    "load_sections",
    "reset_chatbot",
]
