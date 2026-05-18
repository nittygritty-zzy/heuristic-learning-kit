---
name: aitl-paraphrase
description: Generate paraphrase variants for adopted queries in the AITL-HL project to populate paraphrases.jsonl, then check policy robustness across paraphrases. Use when the user runs /aitl-paraphrase, asks to test policy robustness, or asks to expand the multi-seed check.
---

# /aitl-paraphrase

The Chinese HS definition constrains overfitting via "简化 + 回归 + 多 seed".
Simplification and regression are covered by `/aitl-simplify` and
`golden.jsonl`. This skill is the **多 seed** piece: it checks that the
policy returns the same answer for paraphrased versions of an adopted query.

Read `CLAUDE.md` first for invariants.

## Procedure

1. **Find candidate queries.** Read `golden.jsonl`. For each adopted query
   that does not already appear as `canonical_query` in `paraphrases.jsonl`,
   it's a candidate. Skip ones already present (the file is append-only).

2. **Generate 3 paraphrases per candidate.** You may use your own language
   capability — paraphrase generation is the **only** place an LLM appears
   in this system, and its output lands on disk for later replay, not in
   the inference path.

   Good paraphrases:
   - Keep the intent stable (don't accidentally paraphrase across intents).
   - Vary surface form: question/statement, formal/casual, short/long.
   - Avoid copying the canonical query with one word swapped — make them
     meaningfully different.

   Examples:
   - canonical: "how long for refund?"
   - paraphrases: "when will I get my refund?", "refund timing?",
     "how many days until I see the refund?"

3. **Append to `paraphrases.jsonl`.** One row per canonical query:

   ```json
   {"canonical_query": "...", "paraphrases": ["...", "...", "..."]}
   ```

   The file is append-only. If a `canonical_query` is already present,
   skip it; do not edit existing rows.

   Note: `.claude/settings.json` denies direct edits to this file. Use a
   shell append (`>>`) via Bash instead of the Edit tool.

4. **Run the check.**

   ```bash
   python aitl_hl.py paraphrase_check
   ```

   Every entry should show `OK`. Any `DIVERGE` means the policy is fragile
   to wording for that intent.

5. **On divergence, do not silently patch.** Report the divergence to the
   user. The right fix path is a separate `/aitl-update` run where the
   divergent paraphrase enters the normal maintenance flow (as a
   non-adopted trial), with all the safety that flow provides.

6. **Close the loop — record the eval.** Before exiting:

   ```bash
   python aitl_hl.py record --skill aitl-paraphrase \
     --trial-name "paraphrase_v{n}_<scope>" \
     --notes "<rows added; OK/DIVERGE counts>" \
     --files paraphrases.jsonl
   ```

   Pick a hypothesis-label `--trial-name`, e.g.
   `paraphrase_v1_seed_all_goldens` or
   `paraphrase_v2_extend_refund_set`. This appends a `kind: "eval"` row
   to `trials.jsonl` (with `score_mean` and the paraphrase pass count)
   and regenerates `summary.csv`. `files` lists `paraphrases.jsonl` even
   though you only appended — `record` notes your action, not the file
   content change.

## Stop condition

Exit when every adopted query has at least one paraphrase row,
`paraphrase_check` results are printed, AND the maintenance row is
recorded. Print a one-line summary: rows added, OK vs DIVERGE counts.
