"""Programmatic policy for the Flappy HS.

Pure stdlib. No network, no LLM. Edited by the /flappy-update skill.
"""
from __future__ import annotations

from detectors import next_gap_top, predicted_y


SCREEN_MID = 256.0   # SCREEN_H / 2 — used when no pipe is visible
GAP_BIAS = 49.0      # target = gap_top + 49. Sits in the 2-px-wide safe
                     # window [48, 50] derived from the flap rebound
                     # geometry; see memory.md "Solved boundary cases".


def act(obs: dict) -> int:
    """Return 0 (noop) or 1 (flap).

    Flap when the 1-tick predicted bird position exceeds the target
    height (gap_top + GAP_BIAS, or screen mid if no pipe is visible).
    """
    gap_top = next_gap_top(obs)
    target_y = SCREEN_MID if gap_top is None else gap_top + GAP_BIAS
    return 1 if predicted_y(obs) > target_y else 0
