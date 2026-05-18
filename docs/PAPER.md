# The Paper

This kit implements the framework from:

> **Weng, Jiayi (2026). *Learning Beyond Gradients*.**
> Published article: https://trinkle23897.github.io/learning-beyond-gradients/
> Artifact repository: https://github.com/Trinkle23897/learning-beyond-gradients

The article is bilingual (Chinese + English). Both are full-fidelity;
neither is a translation. Read whichever you prefer.

## The thesis in one line

> Coding agents have collapsed the maintenance cost of hand-written
> heuristic systems enough that "programs as policies" is now a viable
> learning paradigm — succeeding pretraining, RLHF, and large-scale
> RL/RLVR for online and continual learning.

## What HL is (per the article)

A **Heuristic System (HS)** has seven components: programmatic policy,
state representation, feedback channels, experiment records, regression
tests, memory, and an update mechanism executed by a coding agent.
**Updates happen via code edits, not gradient descent.** The article's
Chinese term: **Heuristic Learning (HL)**.

See `HS_PATTERN.md` for how the kit instantiates these seven components.

## The empirical anomaly that motivated the article

Weng ran Codex (gpt-5.4) against a series of RL benchmarks with **no
neural network**, only programmatic policies. Results:

- **Atari Breakout**: 387 → 507 → 839 → **864** (theoretical max)
- **MuJoCo Ant**: **6146** via CPG gait + residual MPC
- **MuJoCo HalfCheetah**: 11836.7 mean over 5 seeds
- **VizDoom D3 Battle**: mean 557 / min 440 across 10 seeds, cv2+NumPy
  perception only
- **Atari57**: 342 unattended runs (57 games × 2 obs modes × 3 repeats);
  median HNS ~0.83 with best obs mode per game, competitive with PPO

The Breakout iteration arc (387 → 864) is the article's flagship
worked example; it's reproducible from the artifact repo.

## The boundary case

**Montezuma's Revenge** is the article's "this needs more than
heuristics" example. One unattended run reached 400 points but the
"policy" was an 86-step open-loop macro sequence, not a closed-loop
controller. The article uses this to point at the next layer: composable
macro-actions, recoverable search state, long-term memory. Those are
outside this kit's scope.

## The Atari57 prompt template (the canonical HS spec)

The article's most important reusable artifact, beyond the prose, is the
prompt template that drove the 342-run Atari57 batch:

> https://github.com/Trinkle23897/learning-beyond-gradients/blob/main/atari/atari57/atari57_prompt_template.txt

If you're scaffolding a new HS and want the *canonical* output-files
checklist (policy.py, trials.jsonl, summary.csv, sample_efficiency.png,
README.md) and stop rules (FRAME_BUDGET, simplify-on-best, etc.),
that's the document.

## The hybrid stance

The article is clear that HL doesn't replace neural networks for
perception (ImageNet) or open-ended generation. Quote:

> Heuristic Learning cannot do everything neural networks can do. It is
> bounded by what code can express, especially in complex perception
> and long-horizon generalization.

Proposed synthesis: HL as System-1 (fast, fresh, inspectable,
regression-tested) alongside an NN at perception and open-ended layers.
HL filters and regression-tests online data; the NN gets periodically
updated on that curated stream.

This kit's three example domains all sit squarely on the HL side. For
hybrid stacks, add an NN-driven detector module as needed; the kit's
scaffold doesn't preclude it.

## Citation

```bibtex
@misc{weng2026learning_beyond_gradients,
  title = {Learning Beyond Gradients},
  author = {Weng, Jiayi},
  year = {2026},
  month = may,
  howpublished = {\url{https://trinkle23897.github.io/learning-beyond-gradients/}},
  note = {Blog post}
}
```
