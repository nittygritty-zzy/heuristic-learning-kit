"""Minimal headless Flappy Bird simulation. Pure stdlib, fully deterministic.

Coordinate system: x rightward, y downward (screen-style; y=0 is top).
Single action per tick: 0 = noop, 1 = flap.

The env exposes:
    reset(seed) -> State
    step(state, action) -> State        (mutates state in-place and returns it)
    make_obs(state) -> dict             (the observation the policy sees)
    play(policy_fn, seed, max_ticks)    (one episode end-to-end)

Constants are tuned so that:
- a "never flap" policy dies in ~30 ticks with score 0
- a "follow gap center" policy can score a few pipes
- a velocity-aware predictive policy can score 20+
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


# ---- Game constants -------------------------------------------------------
SCREEN_W = 288
SCREEN_H = 512
BIRD_X = 50
BIRD_SIZE = 20
GRAVITY = 1.0
FLAP_VY = -9.0
MAX_VY = 12.0
PIPE_WIDTH = 52
PIPE_GAP = 70                             # tighter than reference flappy (~100)
PIPE_SPEED = 3.5
PIPE_SPAWN_TICKS = 65                     # one new pipe every N ticks
PIPE_GAP_TOP_MIN = 50.0
PIPE_GAP_TOP_MAX = float(SCREEN_H - 50 - PIPE_GAP)


# ---- State ----------------------------------------------------------------
@dataclass
class Pipe:
    x: float          # left edge
    gap_top: float    # y of top of gap (gap spans [gap_top, gap_top+PIPE_GAP])
    scored: bool = False


@dataclass
class State:
    bird_y: float
    bird_vy: float
    pipes: list[Pipe]
    score: int
    tick: int
    alive: bool
    rng: random.Random = field(repr=False)


# ---- Env API --------------------------------------------------------------
def reset(seed: int) -> State:
    rng = random.Random(seed)
    first_gap = rng.uniform(PIPE_GAP_TOP_MIN, PIPE_GAP_TOP_MAX)
    return State(
        bird_y=SCREEN_H / 2,
        bird_vy=0.0,
        pipes=[Pipe(x=float(SCREEN_W), gap_top=first_gap)],
        score=0,
        tick=0,
        alive=True,
        rng=rng,
    )


def step(s: State, action: int) -> State:
    """One tick. Mutates s and returns it. No-op if already dead."""
    if not s.alive:
        return s

    if action == 1:
        s.bird_vy = FLAP_VY
    s.bird_vy = min(s.bird_vy + GRAVITY, MAX_VY)
    s.bird_y += s.bird_vy
    s.tick += 1

    for p in s.pipes:
        p.x -= PIPE_SPEED

    if s.tick % PIPE_SPAWN_TICKS == 0:
        s.pipes.append(Pipe(
            x=float(SCREEN_W),
            gap_top=s.rng.uniform(PIPE_GAP_TOP_MIN, PIPE_GAP_TOP_MAX),
        ))
    s.pipes = [p for p in s.pipes if p.x + PIPE_WIDTH > 0]

    for p in s.pipes:
        if not p.scored and p.x + PIPE_WIDTH < BIRD_X:
            p.scored = True
            s.score += 1

    if s.bird_y < 0 or s.bird_y + BIRD_SIZE > SCREEN_H:
        s.alive = False
        return s
    for p in s.pipes:
        if (p.x < BIRD_X + BIRD_SIZE
                and p.x + PIPE_WIDTH > BIRD_X
                and (s.bird_y < p.gap_top
                     or s.bird_y + BIRD_SIZE > p.gap_top + PIPE_GAP)):
            s.alive = False
            return s

    return s


def make_obs(s: State) -> dict:
    """Observation: bird state + nearest upcoming pipe.

    Keys:
        bird_y, bird_vy        — float
        next_pipe_dx           — float or None (None when no pipe ahead)
        next_pipe_gap_top      — float or None
        next_pipe_gap_bottom   — float or None
    """
    upcoming = [p for p in s.pipes if p.x + PIPE_WIDTH > BIRD_X]
    np_ = upcoming[0] if upcoming else None
    return {
        "bird_y": s.bird_y,
        "bird_vy": s.bird_vy,
        "next_pipe_dx": (np_.x - BIRD_X) if np_ else None,
        "next_pipe_gap_top": np_.gap_top if np_ else None,
        "next_pipe_gap_bottom": (np_.gap_top + PIPE_GAP) if np_ else None,
    }


def play(policy_fn, seed: int, max_ticks: int = 5000) -> dict:
    """Run one episode. Returns {score, ticks, alive_at_end}."""
    s = reset(seed)
    while s.alive and s.tick < max_ticks:
        action = policy_fn(make_obs(s))
        step(s, action)
    return {"score": s.score, "ticks": s.tick, "alive_at_end": s.alive}
