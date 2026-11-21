"""
Regex-based PII masking.

Before user text is sent to an external model, obvious personal data is
replaced with placeholders so it never leaves the service:

    jane@example.com          -> [EMAIL]
    +1 (415) 555-0199          -> [PHONE]
    4111 1111 1111 1111        -> [CARD]   (only if the Luhn check passes)

The placeholders keep the sentence readable for the model ("contact
[EMAIL] about the order"), which is enough for the assistant's use cases.

Limitations: names, addresses, and national id numbers are not detected;
obfuscated emails ("jane at example dot com") are missed; long numeric ids
such as order or invoice numbers can be masked as phone numbers (false
positive). Microsoft Presidio can replace this module later behind the
same ``mask_text`` function.
"""
import re
from dataclasses import dataclass, field
from typing import Dict

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# 10-15 digits with optional +, and up to two separators (space, dash, dot,
# parentheses) between digits, e.g. "+1 (415) 555-0199" or "0415-555-0199".
PHONE_RE = re.compile(r"(?<![\w.])\+?\(?(?:\d[\s().-]{0,2}){9,14}\d(?![\w.])")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def _luhn_valid(digits: str) -> bool:
    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


@dataclass
class MaskResult:
    text: str
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def masked(self) -> bool:
        return any(self.counts.values())

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def mask_text(text: str) -> MaskResult:
    """Replace emails, card numbers, and phone numbers with placeholders."""
    if not text:
        return MaskResult(text=text, counts={})
    counts: Dict[str, int] = {"email": 0, "card": 0, "phone": 0}

    def _email(match: re.Match) -> str:
        counts["email"] += 1
        return "[EMAIL]"

    def _card(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn_valid(digits):
            counts["card"] += 1
            return "[CARD]"
        return match.group(0)

    def _phone(match: re.Match) -> str:
        counts["phone"] += 1
        return "[PHONE]"

    masked = EMAIL_RE.sub(_email, text)
    masked = CARD_RE.sub(_card, masked)
    masked = PHONE_RE.sub(_phone, masked)
    return MaskResult(text=masked, counts={k: v for k, v in counts.items() if v})
