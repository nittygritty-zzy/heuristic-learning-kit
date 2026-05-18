"""Programmatic policy for the AITL Heuristic System.

Pure Python rules. No network, no LLM, no imports beyond stdlib and
detectors. Inference cost is ~zero. Maintained by the coding agent via
the /aitl-update skill.
"""
from detectors import intent, urgency


RESPONSES = {
    "refund":   "Refunds post to the original payment method within 5 business days. [refund-5d]",
    "shipping": "Standard US shipping takes 3-5 business days. [ship-3to5]",
    "return":   "Items are returnable within 30 days of delivery. [returns-30d]",
}


def respond(q: str) -> str:
    i = intent(q)
    if i == "unknown":
        return "Not sure — escalating to a human agent."
    base = RESPONSES[i]
    if urgency(q) == "high":
        base = "I hear you — flagging this as urgent. " + base
    return base
