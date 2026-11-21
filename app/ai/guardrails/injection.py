"""
Heuristic prompt-injection detection.

A prompt injection is text that tries to change what the model is allowed
to do ("ignore your instructions", "reveal the system prompt", "you are now
an unrestricted assistant"). This module scores text against a list of
known phrasings. It is intentionally simple and transparent:

* every rule has a name, a regex, and a severity;
* the result lists the matched rule names so an operator can see why;
* the highest matched severity decides the outcome: ``high`` blocks the
  request (when blocking is enabled), ``medium`` and ``low`` are allowed
  but recorded.

Limitations: paraphrases, other languages, encodings (base64, leetspeak),
and multi-turn attacks are not caught. Treat this as a tripwire plus an
audit trail, not a guarantee.
"""
import re
from dataclasses import dataclass, field
from typing import List, Tuple

SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}

# (rule name, compiled pattern, severity)
RULES: List[Tuple[str, re.Pattern, str]] = [
    (
        "ignore_previous_instructions",
        re.compile(r"\b(ignore|disregard|forget)\b[^.\n]{0,40}\b(previous|prior|above|earlier|all|your)\b[^.\n]{0,30}\b(instructions?|rules?|prompts?|guidelines?)\b", re.I),
        "high",
    ),
    (
        "reveal_system_prompt",
        re.compile(r"\b(reveal|show|print|repeat|output|leak|dump)\b[^.\n]{0,40}\b(system|hidden|secret|initial|original)\b[^.\n]{0,20}\b(prompt|instructions?|message)\b", re.I),
        "high",
    ),
    (
        "role_override",
        re.compile(r"\byou are now\b|\bfrom now on you (are|will|must)\b|\bact as (an? )?(unrestricted|unfiltered|jailbroken)\b", re.I),
        "high",
    ),
    (
        "developer_mode_jailbreak",
        re.compile(r"\b(developer|god|dan|jailbreak|unfiltered) mode\b|\bdo anything now\b", re.I),
        "high",
    ),
    (
        "override_safety",
        re.compile(r"\b(bypass|override|disable|turn off)\b[^.\n]{0,30}\b(safety|guardrails?|filters?|restrictions?|policy|policies)\b", re.I),
        "high",
    ),
    (
        "fake_system_marker",
        re.compile(r"<\|im_start\|>|<\|system\|>|\[system\]|\bBEGIN SYSTEM PROMPT\b|^\s*system\s*:", re.I | re.M),
        "medium",
    ),
    (
        "instruction_header",
        re.compile(r"^\s*#{1,6}\s*(new )?(instructions?|system)\b", re.I | re.M),
        "medium",
    ),
    (
        "exfiltrate_secrets",
        re.compile(r"\b(api[_ ]?keys?|passwords?|secret[_ ]?keys?|tokens?|credentials?)\b[^.\n]{0,40}\b(send|post|email|upload|exfiltrate|print|reveal)\b|\b(send|post|email|upload|exfiltrate|print|reveal)\b[^.\n]{0,40}\b(api[_ ]?keys?|passwords?|secret[_ ]?keys?|credentials?)\b", re.I),
        "medium",
    ),
    (
        "do_not_follow_rules",
        re.compile(r"\b(do not|don't|never) (follow|obey|respect)\b[^.\n]{0,30}\b(rules?|instructions?|guidelines?|policy)\b", re.I),
        "medium",
    ),
    (
        "pretend_no_restrictions",
        re.compile(r"\bpretend\b[^.\n]{0,40}\b(no|without)\b[^.\n]{0,20}\b(restrictions?|rules?|limits?|filters?)\b", re.I),
        "medium",
    ),
    (
        "assistant_impersonation",
        re.compile(r"^\s*assistant\s*:", re.I | re.M),
        "low",
    ),
    (
        "hidden_text_markers",
        re.compile(r"\[hidden\]|\[invisible\]|\bthis (text|message) is (hidden|invisible)\b", re.I),
        "low",
    ),
]


@dataclass
class InjectionResult:
    severity: str = "none"
    matched: List[str] = field(default_factory=list)

    @property
    def detected(self) -> bool:
        return self.severity != "none"


def scan_text(text: str) -> InjectionResult:
    """Return the highest matched severity and every matched rule name."""
    if not text:
        return InjectionResult()
    matched: List[str] = []
    severity = "none"
    for name, pattern, rule_severity in RULES:
        if pattern.search(text):
            matched.append(name)
            if SEVERITY_ORDER[rule_severity] > SEVERITY_ORDER[severity]:
                severity = rule_severity
    return InjectionResult(severity=severity, matched=matched)


def scan_texts(texts: List[str]) -> InjectionResult:
    """Scan several texts and merge the results."""
    merged = InjectionResult()
    for text in texts:
        result = scan_text(text)
        for name in result.matched:
            if name not in merged.matched:
                merged.matched.append(name)
        if SEVERITY_ORDER[result.severity] > SEVERITY_ORDER[merged.severity]:
            merged.severity = result.severity
    return merged
