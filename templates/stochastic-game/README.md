# Blackjack-HS PoC

A working proof-of-concept of **Heuristic Learning** (Weng 2026)
applied to blackjack. Same HS scaffolding as the AITL-HL (text) and
Flappy (deterministic game) PoCs, now on a stochastic card game where
variance matters and the regression gate has to be CI-aware.

The maintained artifact is **code**. The maintainer is **Claude Code**.
The env is pure stdlib — no card-game library, no display.

See `CLAUDE.md` for the seven HS components and their invariants.

## Quickstart

```bash
# 1. Seed the eval set (once)
python blackjack_hs.py seeds_add --seeds 100 101 102 103 104

# 2. Run the baseline policy and record a trial
python blackjack_hs.py eval \
  --trial-name "baseline_v0_always_stand" \
  --notes "naive always-stand baseline" \
  --files policy.py

# 3. See state
python blackjack_hs.py report
cat STATUS.md

# 4. From inside Claude Code:
#       /blackjack-update
#    Claude reads STATUS.md + recent trials, edits policy.py / detectors.py,
#    re-runs eval, records.

# 5. Verify deterministic reproduction
python blackjack_hs.py replay
```

## Rules summary

- Heads-up player vs. dealer.
- Dealer stands on all 17 (S17).
- Blackjack pays 3:2.
- Infinite shoe (IID card draws). No counting.
- Player actions: 0 = stand, 1 = hit, 2 = double, 3 = split.
  `can_double` and `can_split` are surfaced in obs.
- House rules: no re-split, no DAS, split aces get one card only.
  No surrender or insurance.
- Score per trial = expected value per hand (mean unit return),
  averaged across all hands in the eval set.

## Why blackjack is a good HL target

- **Deterministic env given seed.** Replay is reliable.
- **Known optimal policy.** Basic strategy is a 270-cell lookup table
  iteration should converge toward.
- **Low per-hand variance** (stddev ~1.15) compared to poker. 50k
  hands per eval gives SE ~ 0.005, enough to resolve real
  improvements.
- **Discrete action space, short horizon.** One hand = at most ~5
  decisions. No long-horizon credit assignment.

## Variance-aware iteration

Unlike flappy (deterministic), blackjack eval signals are noisy.
The driver's `is_new_best` requires the new eval's **CI95 lower bound**
to exceed the prior best's **CI95 upper bound** before declaring a
refresh. Three exit codes:

- `0`: `yes` — confident improvement, may simplify.
- `2`: `maybe` — higher EV but CI overlaps; don't crown as new best.
- `1`: `no` — EV did not exceed prior best.

This is the article's regression gate adapted for stochastic eval.

## Layout

```
.
├── README.md
├── CLAUDE.md
├── blackjack_hs.py   driver: eval · probe · seeds_add · replay · report · is_new_best
├── policy.py         (HS-1) programmatic policy
├── detectors.py      (HS-2) state representation
├── blackjack.py      env (do not edit during normal maintenance)
├── trials.jsonl      (HS-4) experiment records (append-only)
├── summary.csv       (HS-4) flat view of trials.jsonl (derived)
├── STATUS.md         (HS-4) human-readable snapshot (derived)
├── eval_seeds.jsonl  (HS-5) regression seed set (append-only)
├── memory.md         (HS-6) failed directions, compression history
└── .claude/
    ├── settings.json     permission allowlist + append-only deny
    └── skills/
        └── blackjack-update/SKILL.md
```
