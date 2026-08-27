---
name: hs-iterate
description: Generic iteration step for any HS project — read STATUS, read memory, edit policy.py and/or detectors.py, run eval, check is_new_best, optionally simplify. Use when the user runs /hs-iterate, asks to improve the policy, or asks to iterate the current HS project.
---

# /hs-iterate

The domain-agnostic version of the project-specific update skills
(`/flappy-update`, `/blackjack-update`, etc). Use this when working in a
project scaffolded from `/hs-new`, before the user has renamed the
shipped iterate skill to their domain.

Read `CLAUDE.md` in the current project first — it lists the seven HS
components and the invariants for this domain. The driver filename is
the project's `<domain>_hs.py`.

## Procedure

1. **Read state.** Run:
   ```bash
   cat STATUS.md
   ```
   Then look at the last 1-2 eval rows in `trials.jsonl` for per-seed /
   per-case detail. Identify which seed or case has the worst score —
   that's your target.

2. **Read memory.** Open `memory.md`, especially "Failed directions
   (do not retry)". Do not repeat anything listed there.

3. **Form a hypothesis.** Look at `policy.py` and `detectors.py`. Ask:
   - Is the failure a *perception* problem (the wrong intent /
     classification / state detected)? → edit `detectors.py`.
   - Is the failure a *control* problem (right state, wrong action)?
     → edit `policy.py`.
   - Does the env have a forward simulation model you can derive
     constraints from? If yes, prefer first-principles math over
     behavioral experiments (see `docs/ITERATION_GUIDE.md`).

4. **Optional: probe first.** If unsure, run the driver's `probe`
   subcommand on synthetic inputs to verify the hypothesis without
   committing to a policy edit. See `<domain>_hs.py probe --help`.

5. **Apply minimal edits.** Prefer one new branch or a broadened
   pattern over rewriting whole functions.

6. **Run eval.** Identify the driver filename (look for `*_hs.py` in
   the project root), then:
   ```bash
   python <driver>.py eval \
     --trial-name "update_v{n}_<what_changed>" \
     --notes "<one-line rationale>" \
     --files policy.py detectors.py
   ```
   Pick `<trial_name>` as a hypothesis label — it's the agent's primary
   key into its own memory next round.

7. **Check the regression gate.**
   ```bash
   python <driver>.py is_new_best
   # 0 yes · 1 regression · 2 CI-overlap maybe · 3 unchanged (accept:
   # a compression pass preserves score by design)
   ```
   Three outcomes:
   - `yes` (exit 0): confident improvement. Continue to step 8.
   - `maybe` (exit 2): higher score but variance overlap. Either accept
     the small gain or run a longer probe (`--n-hands` for stochastic
     or `--max-ticks` for game templates). See
     `docs/ITERATION_GUIDE.md#probing-past-maybe`.
   - `no` (exit 1): score did not exceed prior best. **Revert.**
     Append the reason to `memory.md` under "Failed directions".

8. **Auto-simplify on confirmed new best.** When `is_new_best` returns
   `yes`, simplify `policy.py` while keeping behavior identical on the
   regression set. Re-eval with `--trial-name "simplify_v{n}_<what>"`
   and confirm the score is unchanged.

## Stop condition

Exit when:
- the eval has been recorded,
- `is_new_best` has been checked,
- if `yes`, a simplification pass has been attempted.

Print a one-line summary: what changed, score before → after, gate
verdict.

## When the project has a domain-specific update skill

If `.claude/skills/<domain>-update/` exists, prefer that — it has
domain-tuned hypotheses, failure-mode hints, and reference EVs. This
generic `/hs-iterate` is the fallback for projects that haven't been
specialized yet.
