"""State representation for the Blackjack HS.

Each detector is a pure function on the obs dict, returning a derived
fact the policy uses. Keeping perception separate from policy means the
coding agent can add new facts (e.g. card-counting running count, when
we add a finite shoe) without touching control flow.
"""
from __future__ import annotations


def hand_total(player: list[int]) -> int:
    """Best total <= 21 if possible, otherwise the bust total. Aces flex."""
    total = sum(player)
    aces_high = player.count(11)
    while total > 21 and aces_high > 0:
        total -= 10
        aces_high -= 1
    return total


def is_soft(player: list[int]) -> bool:
    """True iff hand has an ace currently counted as 11 (room to bust safely)."""
    total = sum(player)
    aces_high = player.count(11)
    while total > 21 and aces_high > 0:
        total -= 10
        aces_high -= 1
    return aces_high > 0


def dealer_upcard(obs: dict) -> int:
    """The single dealer card visible to the player (2-10 or 11=ace)."""
    return obs["dealer_upcard"]


def can_double(obs: dict) -> bool:
    """True iff the policy may currently return action=2 (double).
    The env only sets this on the initial 2-card decision."""
    return obs.get("can_double", False)


def can_split(obs: dict) -> bool:
    """True iff the policy may currently return action=3 (split).
    The env only sets this on the initial 2-card decision and when the
    two cards have equal value (10/J/Q/K all count as 10)."""
    return obs.get("can_split", False)


def is_pair_of(obs: dict) -> int | None:
    """If can_split, the card value being split. Otherwise None.
    Useful for split decisions: pair of 8s = 8, pair of aces = 11, etc."""
    if not obs.get("can_split"):
        return None
    return obs["player"][0]
