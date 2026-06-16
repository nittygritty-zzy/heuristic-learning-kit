---
name: hs-flywheel
description: Run an HS project's iteration loop autonomously — repeatedly apply /hs-iterate until a machine-evaluable stop predicate fires, with a two-level gate and anti-gaming safeguards. Use when the user runs /hs-flywheel, asks to "iterate until it converges", "run overnight", or wants the policy improved without supervising each step.
---

# /hs-flywheel

The autonomous wrapper around `/hs-iterate`. Where `/hs-iterate` is one
human-triggered step, `/hs-flywheel` runs the loop itself: edit → eval →
gate → {accept+simplify | probe | revert} → repeat, **deciding on its own
when to keep going and when to stop.**

This is the hardened version of the minimal "edit / run / keep-or-revert /
LOOP FOREVER" pattern (cf. `karpathy/autoresearch`). It adds the three
things a naive loop lacks, which are exactly what make a flywheel safe to
leave unattended:

1. **A machine-evaluable stop predicate** (a naive loop never stops).
2. **A two-level gate** — cheap regression check before expensive eval.
3. **Anti-gaming safeguards** — the loop cannot edit its own scorer.

## Preconditions (check before the first tick)

Do not start the loop unless all hold — an autonomous loop with a soft
gate crowns noise as progress:

- The project passed `/hs-fit-check` (≥ 4/5), in particular **#1 fast
  trusted scalar eval** and **#3 signal > noise**. Without a trusted
  scalar gate, `is_new_best` cannot decide transitions and the loop
  deadlocks on human judgment — stop and tell the user.
- `git status` is clean (so reverts are well-defined).
- The driver exposes `eval` and `is_new_best` (look for `*_hs.py`).

Record the loop's baseline: run `python <driver>.py eval --trial-name
"flywheel_v0_baseline" --notes "flywheel start" --files policy.py
detectors.py` once, then `is_new_best` to fix the starting best.

## Anti-gaming lock (set up once, verify every tick)

The loop may **only** edit `policy.py` and `detectors.py`. Everything that
defines "better" is off-limits: the driver `<domain>_hs.py`, the eval
harness, `golden.jsonl` / `eval_seeds.jsonl`, `trials.jsonl`, `STATUS.md`,
`summary.csv`. These are already denied at the tool layer in the project's
`.claude/settings.json`; the flywheel adds a defense-in-depth check.

- At loop start, record `git rev-parse HEAD:<driver>.py` (or a content
  hash) of the driver, eval harness, and regression files.
- **At the top of every tick, re-verify those hashes are unchanged.** If
  any changed, halt immediately and report — the gate has been corrupted
  and no verdict after that point is trustworthy.

## The loop

Maintain three counters across ticks: `consecutive_no` (reverts with no
accepted best), `accepted` (confirmed new-bests), `tick`.

```
LOOP until a stop predicate fires (see below):
  0. Verify the anti-gaming hashes (above). Halt if changed.
  1. Run /hs-iterate to form ONE hypothesis and edit policy.py / detectors.py.
  2. LEVEL-1 GATE (cheap): run the regression set only.
       - deterministic env: `python <driver>.py replay`  → must be all-green
       - if it breaks a golden → revert immediately, log to memory.md,
         do NOT spend a full eval. consecutive_no += 1. continue.
       - NOTE: this level only saves compute when the regression set is
         *separate from and smaller than* the full eval set (e.g. the
         classification template's `golden.jsonl` vs a larger eval). When
         `replay` and `eval` run the **same** cases (e.g. flappy, where both
         use `eval_seeds.jsonl`), L1 and L2 collapse into one — run `eval`
         directly and skip the redundant `replay`.
  3. LEVEL-2 GATE (expensive): `python <driver>.py eval --trial-name
       "flywheel_v{tick}_<what>" --files policy.py detectors.py`
       then `python <driver>.py is_new_best`:
       - yes   → accept. accepted += 1; consecutive_no = 0.
                 Run the simplification pass (keep behavior identical),
                 re-eval as "simplify_v{tick}_<what>".
       - maybe → probe at 5–10× sample size (see ITERATION_GUIDE).
                 confirmed → treat as yes. unconfirmed → treat as no.
       - no    → revert policy.py/detectors.py to best. consecutive_no += 1.
                 Append the **Lesson** to memory.md "Failed directions".
  4. tick += 1.
```

`/hs-iterate` already reads `STATUS.md` and `memory.md` at the top of each
step, so every tick's input is the accumulated output of the prior ticks —
that compounding is what makes this a flywheel and not a `while` loop. The
**Lesson line** on each revert is load-bearing: without it the loop retries
dead directions and spins without progressing (livelock).

## Stop predicates (any one fires → halt)

A naive loop runs forever; this one self-terminates. Halt and report when:

1. **Search is dry.** `consecutive_no >= K` (default **K = 3**) — three
   straight ticks produced no accepted best. This is the article's
   "2–3 failures per breakthrough" turned into a stop rule.
2. **Ceiling saturated.** Eval hit its max possible score on every seed /
   case. Run one ceiling-search probe (longer episodes / more seeds per
   `ITERATION_GUIDE.md#when-to-stop-iterating`); if the probe is also
   maxed, stop.
3. **Math says optimal.** The policy's safety/optimality condition is a
   closed-form inequality and the current constants sit in its interior
   (see the flappy 2-px-window example in `ITERATION_GUIDE.md`). Confirm
   with one stress probe; ship.
4. **Budget reached.** A user-supplied max-tick / time / token budget is
   exhausted.
5. **Livelock backstop.** `consecutive_no >= 5` with reverts every tick →
   force-restore the best snapshot and stop. (Borrowed from TDAD's
   5-consecutive-revert mandatory restore.) Escalate to the user.

On halt, print: ticks run, accepted new-bests, baseline → final score,
which stop predicate fired, and the path to the new best commit.

## Running it autonomously

`/hs-flywheel` loops **in-session** by default — keep iterating until a stop
predicate fires, then report. Because HS evals are fast (<1 min by the
fit-check contract), in-session looping needs no cross-turn scheduling.

For overnight or cross-session runs, wrap it with `/loop` (dynamic mode):

```
/loop run /hs-flywheel; stop when a stop predicate fires
```

- No interval → dynamic mode → each arc ends by calling `ScheduleWakeup`
  with a fallback delay; **omitting that call is how the loop terminates**,
  so the agent stops scheduling once a stop predicate fires.
- If the driver's `eval` is run as a background job, arm a `Monitor`
  (`persistent: true`) on the run log instead of polling — its completion
  wakes the loop immediately and the `ScheduleWakeup` delay becomes a
  fallback heartbeat (lean 1200–1800s).

## What this leaves behind

The same artifacts every HS iteration produces — `trials.jsonl` rows
(`flywheel_v*`, `simplify_v*`), `memory.md` Failed-directions entries with
Lessons, and a regenerated `STATUS.md` — plus a final one-line summary. The
full arc is replayable from git + `trials.jsonl`, including the directions
the loop tried and reverted.
