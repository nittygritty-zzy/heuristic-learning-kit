# Heuristic Learning Kit

> Build self-maintaining policies as code, iterated by Claude Code.

A Claude Code plugin and template set for **Heuristic Learning (HL)** — the
paradigm proposed in [*Learning Beyond Gradients*](https://trinkle23897.github.io/learning-beyond-gradients/)
by Jiayi Weng. HL treats hand-written heuristic systems as the unit of
learning, with a coding agent (Claude Code) as the maintainer.

This kit ships:

- **Three project templates** — categorized by HS *shape* (deterministic-game,
  stochastic-game, classification). Each is a complete working project
  with optimized policy + full iteration history. `/hs-new` copies one
  of these as your starting point.
- **Three named examples** — the same three projects, but categorized by
  *domain* (Flappy Bird, Blackjack, customer-support AITL). Read end-to-
  end as references.
- **Three skills** — `/hs-new`, `/hs-fit-check`, `/hs-iterate` — to
  bootstrap and maintain a new experiment from inside Claude Code.

## Install

```bash
claude plugin install nittygritty-zzy/heuristic-learning-kit
```

After install, three slash commands are available in any Claude Code session:

| Command          | What it does                                                    |
|------------------|-----------------------------------------------------------------|
| `/hs-fit-check`  | Run the 5-question litmus test on a candidate domain.           |
| `/hs-new`        | Scaffold a new HS project from one of the three templates.      |
| `/hs-iterate`    | Generic update step (read STATUS, edit policy, eval, record).   |

## Quickstart

```text
> /hs-fit-check tetris
... wizard asks 5 questions, scores the domain

> /hs-new tetris
... wizard asks deterministic vs stochastic, copies template,
... renames files, runs git init

> cd ~/workspace/tetris-hs-poc
> # implement env.py for tetris physics
> python env_hs.py eval --trial-name baseline_v0 --notes "naive baseline" --files policy.py
> /hs-iterate
... Claude reads STATUS, edits policy, re-evals, records
```

## What's a Heuristic System?

Per Weng 2026, an HS has seven components, each as a real file:

| Component | Role |
|---|---|
| 程序策略 (programmatic policy) | `policy.py` — pure-stdlib rules |
| 状态表示 (state representation) | `detectors.py` |
| 反馈入口 (feedback channels) | driver: `ask`, `eval`, `probe`, `report` |
| 实验记录 (experiment records) | `trials.jsonl` + `summary.csv` (derived) |
| 回放/测试 (regression set) | `golden.jsonl` or `eval_seeds.jsonl` |
| memory | `memory.md` + git log |
| 更新机制 (update mechanism) | `/hs-iterate` skill or domain-specific `/x-update` |

The driver also produces a `STATUS.md` that's regenerated on every trial
append — the continual-system analog of the article's per-run README.

Append-only history is enforced at the Claude Code tool layer via
`.claude/settings.json` `deny` rules. The agent literally cannot edit
`trials.jsonl`, `golden.jsonl`, `summary.csv`, or `STATUS.md`.

## Templates vs. examples (same content, different framing)

Both directories hold the same three projects, organized for two
different discovery experiences:

- **`templates/<shape>/`** — picked by *what kind of HS you're building*.
  When you're scaffolding Tetris, `templates/deterministic-game/` is
  the natural choice without knowing what "flappy" is.
- **`examples/<name>/`** — picked by *the specific worked domain*. Read
  end-to-end to absorb the pattern in concrete terms.

`/hs-new` consumes `templates/`. Each project retains its optimized
final policy and full iteration history — `trials.jsonl`, `memory.md`
with documented failed directions, the lessons that survived.

| Shape | Example | Final | Highlights |
|---|---|---|---|
| `templates/deterministic-game/` ↔ `examples/flappy/` | flappy bird | 0 → 76 (eval ceiling); 15,384 pipes/seed at 1M-tick stress, zero deaths | math-derived constant, rebound geometry |
| `templates/stochastic-game/` ↔ `examples/blackjack/` | blackjack S17 + double + split | -0.16 → -0.008 (textbook ceiling) | CI-aware regression gate, probing past "maybe" |
| `templates/classification/` ↔ `examples/aitl/` | customer-support AITL | scaffold + first iterations | append-only goldens, paraphrase robustness |

## Domain fit

HL is best for **verifiable, decomposable, low-noise, short-horizon,
regression-testable** domains. Run `/hs-fit-check` before scaffolding.
See `docs/HS_PATTERN.md` for the full taxonomy. Briefly:

- ✓ Customer support intent, deterministic games, low-variance games
- ✗ Open-ended generation, raw-pixel perception, long-horizon credit
  assignment, adversarial equilibria (poker)

In hybrid systems, HL is typically the System-1 layer alongside an NN
that handles perception or open-ended generation. The kit's templates
all assume pure-stdlib policies; for hybrids, add a NN-driven detector
module separately.

## Article

The pattern this kit implements is from:

> Weng, Jiayi (2026). *Learning Beyond Gradients*.
> https://trinkle23897.github.io/learning-beyond-gradients/

The article includes Atari Breakout (864/864), MuJoCo Ant (6146),
HalfCheetah (11836), VizDoom CV, Atari57 batch, and Montezuma as a
boundary case where reactive heuristics aren't enough. The
[Atari57 prompt template](https://github.com/Trinkle23897/learning-beyond-gradients/blob/main/atari/atari57/atari57_prompt_template.txt)
is the canonical codified HS spec.

## License

MIT. See [LICENSE](LICENSE).
