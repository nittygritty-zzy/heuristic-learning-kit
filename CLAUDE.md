# Heuristic Learning Kit

This is a Claude Code plugin providing scaffolding for **Heuristic Learning
(HL)** experiments per Weng 2026, *Learning Beyond Gradients*.

When a user opens this repo or has this plugin installed, they get three
slash commands: `/hs-new`, `/hs-fit-check`, `/hs-iterate`. Source those
skills via `skills/<name>/SKILL.md`.

## Repo layout

```
.
├── README.md                 # the install + pitch
├── CLAUDE.md                 # this file
├── LICENSE                   # MIT
├── .claude-plugin/
│   └── plugin.json           # Claude Code plugin manifest
├── skills/                   # plugin-provided skills
│   ├── hs-new/SKILL.md       # /hs-new — copy a template to a new project
│   ├── hs-fit-check/SKILL.md # /hs-fit-check — 5-question litmus test
│   └── hs-iterate/SKILL.md   # /hs-iterate — generic update step
├── templates/                # categorized by HS shape; /hs-new copies from here
│   ├── deterministic-game/   # (same content as examples/flappy)
│   ├── stochastic-game/      # (same content as examples/blackjack)
│   └── classification/       # (same content as examples/aitl)
├── examples/                 # categorized by named domain; read as references
│   ├── flappy/               # deterministic game (flappy bird)
│   ├── blackjack/            # stochastic game w/ double + split
│   └── aitl/                 # text classification + response
└── docs/
    ├── HS_PATTERN.md
    ├── ITERATION_GUIDE.md
    └── PAPER.md
```

## What an agent landing here should do

If the user wants to **start a new HL experiment**, invoke `/hs-new`.
That skill is the wizard.

If the user wants to **see a finished example**, point them at
`examples/<flappy|blackjack|aitl>/` — each is a complete project with
its own CLAUDE.md, multi-commit history, and documented memory.md.

If the user wants to **understand the pattern**, read
`docs/HS_PATTERN.md` (the seven components + invariants) and
`docs/ITERATION_GUIDE.md` (the maybe-probe-confirm flow for stochastic
domains).

## Invariants for agents working in this repo

1. **Templates and examples hold the same three projects.** Templates
   are categorized by shape (deterministic-game / stochastic-game /
   classification); examples by domain (flappy / blackjack / aitl).
   Keeping them in sync is a hard invariant — when a lesson is promoted
   into one, mirror it into the matching counterpart in the same commit.

2. **Both retain the optimized final policy and full iteration history.**
   trials.jsonl, memory.md, and STATUS.md are *load-bearing* — they
   show the new project's owner what a real iteration arc looks like,
   including failed directions and their lessons. Do not strip these.

3. **Do not modify templates/examples in response to "improve the policy"
   for a user task.** That's what `/hs-new` is for: create a new project,
   then iterate there. The shipped templates/examples are stable.

4. **The kit is itself a project** with its own git history. Plugin
   skills and templates/examples evolve over time; each change is a
   normal commit on this repo. Lessons from real PoCs *can* be promoted
   into templates if they're load-bearing — mirror them into the
   matching example in the same commit.

## When updating the kit

If a real experiment surfaces a lesson worth promoting to a template
or doc, add it. The kit's value compounds when the templates absorb
lessons from real PoCs. Don't promote anything that's not load-bearing.
