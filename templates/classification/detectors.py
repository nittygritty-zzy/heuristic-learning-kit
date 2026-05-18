"""State representation for the AITL Heuristic System.

Detectors read a raw customer query and emit structured facts. They are
deliberately separate from policy.py so perception (how we read the world)
can evolve independently from response logic (what we say). Each detector
must be a pure function: stdlib only, no side effects, no I/O.
"""
from __future__ import annotations

import re


Intent = str    # "refund" | "shipping" | "return" | "unknown"
Urgency = str   # "normal" | "high"


def intent(q: str) -> Intent:
    s = q.lower()
    if re.search(r"\brefund", s):
        return "refund"
    if re.search(r"\bship|deliver|tracking|package", s):
        return "shipping"
    if re.search(r"\breturn|send.*back", s):
        return "return"
    return "unknown"


def urgency(q: str) -> Urgency:
    if re.search(r"\b(urgent|asap|today|right now|immediately)\b", q.lower()):
        return "high"
    return "normal"
