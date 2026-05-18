---
name: flappy-update
description: Iterate the flappy bird policy. Read STATUS.md + recent trials, edit policy.py / detectors.py, re-run eval, and ensure score_mean does not drop below the previous best. Trigger /flappy-simplify automatically if a new best is reached. Use when the user runs /flappy-update or asks to improve the flappy policy.
---

# /flappy-update

You are the maintenance step of a flappy-bird Heuristic System. Read
`CLAUDE.md` first for invariants.

## Procedure

1. **Read state.** Run `cat STATUS.md` for the snapshot. Then look at
   the last 1–2 eval rows in `trials.jsonl` — note score_mean, score_min,
   and per-seed scores. The lowest-scoring seed is usually the one to
   target.

2. **Read memory.** Open `memory.md` and read "Failed directions".
   Do not retry anything listed there.

3. **Form a hypothesis.** Look at `policy.py` and `detectors.py`. Ask:
   - Does the policy account for `bird_vy` (current velocity)?
   - Does it look at `next_pipe_dx` (horizontal distance to pipe)?
   - Does it have safety margins (gap_top + N, gap_bottom - N)?
   - Does it predict where the bird will be N ticks ahead rather than
     reacting to current position?
   - On the worst seed, what is the bird doing when it dies — hitting
     ceiling (flap too aggressive), floor (no flap), or pipe edge
     (timing off)?

4. **Optional: probe before editing.** If you're not sure your
   hypothesis is right, run a probe on the worst seed plus a few
   neighbors:

   ```bash
   python flappy_hs.py probe \
     --trial-name "probe_v1_<scope>" \
     --notes "<what you're checking>" \
     --seeds 103 200 201 202
   ```

5. **Edit `policy.py` (or `detectors.py`).** Apply minimal changes.
   Prefer adding a new branch or a velocity-aware predicted_y over
   rewriting the whole function.

6. **Run eval.**

   ```bash
   python flappy_hs.py eval \
     --trial-name "update_v{n}_<what_changed>" \
     --notes "<one-line rationale>" \
     --files policy.py
   ```

   The `--trial-name` must be a hypothesis label, e.g.
   `update_v3_velocity_aware`, `update_v4_safety_margin_15`.

7. **Check the no-regress gate.** Compare the new eval's `score_mean`
   against the previous best (visible in STATUS.md "Best score").
   - If new score_mean ≥ previous best: continue.
   - If new score_mean < previous best: REVERT your edits in
     `policy.py` / `detectors.py`. Append to `memory.md` under "Failed
     directions" with the reason. Do not record a second eval — the
     append-only history already shows the failed attempt.

8. **Auto-simplify on new best.** Run:

   ```bash
   python flappy_hs.py is_new_best
   ```

   If `yes` (exit 0): simplify `policy.py` while keeping behavior
   identical on every eval seed. Re-run `eval` with
   `--trial-name "simplify_v{n}_<what>"`. Confirm score is unchanged.

## Stop condition

Exit when `python flappy_hs.py is_new_best` has been checked AND, if it
said `yes`, a simplification pass has run with score preserved. Print
a one-line summary: what you changed, score_mean before → after,
whether you simplified.
