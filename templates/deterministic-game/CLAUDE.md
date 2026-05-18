# Flappy Heuristic System

A self-maintaining flappy-bird controller. Inference is pure Python;
maintenance is a Claude Code coding agent. Same HS pattern as the
AITL-HL PoC, applied to a game environment.

| HS component (Weng 2026) | File / mechanism                                  |
|--------------------------|---------------------------------------------------|
| 程序策略                  | `policy.py` (`act(obs) -> int`)                   |
| 状态表示                  | `detectors.py` + `flappy.make_obs`                |
| 反馈入口                  | `flappy_hs.py` (eval · probe · report · replay)   |
| 实验记录                  | `trials.jsonl` + `summary.csv` (derived)          |
| 回放 / 测试                | `eval_seeds.jsonl` + `flappy_hs.py replay`        |
| memory                   | `memory.md` + git log                             |
| 更新机制                  | `/flappy-update` skill                            |

## Invariants (never violate)

1. **Pure-Python policy.** `policy.py` and `detectors.py` use stdlib
   only, plus `from detectors import ...` and `from flappy import ...`
   in `policy.py`. No network, no LLM, no third-party packages.

2. **Append-only history.** `trials.jsonl` and `eval_seeds.jsonl` are
   append-only. Never delete or rewrite a row. The project
   `.claude/settings.json` denies edit on these.

3. **No-regress gate.** Every `/flappy-update` ends by running
   `python flappy_hs.py eval` and confirming `score_mean` did not drop
   below the previous best. If it did, revert.

4. **Failed directions get written down.** Append abandoned directions
   to `memory.md` under "Failed directions" so the next round doesn't
   retry them.

5. **Generalize, don't memorize.** A fix that only works on one seed
   is overfitting. Cross-check on multiple seeds via probe before
   accepting it.

6. **Close the loop.** Every `/flappy-update` ends by calling
   `python flappy_hs.py eval --trial-name <label> --notes <why>
   --files <what>`. The eval row records what the new policy DID, not
   metadata about the edit. The edit itself lives in git.

7. **Auto-simplify on new best.** After eval, run
   `python flappy_hs.py is_new_best`. If `yes`, simplify `policy.py`
   while keeping `score_mean` exactly the same on every eval seed, then
   re-record. The shipped policy is always the simplest version that
   holds the current best.

## Files at a glance

- `flappy.py` — headless env. Don't edit during normal maintenance.
- `policy.py` — the live policy. Edit freely (within invariant 1).
- `detectors.py` — perception helpers. Edit freely.
- `flappy_hs.py` — driver. Don't edit unless adding a feedback channel.
- `trials.jsonl` — every eval + probe, append-only.
- `eval_seeds.jsonl` — the regression seed set, append-only.
- `summary.csv` — flat view of `trials.jsonl`; derived.
- `STATUS.md` — human-readable snapshot; derived.
- `memory.md` — design notes, failed directions, compression history.

## Workflow

```text
python flappy_hs.py eval --trial-name baseline_v0 --notes "naive never-flap"
python flappy_hs.py report
/flappy-update    # Claude Code edits policy.py, re-evals, records
python flappy_hs.py is_new_best   # exit 0 if score refreshed
```
