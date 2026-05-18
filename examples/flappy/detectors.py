"""State representation for the Flappy HS.

Each detector is a pure function on the obs dict, returning a derived
fact the policy needs. Adding a new aspect of perception (e.g. distance
to next pipe in ticks rather than px) should be a new detector here,
not new logic in policy.py.
"""
from __future__ import annotations


def next_gap_top(obs: dict) -> float | None:
    """Y coordinate of the top edge of the next pipe's gap, or None if no
    pipe is currently ahead of the bird."""
    return obs.get("next_pipe_gap_top")


def predicted_y(obs: dict) -> float:
    """One-tick forward extrapolation of bird_y given current vy. Used as
    the policy's decision criterion to react one tick before the bird
    physically crosses a target threshold."""
    return obs["bird_y"] + obs["bird_vy"]
