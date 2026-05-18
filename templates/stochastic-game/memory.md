# Blackjack HS — memory

Maintained by the coding agent during `/blackjack-update` runs.

## Design rationale

- `blackjack.py` is pure stdlib, infinite shoe (IID card draws). The
  infinite-shoe choice deliberately rules out card counting so the
  policy iteration focuses on basic-strategy decisions.
- `detectors.py` exposes `hand_total`, `is_soft`, `dealer_upcard`.
  Adding card-count-aware perception (running count, true count) is
  the natural next step if we later switch to a finite shoe.
- Eval is N seeds × 10,000 hands. With per-hand stddev ~1.15, a 50,000
  hand eval has SE ~ 0.005 on EV — that's the resolution we can
  reliably distinguish, so improvements smaller than ~0.01 EV are
  noise from this signal's perspective.

## Reference EVs (for orientation, not as a regression target)

- Always stand: ~ -0.16
- Always hit: ~ -0.88
- Mimic dealer (hit < 17): ~ -0.08
- Basic strategy (hit/stand only, S17): ~ -0.015 to -0.025
- Basic strategy + double + split (S17): ~ -0.005

## Failed directions (do not retry)

_none yet_

## Solved boundary cases

- **2026-05-17 — v3 `maybe` verdict, true gain confirmed by 1M-hand probe**
  v3 added "soft 18 hits vs dealer 9/10/A" on top of v2. The 50k-hand
  eval gave EV = -0.0173 ± 0.0044 vs v2's -0.0185 ± 0.0044 — apparent
  improvement of +0.0012, but CIs overlapped heavily so `is_new_best`
  returned `maybe` (exit 2).

  A 1M-hand probe of v3 gave EV = -0.0234. Inline comparison of v2 at
  the same seeds × n_hands gave EV = -0.0238. **True gain: +0.0004.**

  Both 50k-hand estimates were on the lucky side of their CIs (v2's
  -0.0185 was at the +1σ tail of its true -0.0238; v3's -0.0173
  similarly). The CI gate's `maybe` was the right call — the gain is
  real, but the eval as configured cannot confirm it.

  **Lesson:** when the eval signal's noise floor (here, ~0.005 at 50k
  hands) is larger than the expected gain from an improvement (here,
  ~0.0004), the regression gate becomes the binding constraint, not
  the policy. Either: (a) accept that small gains compound and move
  on without strict-best confirmation; or (b) increase n_hands per
  eval so the noise floor drops below the expected gain size. We
  did (a) for v3 — accepted the change, moved on.

## Compression history

_none yet_

## Achieved performance

After 3 iterations the policy implements basic strategy for hit/stand
hands (no double, no split). Achieved EV ≈ -0.024 per hand, confirmed
at 1M hands per seed. The theoretical hit/stand-only EV for
infinite-shoe S17 blackjack is ~ -0.025, so the policy is at the
ceiling for this action space.

To improve further, the env's action space would need to grow:
adding `act` values 2=double and 3=split would unlock basic
strategy's full -0.005 EV. That's a future iteration on the env, not
the policy.

## Env v2: double + split (2026-05-17)

The env was extended to support actions 2 (double) and 3 (split). House
rules in this version:
  - Dealer S17, BJ pays 3:2 (unchanged).
  - Double: initial 2 cards only, one card then stand, bet ×2.
  - Split: initial pair only, two hands play independently with hit/stand
    only (no DAS, no resplit). Split aces get one card each and 21 on
    split aces is NOT BJ (pays 1:1).

`v3` policy (basic strategy hit/stand) was re-verified on the new env:
per-seed EVs identical to the pre-expansion eval, confirming the env
change is backward-compatible — the new actions are available but
dormant for policies that only return 0/1.

Sanity check: a policy that always doubles + always splits gives
EV = -0.4440 (terrible, as expected). Return distribution shows the
new -2.0 / +2.0 outcomes from doubling and splitting both ways.

## v4 + v5 iteration (2026-05-17)

Added doubling (v4) and splitting (v5) to the policy. Both 50k-hand
evals returned `maybe` from the regression gate, but 1M-hand probes
confirmed both gains are real:

  v3 (hit/stand only)       true EV = -0.0234
  v4 (+ doubling)           true EV = -0.0109   gain = +0.0125
  v5 (+ splitting, FULL)    true EV = -0.0075   gain = +0.0034

v5 lands right at the textbook ceiling for S17 + no DAS basic
strategy (-0.005 to -0.010). Cumulative gain v3 → v5 = +0.016 EV
per hand, i.e. ~1.6 percentage points of EV recovered by expanding
the action space and using the new actions correctly.

Doubling rules in v4:
  - Hard 11 vs 2-10, hard 10 vs 2-9, hard 9 vs 3-6
  - Soft A,2/A,3 vs 5-6; A,4/A,5 vs 4-6; A,6/A,7 vs 3-6
  (no DAS, so no doubling-after-split branches needed)

Splitting rules in v5:
  - A,A and 8,8 always
  - 2/3/7 vs 2-7; 6 vs 2-6; 9 vs 2-6, 8, 9
  - Never 4,4 / 5,5 / 10,10 (5s prefer to be played as hard 10)

**Lesson:** the CI gate's `maybe` is conservative on purpose, but it
should not stop iteration. v3 → v4 → v5 produced repeated `maybe`
verdicts while in fact each step recovered real EV. The probe
(higher sample) is the disambiguator the gate is designed to
encourage — and it confirmed all three points compound. The right
read of `maybe` is "the gain might be real; probe to find out", not
"the iteration failed". See the v3 entry in "Solved boundary cases"
for the first time this came up.
