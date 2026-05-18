# Blackjack Heuristic System

A self-maintaining blackjack policy. Inference is pure Python;
maintenance is a Claude Code coding agent. Same HS pattern as the
AITL-HL and Flappy PoCs, applied to a stochastic card game where
variance matters more than in flappy.

| HS component (Weng 2026) | File / mechanism                                  |
|--------------------------|---------------------------------------------------|
| 程序策略                  | `policy.py` (`act(obs) -> int`)                   |
| 状态表示                  | `detectors.py` + `blackjack.make_obs`             |
| 反馈入口                  | `blackjack_hs.py` (eval · probe · report · replay) |
| 实验记录                  | `trials.jsonl` + `summary.csv` (derived)          |
| 回放 / 测试                | `eval_seeds.jsonl` + `blackjack_hs.py replay`     |
| memory                   | `memory.md` + git log                             |
| 更新机制                  | `/blackjack-update` skill                         |

## Invariants (never violate)

1. **Pure-Python policy.** `policy.py` and `detectors.py` use stdlib
   only, plus `from detectors import ...` and `from blackjack import ...`
   in `policy.py`. No network, no LLM, no third-party packages.

2. **Append-only history.** `trials.jsonl` and `eval_seeds.jsonl` are
   append-only. Never delete or rewrite a row. `summary.csv` and
   `STATUS.md` are derived and never hand-edited. The project
   `.claude/settings.json` denies edits on these.

3. **Variance-aware regression gate.** Blackjack EV per hand has
   per-trial standard error ~0.005 in a 50k-hand eval. A naive `>`
   comparison would crown noise as improvement. Every `/blackjack-update`
   ends by calling `python blackjack_hs.py is_new_best`, which requires
   the new CI95 lower bound to exceed the prior best's CI95 upper bound
   before declaring `yes`. Outcomes:
   - `yes` (exit 0): real improvement, may trigger simplification.
   - `maybe` (exit 2): higher EV but CI overlaps prior best — do NOT
     commit as a refresh; the next iteration should re-eval with more
     hands to disambiguate, or accept and move on.
   - `no` (exit 1): EV did not exceed prior best. Revert.

4. **Failed directions get written down.** Append abandoned approaches
   to `memory.md` under "Failed directions" so the next round doesn't
   retry them.

5. **Generalize, don't memorize.** The eval set is 5 seeds × 10000
   hands = 50k IID hands. A fix that wins on one seed but loses on
   another is overfitting to seed-specific card sequences. Cross-check
   per-seed EV before accepting.

6. **Close the loop.** Every `/blackjack-update` ends with
   `python blackjack_hs.py eval --trial-name <label> --notes <why>
   --files <what>`. The eval row records what the new policy DID, not
   metadata about the edit. The edit itself lives in git.

7. **Auto-simplify on confident new best.** After eval, run
   `python blackjack_hs.py is_new_best`. Only on exit code 0 (`yes`)
   does the shipped `policy.py` reflect a refreshed best — and at that
   point simplification should run. On `maybe` (exit 2), defer
   simplification until the gain is confirmed.

## Files at a glance

- `blackjack.py` — env. Don't edit during normal maintenance.
- `policy.py` — the live policy. Edit freely (within invariant 1).
- `detectors.py` — perception helpers. Edit freely.
- `blackjack_hs.py` — driver. Don't edit unless adding a channel.
- `trials.jsonl` — every eval + probe, append-only.
- `eval_seeds.jsonl` — the regression seed set, append-only.
- `summary.csv` — flat view of `trials.jsonl`; derived.
- `STATUS.md` — human-readable snapshot; derived.
- `memory.md` — design notes, failed directions, compression history.

## Workflow

```text
python blackjack_hs.py eval --trial-name baseline_v0 --notes "always stand"
python blackjack_hs.py report
/blackjack-update         # Claude Code edits policy/detectors, re-evals, records
python blackjack_hs.py is_new_best   # exit 0 only if CI-separated improvement
```

## Action space (env v2)

The env now supports four actions:

| value | name   | when allowed                       | effect                                         |
|-------|--------|------------------------------------|------------------------------------------------|
| 0     | stand  | always                             | end hand; dealer plays; settle ×1              |
| 1     | hit    | always                             | take one card; if bust, lose ×1                |
| 2     | double | only on initial 2-card hand        | double bet, take 1 card, then stand; settle ×2 |
| 3     | split  | only on initial pair (same value)  | split into two hands, each plays independently |

Obs carries `can_double` and `can_split` flags so the policy can tell
when the new actions are legal. The `detectors.can_double` /
`detectors.can_split` / `detectors.is_pair_of` helpers wrap these.

House rules: dealer S17, BJ pays 3:2, no re-split (max 2 hands),
no double after split (DAS off), split aces get exactly one card each
(21 on split aces is *not* BJ — pays 1:1).

## Useful reference EVs (do not encode as targets)

These are what the *literature* says for an infinite-shoe S17 game:

- Always stand: ~ -0.16
- Always hit: ~ -0.88
- Mimic dealer (hit < 17): ~ -0.08
- Basic strategy (hit/stand only): ~ -0.015 to -0.025
- **Basic strategy + double + split (this env's ceiling): ~ -0.005**

If your policy's EV approaches the bottom row's number, you've
effectively reproduced the textbook lookup table through iteration.
