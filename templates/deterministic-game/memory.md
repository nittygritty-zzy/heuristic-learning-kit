# Flappy HS — memory

Maintained by the coding agent during `/flappy-update` runs.

## Design rationale

- `flappy.py` is pure stdlib so the env runs in any Python. No pygame, no
  display, no third-party deps. Coordinates are screen-style (y down).
- `detectors.py` derives facts from the obs dict (gap_center,
  is_below_gap_center). The obs is already structured, so detectors do
  less work than in Breakout — they exist mainly so the agent can grow
  perception (e.g. predicted_y_at_pipe) without entangling `policy.py`.
- `flappy_hs.py eval` runs the policy on every seed in `eval_seeds.jsonl`
  and records a single trial row. Per-seed scores are preserved in the
  `per_seed` field for debugging.

## Failed directions (do not retry)

- **2026-05-17 — `update_v2_velocity_aware` (LOOKAHEAD=3 with gravity term)**
  Tried `predicted_y = bird_y + vy*N + 0.5*N*(N+1)`. With N=3 and gravity=1
  this adds +6 to predicted_y even when vy=0, so the policy flaps too
  aggressively on the first few ticks (before any pipe is in range) and
  the bird hits the ceiling. All 5 eval seeds died at identical tick 63.
  Reverted to `update_v1_follow_center` (score_mean=2.60).

  **Lesson:** when adding a predictive term, keep the constant (no-velocity)
  bias small or zero. Lookahead is fine; predicting fall *while already
  falling* is fine; predicting fall *while stationary* over-flaps.

- **2026-05-17 — `update_v3_velocity_projection` (vy * 4 lookahead, no gravity)**
  Tried `projected_y = bird_y + vy * 4`. Same regression as v2: all 5 eval
  seeds die at tick 62-63, this time hitting the **top** of the gap.
  Trace on seed 100 (gap_top=99.8, center=134.8): bird oscillated near
  gap_top (y=74–88) because each flap from y≈133 with vy≈1 projected to
  y=137, triggering a flap that sent bird up 45 px (one flap-and-decay
  cycle). Reverted to `update_v1_follow_center`.

  **Lesson:** for a tight gap (70 px) with a strong flap (-9 vy), even
  a small lookahead × small positive vy can trigger a flap whose rise
  exceeds the gap height. The bandwidth of safe oscillation is narrow.
  Either reduce lookahead to ≤1 or aim BELOW center, not at center.

- **2026-05-17 — `update_v9_asymmetric_lookahead` (lookahead=2 when vy>8)**
  Tried to fix the seed-100 inter-pipe failure (bird reaches MAX_VY=12
  between pipes; rebound from there clips gap_top by 2.1 px) by using
  2-tick lookahead when vy > 8. Regressed from 63.00 → 6.40. The vy>8
  branch fires not only between pipes but also during normal
  oscillation (peak descent vy of the steady state is around 8), so the
  policy starts over-flapping inside the gap. Reverted to v8.

  **Lesson:** an asymmetric rule that triggers on a velocity threshold
  can leak into the steady-state regime. Better fix: detect "between
  pipes" by `next_pipe_dx` (distance to next pipe), not by vy. Or:
  cap the bird's vertical speed before it reaches a new pipe by adding
  a flap during the inter-pipe gap. Not pursued here — v8 score=63 is
  the current best.

## Compression history

- **2026-05-17 — `simplify_v1_remove_dead_detectors_wire_in_policy`**
  After v12 hit the eval ceiling (76/76) and the 1M-tick stress test
  showed no failure mode, ran the mandated post-best-score
  simplification pass.

  Removed:
  - `detectors.gap_center` — unused since v8 (last reader was v1).
  - `detectors.is_below_gap_center` — never used by any working policy.
  - The if/else block in `policy.act` that unpacked `obs.get(...)` and
    `obs["bird_y"] + obs["bird_vy"]` inline.

  Added:
  - `detectors.next_gap_top(obs)` and `detectors.predicted_y(obs)` —
    the two detectors `policy.act` actually needs. `policy.py` now
    imports them, so detectors.py is no longer disconnected from the
    policy as it had been since v8.
  - Trimmed the GAP_BIAS comment in policy.py to point at this file
    instead of restating the math.

  Line-count delta: `policy.py` 38 → 24, `detectors.py` 24 → 21,
  combined -17 lines. Behavior preserved: 5/5 at 76 on eval seeds and
  6/6 at 15384 on the 1M-tick stress set, identical to v12.

  **Lesson:** "simplification" in HL is not only about lines of code —
  the bigger win here was eliminating the *disconnect* between
  detectors.py (declared as a HS component in CLAUDE.md) and
  policy.py (which had stopped using it). A module that exists by
  convention but is not actually called is a slow-rotting form of
  coupling: future agents will keep deferring to its docstring
  description while the policy quietly drifts past it.

## Solved boundary cases

- **2026-05-17 — seed 100 (v12, GAP_BIAS=45 → 49)**
  v8 (GAP_BIAS=45) cleared 4/5 seeds but seed 100 died at t=778 with
  the rebound clipping gap_top by 2 px. Initial hypotheses (velocity
  cap via vy > 9, next_pipe_dx gate, drop lookahead entirely) were
  *all* dead ends — probe data showed every surviving seed also
  reaches vy=12 between pipes, so vy alone isn't an inter-pipe
  signature; and dropping lookahead opened a fall-through to
  gap_bottom (regression to 0.40).

  The fix turned out to be a 4-px nudge to GAP_BIAS, derived by
  walking the rebound math carefully:
    - 1-tick lookahead means flap fires at y = target - vy
    - rebound = 36 px (sum of vy from -9 to 0 after one flap)
    - so min_y after rebound = target - vy - 36
    - for min_y ≥ gap_top with worst-case vy = 12: target ≥ gap_top + 48
    - for body_bottom ≤ gap_bottom at flap moment: target ≤ gap_top + 50

  GAP_BIAS = 49 sits in the 2-px-wide safe range. All 5 eval seeds +
  20 unseen probe seeds now score the time-limit max of 76.

  **Lesson:** when the system has a clear forward-simulation model
  (here: deterministic physics), prefer deriving constraints from
  first principles before trying behavioral fixes. The "velocity cap"
  family of fixes I tried (v9, v11) were chasing a symptom; the
  actual constraint was a tight inequality the geometry already
  imposed, and v8 was just barely on the wrong side of it.

- **2026-05-17 — real ceiling search for v12**
  After v12 hit the time-limit cap on all 5 eval seeds (`max_ticks=5000`,
  score 76 each), ran progressively longer episodes to find the policy's
  intrinsic ceiling:

  | max_ticks  | theoretical max | observed | alive_at_end |
  |------------|-----------------|----------|--------------|
  | 5,000      | 76              | 76       | yes (5/5)    |
  | 50,000     | 769             | 768      | yes (5/5)    |
  | 200,000    | 3,076           | 3,076    | yes (5/5)    |
  | 100,000    | 1,538           | 1,538    | yes (9/9, recorded as `probe_v3_ceiling_search_100k`) |
  | 1,000,000  | 15,384          | 15,384   | yes (6/6, incl. seeds 13, 999, 12345) |

  Total observed pipe encounters across all ceiling-search runs:
  ~92,300. Zero deaths. The v12 policy has no empirically discoverable
  failure mode within this env's normal regime.

  **Lesson:** "policy ceiling" and "evaluation ceiling" are different
  things. With `max_ticks=5000` the v12 row in summary.csv showed
  76/76 — but 76 was the *evaluation* ceiling, not the policy's. For
  truly bounded eval seeds, the meaningful metric becomes
  `alive_at_end_count / n_seeds`, not score. The probe subcommand was
  the right venue to surface this since it doesn't update
  best_score_mean and so doesn't pollute the eval timeline.
