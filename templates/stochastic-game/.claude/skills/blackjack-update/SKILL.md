---
name: blackjack-update
description: Iterate the blackjack policy. Read STATUS.md + recent trials, edit policy.py / detectors.py, re-run eval, and ensure EV does not drop (using CI-aware regression gate). Trigger simplification automatically only on a *confident* new best. Use when the user runs /blackjack-update or asks to improve the blackjack policy.
---

# /blackjack-update

You are the maintenance step of a blackjack Heuristic System. Read
`CLAUDE.md` first for invariants. The most important difference from
the flappy skill: **EV signals are noisy.** A small EV gain may be
chance, not real. The driver enforces this via `is_new_best`'s
CI-overlap check — respect its three exit codes.

## Procedure

1. **Read state.** Run `cat STATUS.md` for the snapshot. Then look at
   the last 1–2 eval rows in `trials.jsonl` — note `ev`, `se`, per-seed
   EV breakdown. If one seed has much worse EV than the others, that's
   a target for the next fix.

2. **Read memory.** Open `memory.md` and read "Failed directions".
   Do not retry anything listed there.

3. **Form a hypothesis.** Look at `policy.py` and `detectors.py`. Ask:
   - Does the policy account for `dealer_upcard`? Optimal play depends
     heavily on it (hit 12-16 when dealer shows 2-6, stand otherwise).
   - Does it distinguish soft from hard totals? Soft hands can hit
     more aggressively because aces flex.
   - Is there a particular total range where the current policy is
     wrong? Probe to confirm.

4. **Optional: probe before editing.** If you're not sure your
   hypothesis is right, run a probe with extra hands on a few seeds:

   ```bash
   python blackjack_hs.py probe \
     --trial-name "probe_v1_<scope>" \
     --notes "<what you're checking>" \
     --seeds 100 200 300 \
     --n-hands 50000
   ```

   More hands per seed = tighter CI = sharper signal for the
   investigation.

5. **Edit `policy.py` (or `detectors.py`).** Apply minimal changes.
   Prefer adding one new branch over rewriting the whole function.

6. **Run eval.**

   ```bash
   python blackjack_hs.py eval \
     --trial-name "update_v{n}_<what_changed>" \
     --notes "<one-line rationale>" \
     --files policy.py
   ```

   The `--trial-name` is a hypothesis label, e.g.
   `update_v3_hit_until_17`, `update_v5_stand_12_on_dealer_low`.

7. **Check the regression gate.** Run:

   ```bash
   python blackjack_hs.py is_new_best
   ```

   - `yes` (exit 0): confident improvement. Proceed to step 8.
   - `maybe` (exit 2): higher EV but CI overlap. **Do NOT** declare a
     new best. Either: (a) accept the change as a minor refinement
     (no simplification triggered), or (b) re-eval with more hands by
     widening `n_hands` via a probe to see if the gain holds. If the
     re-eval still shows `maybe`, take it as a small improvement and
     move on — repeated maybe-improvements compound.
   - `no` (exit 1): EV did not exceed prior best. **REVERT** your
     edits. Append to `memory.md` under "Failed directions" with the
     reason. Do not record another eval.

8. **Auto-simplify only on `yes`.** When `is_new_best` confirms a
   real improvement, simplify `policy.py` while keeping behavior
   exactly the same on every eval seed, then re-run `eval` with
   `--trial-name "simplify_v{n}_<what>"`. The shipped `policy.py` is
   always the simplest version that holds the current confirmed best.

## Stop condition

Exit when:
- `is_new_best` has been checked
- if it said `yes`, simplification has run and `replay` shows EV
  unchanged within the noise floor (CI overlap with the unsimplified
  version is fine here — we're preserving behavior, not improving it)

Print a one-line summary: what changed, EV before → after, gate
verdict (yes/maybe/no), whether you simplified.
