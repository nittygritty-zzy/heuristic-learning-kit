# Flappy-HS PoC

A working proof-of-concept of **Heuristic Learning** (Weng 2026) applied
to a game environment. Same HS pattern as the AITL-HL PoC (customer
support text), now driving a headless Flappy Bird simulation.

The maintained artifact is **code**. The maintainer is **Claude Code**.
The env is pure stdlib — no pygame, no display.

See `CLAUDE.md` for the seven HS components and their invariants.

## Quickstart

```bash
# 1. Seed the eval set (once)
python flappy_hs.py seeds_add --seeds 100 101 102 103 104

# 2. Run the baseline policy and record a trial
python flappy_hs.py eval \
  --trial-name "baseline_v0_never_flap" \
  --notes "naive never-flap policy" \
  --files policy.py

# 3. See state
python flappy_hs.py report
cat STATUS.md

# 4. From inside Claude Code:
#       /flappy-update
#    Claude reads STATUS.md + recent trials, edits policy.py / detectors.py,
#    re-runs eval, records.

# 5. Verify deterministic reproduction
python flappy_hs.py replay
```

## What's HL about this

- Inference path: zero LLM calls. `policy.py` is pure Python rules.
- Memory: explicit and inspectable (`memory.md`, `trials.jsonl`, git).
- Regression: `eval_seeds.jsonl` is the fixed seed set; every edit must
  not drop `score_mean` below the previous best.
- Probes: `flappy_hs.py probe` runs the policy on ad-hoc seeds without
  refreshing the best score — for testing edge cases.

## What's Claude-Code-native about this

- `/flappy-update` is a project-scoped skill, not an SDK call.
- `CLAUDE.md` auto-loaded each session; invariants don't need
  re-pasting.
- `.claude/settings.json` denies edits to append-only files at the tool
  layer — even if the agent forgets the invariant, the harness blocks
  the edit.
