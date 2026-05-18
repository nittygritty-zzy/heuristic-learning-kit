---
name: aitl-simplify
description: Compress policy.py and detectors.py in the AITL-HL project without changing behavior on golden cases or paraphrase checks. Required maintenance every 5 accepted /aitl-update runs. Use when the user runs /aitl-simplify, asks to refactor the policy, or asks to reduce rule sprawl.
---

# /aitl-simplify

Compression is required maintenance. Quoting the article:

> An HS that only grows and never compresses will eventually become a big
> ball of mud.

Read `CLAUDE.md` first for invariants.

## Procedure

1. **Establish a green baseline.** Run:

   ```bash
   python aitl_hl.py report
   ```

   If it is not all green, **stop** and run `/aitl-update` first.
   Simplification on top of broken behavior just hides the bug.

2. **Read** `policy.py` and `detectors.py` and look for compression
   opportunities:
   - **Dead branches** — no trial in `trials.jsonl` has ever exercised
     them, and no golden depends on them.
   - **Duplicated regex patterns** — same alternation copy-pasted across
     detectors.
   - **Multiple `if` arms** mapping to the same response — collapse via
     a dict.
   - **Long if-chains** that could be a dict lookup.
   - **Repeated string literals** — promote to module constants.

3. **Refactor.** Behavior must remain *identical* on every golden case and
   every paraphrase case. This is non-negotiable.

4. **Verify.**

   ```bash
   python aitl_hl.py report
   ```

   Required:
   - `regression:  N/N passing` (same N as baseline)
   - `paraphrase:  N/N consistent` (same N as baseline)

5. **Revert on any regression.** No exceptions. A simplification that
   breaks behavior is a bug, not a simplification.

6. **Record rationale.** Append to `memory.md` under "Compression history":
   date, files touched, line-count delta, one sentence describing what was
   merged or removed.

7. **Close the loop — record the eval.** Before exiting:

   ```bash
   python aitl_hl.py record --skill aitl-simplify \
     --trial-name "simplify_v{n}_<what_was_simplified>" \
     --notes "<line-count delta and what was simplified>" \
     --files <each file you edited>
   ```

   Pick a hypothesis-label `--trial-name`, e.g.
   `simplify_v1_collapse_response_dict` or
   `simplify_v2_merge_return_regex`. Score should match the pre-simplify
   baseline exactly — that is the invariant a simplification preserves.

## Stop condition

Exit when the refactor passes, `memory.md` is updated, AND the eval
row is recorded. Print a one-line summary of the line-count delta and
what was simplified.
