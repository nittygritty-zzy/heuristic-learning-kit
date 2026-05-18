# AITL-HL PoC

A working proof-of-concept of **Heuristic Learning (HL)** from Weng 2026
(《Learning Beyond Gradients》), rebuilt as a Claude Code project.

The maintained artifact is **code**, not weights. The maintainer is
**Claude Code**, not a human. Customer-support intent classification is
the worked example.

See `CLAUDE.md` for the seven HS components and their invariants.

## Quickstart

```bash
# 1. Serve a few queries and annotate (you act as the "human agent" in AITL)
python aitl_hl.py ask
python aitl_hl.py ask
python aitl_hl.py ask

# 2. See what the coding agent will see
python aitl_hl.py report
cat STATUS.md  # human-readable snapshot, regenerated automatically

# 3. From inside Claude Code in this directory:
#       /aitl-update
#    Claude reads trials.jsonl + memory.md, edits policy.py / detectors.py,
#    iterates until `python aitl_hl.py report` is green.

# 4. Verify regressions still hold
python aitl_hl.py replay

# 5. Generate paraphrase robustness tests (periodically)
#       /aitl-paraphrase

# 6. After 5 accepted updates, run the mandatory compression pass
#       /aitl-simplify
```

## What's HL about this

- **Inference path: zero LLM calls.** `policy.py` is pure Python rules.
- **Memory is explicit, deletable, refactorable.** `memory.md` + git, not
  weights.
- **Regression as a hard contract.** `golden.jsonl` is append-only. Any
  policy edit that breaks a golden is reverted.
- **Catastrophic forgetting is a git operation.** Old capabilities live as
  goldens, not as parameters. Removing one is a deliberate, auditable act.

## What's Claude-Code-native about this

- The update step is a **project-scoped skill** (`/aitl-update`), not an
  SDK call. Claude reads files itself, edits in place, runs `report`,
  iterates inside one invocation.
- `CLAUDE.md` is loaded automatically — invariants don't need re-pasting
  into every prompt.
- `.claude/settings.json` denies edits to the append-only JSONL files at
  the tool layer. Defense in depth against an over-eager agent.

## Layout

```
.
├── README.md
├── CLAUDE.md
├── aitl_hl.py        driver: ask · report · replay · paraphrase_check
├── policy.py         (HS-1) programmatic policy
├── detectors.py      (HS-2) state representation
├── trials.jsonl      (HS-4) experiment records (append-only)
├── summary.csv       (HS-4) flat view of trials.jsonl (derived)
├── STATUS.md         (HS-4) human-readable snapshot of system state (derived)
├── golden.jsonl      (HS-5) regression tests (append-only)
├── paraphrases.jsonl (HS-5b) multi-seed robustness set (append-only)
├── memory.md         (HS-6) failed directions, compression history
└── .claude/
    ├── settings.json     permission allowlist + append-only deny
    └── skills/
        ├── aitl-update/SKILL.md     (HS-7a) update mechanism
        ├── aitl-simplify/SKILL.md   (HS-7b) mandatory compression pass
        └── aitl-paraphrase/SKILL.md (HS-7c) generate paraphrase tests
```
