# Iteration Guide

Lessons distilled from the three example projects. Read this before
starting a long iteration arc — most of these patterns will save you
from the failure modes the examples surfaced.

## The shape of a healthy iteration

From the three examples:

| Project | Iterations | Failed (reverted) | Breakthroughs |
|---|---|---|---|
| flappy | 12 | 6 | 3 (v1=2.6, v7=9.6, v8=63, v12=76) |
| blackjack | 5 | 1 | 4 (v1=mimic, v2=upcard, v4=double, v5=split) |
| aitl | 0 (scaffold only) | — | — |

Roughly **2-3 failures per breakthrough** at minimum. This matches the
article's Ant case study. If you're getting many fewer failures, you're
probably not really iterating (just polishing). If you're getting many
more, you're not reading `memory.md` before each attempt.

The article's framing: the failure log is what makes the system
*learn*. Quote: *与神经网络把经验压进权重完全不一样：HL 的历史是显式、
可读、可删、可重构的。它负责"记住"，也负责把一堆局部补丁压缩成更简单
的表示。*

## When the env has a forward simulation model — math first

If the env is deterministic and the state space is small enough to
reason about, **derive constraints algebraically before trying
behavioral fixes.**

Concrete example from flappy (extracted from
`examples/flappy/memory.md`):

The failure (v8 dies on seed 100): the flap rebound from the bird's
position at the moment of flap clipped the upper pipe.

The math:
- 1-tick lookahead means flap fires at `y = target - vy`
- Rebound = sum of `-vy` over one flap-and-decay cycle = 36 px (fixed)
- min_y after rebound = `target - vy - 36`

Two constraints:
- min_y ≥ gap_top (don't clip upper pipe) with worst-case `vy=12`:
  → `target ≥ gap_top + 48`
- body_bottom ≤ gap_bottom at flap moment:
  → `target ≤ gap_top + 50`

**Combined: `gap_top + 48 ≤ target ≤ gap_top + 50`. A 2-px window.**
v8's `GAP_BIAS=45` was outside; the fix was a single constant: `49`.

This single-line change (verified by stress testing at 1M ticks/seed,
zero deaths over ~92,300 pipe encounters) emerged from algebra, not
from a "try GAP_BIAS=46, 47, 48..." parameter sweep.

**When to do this:** if you can write down the env's update rule in
closed form, you can almost always derive the policy's safe envelope
from it. Don't reach for behavioral hacks like "cap velocity" until
you've ruled out the algebraic fix.

**When to skip this:** envs with too much state to analyze
(MuJoCo Ant's full-body dynamics), or stochastic envs where any
analytical constraint has a long tail. In those, lean on the
empirical iteration loop.

## Probing past `maybe`

Stochastic envs have noisy eval. The kit's `is_new_best` returns three
exit codes, not two:

- **`yes` (exit 0)**: improvement is CI-separated from prior best.
- **`maybe` (exit 2)**: higher EV but CIs overlap.
- **`no` (exit 1)**: EV did not exceed prior best.

`maybe` is **not** "iteration failed". It means the eval can't confirm
the gain at the current sample size. The gain might be real.

The blackjack example surfaces this concretely. In v3 → v4 → v5:

| step | 50k-hand eval | gate | true EV (1M-hand probe) |
|---|---|---|---|
| v3 (hit/stand) | -0.0173 ± 0.0044 | (baseline) | -0.0234 |
| v4 (+ doubling) | -0.0032 ± 0.0050 | maybe | -0.0109 (+0.0125) |
| v5 (+ splitting) | +0.0002 ± 0.0051 | maybe | -0.0075 (+0.0034) |

**Three consecutive `maybe` verdicts hid three real gains** totaling
+0.0159 EV per hand (landing at the textbook ceiling for the rule set).
A naive reading would have stopped iteration at v3.

The right action on `maybe`:

1. Run the driver's `probe` subcommand at 5-10× the eval's sample size,
   focused on the same seeds.
2. If the probe confirms the gain, accept the change as the new best.
3. Update `memory.md` "Solved boundary cases" with the gain + probe
   sample size + lesson.

**Why this is the gate's design:** strict `>` on a noisy signal would
crown random fluctuations as new bests, polluting the iteration log
with false positives. `maybe` is the system asking for more data, not
declaring failure.

## Naming trials to be greppable later

Trial names are the agent's primary key into its own memory. The
convention from the article's Breakout case study:

- `tunnel0_v1` — parameter + value + version (the agent set
  `tunnel_offset=0`, version 1)
- `ant_mpc_residual_warm02_eval5` — variant tag + sub-parameter +
  evaluation episodes

For this kit's projects:

- `update_v3_broaden_return_regex` — version + what changed
- `update_v5_target_42_lookahead_1` — version + key parameters
- `simplify_v1_collapse_response_dict` — kind + version + scope
- `probe_v3_ceiling_search_100k` — kind + version + purpose

Avoid: `try1`, `experiment_a`, `trial_2026-05-17`. Time-stamped names
don't help future iterations grep for past hypotheses.

## Compression as required maintenance

After every confirmed new best, simplify. The article quotes:

> 只增长不压缩的 HS，最后一定会变成屎山代码。

The simplify pass should:

1. Confirm baseline: `python <driver>.py eval` is all green.
2. Look for: dead branches (no trial in history exercises them),
   duplicated regex patterns, multiple `if` arms collapsing to a dict
   lookup, long if-chains becoming table lookups.
3. Edit. Behavior must be **identical** on every regression case.
4. Re-eval. Score must be unchanged.
5. Append to `memory.md` "Compression history" with line-count delta
   and what was merged.

If the policy is already minimal (e.g. flappy's final 6 lines), the
simplify pass becomes a no-op. Record it that way.

## Memory entries that compound

Useful `memory.md` entries are not "what I tried" — they're "what
*lesson* survives." The article's pattern:

```markdown
- **2026-05-17 — update_v9_asymmetric_lookahead**
  Tried lookahead=2 when vy>8 to fix seed-100. Regressed from 63 → 6.4.
  vy>8 also fires during normal-osc peak descent (~8), so the policy
  starts over-flapping inside the gap.

  **Lesson:** detect "between pipes" by next_pipe_dx, not by vy.
  Asymmetric thresholds on shared signals leak across regimes.
```

Three parts:
- **The artifact** (`update_v9_asymmetric_lookahead`) — gives the next
  agent a greppable handle.
- **What happened** (regressed 63 → 6.4 + the proximate cause).
- **The Lesson:** line — generalizes the failure so future iterations
  in *any* domain with the same shape benefit.

Entries without a Lesson line decay. Entries with one compound.

## When to stop iterating

Two clear stop signals:

1. **Score saturates the eval ceiling.** Flappy hit 76/76 on every
   seed at `max_ticks=5000`. Further iteration on the *eval* won't
   reveal more — switch to the **policy ceiling search** (a probe at
   longer episodes or more seeds) to find the policy's intrinsic
   limit. Flappy's policy held up at 1M ticks with zero deaths.

2. **Math says you're optimal.** When you can write the policy's
   safety condition as a closed-form inequality and your constants are
   in the safe interior, further iteration on the policy is wasted.
   Confirm with one stress test; ship.

Without a stop signal, iteration tends to add lines without adding EV.
That's how rule systems decay into mud.
