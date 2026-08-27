# The HS Pattern

A **Heuristic System (HS)** per Weng 2026 is more than a `policy.py`. It
has seven components, each as a real, inspectable artifact. This document
extracts the pattern from the three working examples in `examples/` (and
templates in `templates/`).

## The seven components

| Component (Chinese) | English | Concrete file | What it does |
|---|---|---|---|
| 程序策略 | Programmatic policy | `policy.py` | Pure-Python rules. `act(obs) -> action`. |
| 状态表示 | State representation | `detectors.py` + `env.make_obs` | Derived facts the policy needs. |
| 反馈入口 | Feedback channels | `<env>_hs.py` (driver) | `eval`, `probe`, `report`, `replay`, `record`. |
| 实验记录 | Experiment records | `trials.jsonl` + `summary.csv` (derived) | Append-only log of every eval and probe. |
| 回放 / 测试 | Regression set | `golden.jsonl` or `eval_seeds.jsonl` | The contract every edit must preserve. |
| memory | Memory | `memory.md` + git log | Design rationale, failed directions, lessons. |
| 更新机制 | Update mechanism | `.claude/skills/<domain>-update/SKILL.md` | The Claude Code skill that drives iteration. |

The driver also produces `STATUS.md`, the continual-system analog of the
article's per-run README — auto-regenerated on every trial append.

## The seven invariants

Every HS project's `CLAUDE.md` enumerates these as hard rules:

1. **Pure-Python policy.** `policy.py` and `detectors.py` use stdlib
   only. No network, no LLM, no third-party deps at inference time.

2. **Append-only history.** `trials.jsonl`, `golden.jsonl` /
   `eval_seeds.jsonl`, `paraphrases.jsonl` are append-only.
   `summary.csv` and `STATUS.md` are *derived* — regenerated on every
   trial append, never hand-edited. The project's `.claude/settings.json`
   denies Edit/Write on all of these at the tool layer.

3. **All-green regression gate.** Every edit ends with the driver's
   `eval` or `replay` showing all goldens pass (deterministic envs) or
   `is_new_best` returning `yes` / `maybe` with explicit confirmation
   (stochastic envs). `unchanged` (exit 3) is also an accept: it is the
   expected verdict for the mandatory compression pass of invariant #5.

4. **Failed directions get written down.** Abandoned approaches go
   into `memory.md` under "Failed directions" with the reason. The next
   round reads them first and does not retry.

5. **Mandatory compression.** After every accepted new-best, run a
   simplification pass: rewrite the policy more concisely while keeping
   behavior identical on the regression set. The article calls this
   out as the difference between an HS and a "ball of mud" rules pile.

6. **Generalize, don't memorize.** A fix that only works on one
   specific eval input is overfitting. Express the *pattern*, not the
   literal.

7. **Close the loop with a recorded trial.** Every maintenance step
   ends by calling the driver's eval subcommand to record a
   `kind: "eval"` row. The edit lives in git; the eval row records what
   the new policy *did*.

## Append-only enforced at the tool layer

This is the kit's main contribution beyond the article. Each project's
`.claude/settings.json` includes deny rules like:

```json
"deny": [
  "Edit(./trials.jsonl)",
  "Edit(./golden.jsonl)",
  "Edit(./summary.csv)",
  "Edit(./STATUS.md)",
  "Write(./trials.jsonl)",
  ...
]
```

This means even if Claude forgets the CLAUDE.md invariant, the harness
blocks the edit. Defense in depth.

## Trial schema

Every row in `trials.jsonl` has at minimum:

- `timestamp` — ISO datetime
- `kind` — one of `"ask"` (single human-served case), `"eval"` (full
  regression run), `"probe"` (exploratory inference, no score refresh)
- `trial_name` — hypothesis label (e.g. `update_v3_broaden_return_regex`,
  `simplify_v1_collapse_response_dict`, `probe_v2_unseen_seeds`)
- `inferences` — count of policy calls during this trial
- `notes` — one-line rationale or status

Eval rows add `score_mean` / `regression_pass` / `regression_total`.
Probe rows have no score (they don't refresh `is_new_best`). Ask rows
have query/response/adopted/fix for human-in-the-loop classification.

## Naming conventions

Trial names follow the article's pattern: a hypothesis label that
encodes the manipulated variable, version-numbered for chronology.

- ✓ `update_v3_broaden_return_regex` — version + what changed
- ✓ `tunnel0_v1` (from the article's Breakout case) — parameter +
  value + version
- ✓ `probe_v2_unseen_seeds_for_v8_check` — kind + version + scope
- ✗ `trial_2026_05_17` — timestamps don't tell you what was tested
- ✗ `try1` — version without semantic content

The agent uses trial names as the primary key into its own memory.
Greppable names let next-round iteration find prior experiments.

## What makes this a "system", not just a codebase

Single-rule scripts aren't HSs. The article is explicit: rules,
feedback, history, and the next update path must all *connect*. In this
kit's terms, the connection looks like:

```
human iteration trigger
        ↓
/<domain>-update or /hs-iterate skill
        ↓
reads STATUS.md (← derived from trials.jsonl)
        ↓
reads memory.md (← updated by prior maintenance)
        ↓
edits policy.py / detectors.py
        ↓
runs driver.eval
        ↓
driver appends to trials.jsonl
        ↓
driver regenerates summary.csv + STATUS.md
        ↓
driver.is_new_best gates the outcome
        ↓
on yes: simplification triggered
on maybe: probe past it
on no: revert; append to memory.md
```

This is the closed loop the article diagrams. The kit provides the
scaffolding for that loop in three concrete domain shapes.
