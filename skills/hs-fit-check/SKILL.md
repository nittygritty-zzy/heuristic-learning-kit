---
name: hs-fit-check
description: Run the 5-question litmus test on a candidate domain to decide whether Heuristic Learning is the right paradigm before scaffolding a project. Use when the user asks "is X a good HL target?", runs /hs-fit-check, or proposes a domain you're not sure fits.
---

# /hs-fit-check

A pre-flight check for whether a domain is well-suited to HL. Score the
five questions; ≥ 4 of 5 = scaffold and start iterating (run `/hs-new`).
2+ no = reshape the problem or accept that an NN belongs somewhere in
the loop.

## The five questions

Walk the user through each question. For each, ask them to answer
**yes** or **no** with one sentence of reasoning. Don't accept "maybe"
— push for a definitive answer.

1. **Fast trusted eval.** Can you write a regression test that takes
   < 1 minute to run and gives a scalar you trust?
   - Yes if the env is deterministic or low-variance enough that 1 minute
     of execution gives a tight enough CI to detect meaningful gains.
   - No if a single run is noisy or slow (e.g. real-world API calls,
     hour-long simulations).

2. **Decomposable policy.** Can you describe the desired policy in 3-5
   named modules without hand-waving?
   - Yes for "intent detection + response template + urgency modifier"
     or "gait CPG + residual MPC + balance feedback".
   - No for "the model just knows" or "it's emergent from training".

3. **Signal > noise.** Is per-eval variance smaller than the improvement
   you expect from one good edit?
   - Yes for deterministic envs (flappy: 0 variance) and most
     classification tasks (golden eval is deterministic).
   - No for high-variance gambling games at low sample sizes (poker even
     at 10k hands has SE ≥ a real skill gain). Mitigation: use the
     stochastic-game template's CI-aware gate and probe past `maybe`
     verdicts.

4. **Regression-stable contract.** Does the right answer have a stable
   ground truth that doesn't drift week-over-week?
   - Yes for chess rules, classification with curated labels,
     deterministic game scoring.
   - No for "what makes a good customer reply" (drifts with product
     changes), open-ended generative quality.

5. **Local failure mode.** If your policy is wrong, does the failure
   show up locally (within a few steps) or only after many actions?
   - Yes for one-shot tasks, short games, classification.
   - No for Montezuma-style long-horizon planning where a wrong choice
     at step 1 only manifests at step 86.

## Scoring

After all five answers, score and recommend:

- **5/5 yes**: Strong fit. Run `/hs-new <domain>` to scaffold.
- **4/5 yes**: Good fit. Note which one was "no" and what mitigation
  applies (e.g. "use stochastic-game template if #3 was no").
  Recommend `/hs-new`.
- **3/5 yes**: Marginal. Discuss with the user whether the problem can
  be reshaped (e.g. "could you eval against a smaller golden set?").
  Don't scaffold without a plan for the failing dimensions.
- **≤ 2/5 yes**: Poor fit. Don't scaffold. Recommend the hybrid pattern
  from the article: HL as System 1 (the bounded, fast-iterating layer)
  alongside an NN for the parts HL can't express (perception, open-ended
  generation, strategic equilibria).

## Worked examples (use as anchors)

| Domain | Score | Notes |
|---|---|---|
| Customer-support intent | 5/5 | aitl-hl example |
| Flappy bird | 5/5 | flappy example |
| Blackjack (S17 + double + split) | 4/5 | blackjack example; #3 was the limit, CI gate handles it |
| Pong | 5/5 | analogous to flappy |
| Tetris (lines cleared) | 4-5/5 | deterministic given seed; per-game variance moderate |
| Poker (heads-up NLHE) | 2/5 | variance + multi-agent equilibria |
| Montezuma's Revenge | 2/5 | long-horizon credit assignment (the article's boundary case) |
| ImageNet | 1/5 | perception needs learned features |

## Output

End with a clear yes/no/conditional recommendation and the next step
(`/hs-new <domain>` if recommended). If conditional, name the
specific question that's blocking and propose a mitigation.
