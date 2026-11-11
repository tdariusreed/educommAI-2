"""Safety gate. Runs before anything else sees the student's message.

This is a baseline (patterns, not a classifier). It does three things:
  1. scrub personal info (emails, phones, SSNs, street addresses) so it is never stored or logged
  2. block prompt-injection attempts
  3. catch self-harm language and respond with care instead of routing to career advice
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PII = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email removed]"),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[number removed]"),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"), "[phone removed]"),
    ("address", re.compile(
        r"\b\d{1,6}\s+(?:[A-Za-z0-9.]+\s+){1,4}(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|court|ct|way)\b\.?",
        re.I), "[address removed]"),
]

_INJECTION = [
    re.compile(r"ignore (?:all |any |your |the )?(?:previous|prior|above|earlier)\s+(?:instructions|rules|prompts?)", re.I),
    re.compile(r"disregard (?:all |any |your |the )?(?:previous|prior|above|earlier)?\s*(?:instructions|rules)", re.I),
    re.compile(r"(?:reveal|show|print|repeat)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)", re.I),
    re.compile(r"\byou are now\b.{0,40}\b(?:dan|unrestricted|jailbroken)\b", re.I),
    re.compile(r"developer mode|jailbreak", re.I),
]

_SELF_HARM = re.compile(
    r"\b(?:kill myself|suicid\w*|end my life|want to die|self[- ]?harm|hurt myself|cut myself)\b", re.I)

_UNSAFE = re.compile(r"\b(?:porn\w*|nude|sexting|how to make (?:a )?(?:bomb|weapon))\b", re.I)

CRISIS_REPLY = (
    "I'm really glad you told me, and I'm sorry things feel this heavy. You deserve support from a real person "
    "right now. Please talk to a trusted adult, like a parent, teacher, or school counselor. You can also call or "
    "text **988** (the Suicide & Crisis Lifeline) any time, day or night. If you are in danger right now, call 911. "
    "I'm here for career questions whenever you want to come back to them."
)
INJECTION_REPLY = "I can't change how I work, but I'm happy to help you explore careers, college, and programs. What are you curious about?"
UNSAFE_REPLY = "That's not something I can help with. I can help you explore careers, classes, college, and scholarships. What would you like to look at?"


@dataclass
class SafetyResult:
    allowed: bool
    text: str                      # scrubbed text (safe to store and log)
    flags: list[str] = field(default_factory=list)
    reply: str = ""                # what to say if blocked


def scrub_pii(text: str) -> tuple[str, list[str]]:
    flags = []
    for name, pattern, repl in _PII:
        if pattern.search(text):
            flags.append(f"pii:{name}")
            text = pattern.sub(repl, text)
    return text, flags


def check_input(text: str, max_chars: int = 2000) -> SafetyResult:
    text = (text or "").strip()[:max_chars]
    if _SELF_HARM.search(text):
        return SafetyResult(False, "[message withheld]", ["self_harm"], CRISIS_REPLY)
    if any(p.search(text) for p in _INJECTION):
        return SafetyResult(False, "[message withheld]", ["injection"], INJECTION_REPLY)
    if _UNSAFE.search(text):
        return SafetyResult(False, "[message withheld]", ["unsafe_topic"], UNSAFE_REPLY)
    clean, flags = scrub_pii(text)
    return SafetyResult(True, clean, flags)


def check_output(text: str) -> tuple[str, list[str]]:
    """Last pass over the final answer: never echo personal info back."""
    return scrub_pii(text)
