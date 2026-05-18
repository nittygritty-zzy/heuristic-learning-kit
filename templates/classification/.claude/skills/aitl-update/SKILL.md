---
name: aitl-update
description: Rewrite policy.py and detectors.py from recent non-adopted trials in the AITL-HL project. All golden regressions and paraphrase checks must keep passing. Record abandoned directions in memory.md. Use when the user runs /aitl-update, asks to update the AITL policy, or asks to fix non-adopted trials.
---

# /aitl-update

You are the maintenance step of an AITL Heuristic System. Your job is to
edit `policy.py` and/or `detectors.py` so recent non-adopted trials get
the answer the human agent wrote — without breaking any golden case.

Read `CLAUDE.md` first for the system-wide invariants. The seven HS
components are listed there.

## Procedure

1. **Look at the feedback buffer.**

   ```bash
   python aitl_hl.py report
   ```

   This shows: non-adopted trials, regression status, paraphrase
   consistency, escalation rate. Treat this as your primary input — not
   the trial file directly.

2. **Read prior memory.** Open `memory.md` and read "Failed directions".
   Do not retry anything listed there.

3. **Classify each non-adopted trial.** For every row with `adopted=false`,
   decide which component is at fault:
   - **`detectors.py`** if the intent was misclassified. (Example: query
     "I want my money back" should hit `refund`, but `intent()` returned
     `unknown`. Fix: broaden the regex.)
   - **`policy.py`** if the intent was right but the response was wrong or
     missing a modifier. (Example: urgent queries need a different opener.)

   **Optional: probe before editing.** If you're not sure your hypothesis
   is right (e.g. "is the regex too narrow, or is the response wrong?"),
   run a probe first:

   ```bash
   python aitl_hl.py probe \
     --trial-name "intent_coverage_v1_<scope>" \
     --notes "<what you're checking>" \
     --queries "candidate query 1" "candidate query 2" "..."
   ```

   This shows you exactly what `respond()` and `intent()` return for each
   query, costs you only a row in `trials.jsonl`, and saves you a bad
   edit + revert cycle. Skip it when the failure mode is obvious.

4. **Apply minimal edits.** Prefer adding one branch or broadening a regex
   over rewriting whole functions. If multiple fixes share a real pattern,
   express the pattern — don't enumerate literals. Quoting CLAUDE.md
   invariant 6: a fix that only works on the literal query string is a bug.

5. **Run the report again.**

   ```bash
   python aitl_hl.py report
   ```

   Required final state:
   - `regression:  N/N passing`
   - `paraphrase:  N/N consistent` (if any exist)
   - 0 escalations on previously adopted queries

6. **On regression, revise and rerun.** Iterate until clean. If you
   conclude a fix is impossible without breaking goldens, do not ship a
   half-edit: revert your changes, then append to `memory.md` under
   "Failed directions" with a short note ("query X cannot be served while
   golden Y stands — they disagree on the same intent. Considered: …").

7. **Never edit** `trials.jsonl`, `golden.jsonl`, or `paraphrases.jsonl`.
   The project `.claude/settings.json` blocks these edits at the tool
   layer; if you hit that denial, stop and rethink — you've taken a wrong
   turn.

8. **Close the loop — record the eval.** Before exiting, call:

   ```bash
   python aitl_hl.py record --skill aitl-update \
     --trial-name "<hypothesis label>" \
     --notes "<one-line rationale>" \
     --files <each file you edited>
   ```

   Pick `--trial-name` as a hypothesis label following the article's
   convention (e.g. `tunnel0_v1`, `ant_mpc_residual_warm02_eval5`). For
   our domain: `update_v{n}_<what_changed>`, e.g.
   `update_v3_broaden_return_regex`. The name must be greppable next
   round — it is the agent's primary key into its own memory.

   This appends a `kind: "eval"` row to `trials.jsonl` (with
   `score_mean = regression_pass / regression_total`) and regenerates
   `summary.csv`. Without this step, your edit lives only in git — the
   article's loop requires writing results back to trials.

9. **Auto-simplify on new best_score.** Run:

   ```bash
   python aitl_hl.py is_new_best
   ```

   If it prints `yes` (exit 0), the new policy beat every prior eval.
   The Atari57 prompt mandates: *"每当你刷新当前 run 的 best_score 时…
   先进入一次「代码简化阶段」"*. Immediately invoke `/aitl-simplify`
   and let it run before you exit. The shipped `policy.py` must be the
   simplest version that holds the new best.

   If `is_new_best` prints `no` (exit 1), skip simplification — you
   only matched a prior peak, not refreshed it.

## Stop condition

Exit when:
- `python aitl_hl.py report` shows all green
- the eval row is recorded
- if a new best was reached, `/aitl-simplify` has run and left
  everything still green

Print a one-line summary of what changed, the final pass counts, and
whether you triggered simplification.
