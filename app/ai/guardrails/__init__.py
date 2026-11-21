"""
Basic AI guardrails.

- ``injection``  heuristic prompt-injection detection for user input and
                 uploaded documents
- ``pii``        regex masking of emails, phone numbers, and card numbers
                 before text leaves the service
- ``output``     grounding and shape checks on model answers
- ``events``     audit trail (``guardrail_events`` table)
- ``pipeline``   the input screen the chat and assistant routes call

These are heuristics. They raise the bar and leave an audit trail; they do
not guarantee complete protection, and the limitations are documented in
each module.
"""
from app.ai.guardrails.pipeline import ScreenResult, screen_messages

__all__ = ["ScreenResult", "screen_messages"]
