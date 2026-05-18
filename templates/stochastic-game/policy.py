"""Programmatic policy for the Blackjack HS.

Pure stdlib. No network, no LLM. Edited by the /blackjack-update skill.
"""
from __future__ import annotations

from detectors import (
    can_double, can_split, dealer_upcard, hand_total, is_pair_of, is_soft,
)


def act(obs: dict) -> int:
    """Return 0 (stand), 1 (hit), 2 (double), or 3 (split).

    Full basic strategy for S17, no DAS, no resplit:
      Splits (only when can_split):
        - A,A and 8,8: always split
        - 2,2 / 3,3 / 7,7: split vs 2-7
        - 6,6:           split vs 2-6
        - 9,9:           split vs 2-6, 8, 9 (stand vs 7, 10, A)
        - 4,4 / 5,5 / 10,10: never split (5s prefer double; 10s stand)
      Doubles (only when can_double):
        - Hard 9 vs 3-6, hard 10 vs 2-9, hard 11 vs 2-10
        - Soft A,2 / A,3 vs 5-6; A,4 / A,5 vs 4-6; A,6 / A,7 vs 3-6
      Hit/stand:
        - inherits v3 logic
    """
    total = hand_total(obs["player"])
    soft = is_soft(obs["player"])
    up = dealer_upcard(obs)

    # --- split layer (only on initial pair) ---
    if can_split(obs):
        pair = is_pair_of(obs)
        if pair == 11:               # A,A — always
            return 3
        if pair == 8:                # 8,8 — always
            return 3
        if pair in (2, 3, 7) and up in (2, 3, 4, 5, 6, 7):
            return 3
        if pair == 6 and up in (2, 3, 4, 5, 6):
            return 3
        if pair == 9 and up in (2, 3, 4, 5, 6, 8, 9):
            return 3
        # 4,4 / 5,5 / 10,10: never split — fall through to hard-total logic

    # --- doubling layer (only on initial 2-card hand) ---
    if can_double(obs):
        if not soft:
            if total == 11 and up != 11:                          return 2
            if total == 10 and up not in (10, 11):                return 2
            if total == 9 and up in (3, 4, 5, 6):                 return 2
        else:
            if total in (13, 14) and up in (5, 6):                return 2
            if total in (15, 16) and up in (4, 5, 6):             return 2
            if total in (17, 18) and up in (3, 4, 5, 6):          return 2

    # --- v3 hit/stand fallthrough ---
    if soft:
        if total <= 17:
            return 1
        if total == 18:
            return 1 if up in (9, 10, 11) else 0
        return 0

    if total >= 17:
        return 0
    if total <= 11:
        return 1
    if total == 12:
        return 0 if up in (4, 5, 6) else 1
    return 0 if up in (2, 3, 4, 5, 6) else 1
