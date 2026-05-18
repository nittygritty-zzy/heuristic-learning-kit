---
name: hs-new
description: Scaffold a new Heuristic Learning project by copying the closest template from the heuristic-learning-kit (deterministic-game, stochastic-game, or classification) into ~/workspace/<domain>-hs-poc/. Use when the user asks to create a new HS / HL experiment, scaffold a new project, or run /hs-new.
---

# /hs-new

This skill bootstraps a new Heuristic Learning project. It copies one of
the kit's templates (organized by HS *shape*) into a new directory,
renames the env file to match the user's domain, updates the imports,
and runs `git init`.

The user inherits the template's optimized policy, full iteration history,
and documented `memory.md` lessons. They then **replace the env physics**
with their domain and iterate from there.

## Procedure

1. **Get the domain name.** Ask the user (e.g. "poker", "tetris",
   "spam-classifier"). Use the bare name as `<domain>` throughout.

2. **Decide which template fits.** Ask:
   - Is the env **deterministic given a seed** (no per-trial randomness
     in the outcome metric)? → `templates/deterministic-game/` (env file
     is `flappy.py`, driver is `flappy_hs.py`)
   - Is the env **stochastic per trial** (variance dwarfs single-trial
     signal)? → `templates/stochastic-game/` (env `blackjack.py`,
     driver `blackjack_hs.py`; uses CI-aware regression gate)
   - Is the task **classify-or-respond against a golden set**? →
     `templates/classification/` (env `aitl_hl.py`, with golden +
     paraphrase regression sets)

   If unsure, recommend running `/hs-fit-check <domain>` first.

3. **Find the kit install path.** The kit is installed as a Claude Code
   plugin. Probe the standard locations:
   ```bash
   # Most common: under ~/.claude/plugins/cache/
   ls ~/.claude/plugins/cache/ 2>/dev/null | grep heuristic-learning-kit
   ```
   If not installed via plugin, the user may have cloned the repo
   manually; ask them where it lives.

4. **Copy the template.** Where `<SHAPE>` is `deterministic-game` |
   `stochastic-game` | `classification` and `<KIT>` is the kit install
   path:
   ```bash
   cp -r <KIT>/templates/<SHAPE>/ ~/workspace/<domain>-hs-poc/
   cd ~/workspace/<domain>-hs-poc/
   rm -rf __pycache__ .git
   ```

5. **Rename the env file to match the domain.** Each template ships with
   its original env name (`flappy.py`/`flappy_hs.py` for
   deterministic-game; `blackjack.py`/`blackjack_hs.py` for
   stochastic-game; `aitl_hl.py` for classification). Look at the files
   in the new directory to find `<SRC>` (the base env name) and rename:
   ```bash
   mv <SRC>.py <domain>.py
   mv <SRC>_hs.py <domain>_hs.py     # game templates
   # classification uses a single aitl_hl.py — rename accordingly
   ```
   Update imports inside the renamed files (sed-replace `<SRC>` →
   `<domain>` carefully — be precise about word boundaries):
   ```bash
   sed -i.bak "s/\b<SRC>\b/<domain>/g" <domain>.py <domain>_hs.py policy.py detectors.py
   rm *.bak
   ```

6. **Rename the iterate skill.** The template has
   `.claude/skills/<SRC>-update/`; rename to `<domain>-update`:
   ```bash
   mv .claude/skills/<SRC>-update .claude/skills/<domain>-update
   sed -i.bak "s/\b<SRC>\b/<domain>/g" .claude/skills/<domain>-update/SKILL.md
   rm .claude/skills/<domain>-update/SKILL.md.bak
   ```

7. **Update settings.json permission patterns.** The template's
   `.claude/settings.json` references `<SRC>_hs.py` and `<SRC>.py`;
   sed-replace:
   ```bash
   sed -i.bak "s/<SRC>/<domain>/g" .claude/settings.json
   rm .claude/settings.json.bak
   ```

8. **Update CLAUDE.md, README.md, memory.md** with domain-specific
   replacements. Replace `<SRC>` and the template's title (e.g.
   "Flappy Bird" or "Blackjack") with the user's domain language.
   This step is best done by *reading* each file and rewriting the
   domain-specific paragraphs (the structure should stay the same).

9. **Decide what state files to reset.** The kit-shipped templates
   retain the optimized policy and full iteration history by design —
   that's the load-bearing teaching artifact. But for a *new project*,
   the historical trials don't apply to the new domain.

   Ask the user which mode they want:

   - **Fresh log** (recommended for most domains): reset trials,
     goldens, STATUS, summary. Keep `policy.py` (the optimized version)
     and `memory.md` (the documented lessons). The new domain inherits
     the *scaffolding wisdom* but not the prior trial outcomes.
     ```bash
     : > trials.jsonl
     : > golden.jsonl 2>/dev/null
     : > eval_seeds.jsonl 2>/dev/null
     : > paraphrases.jsonl 2>/dev/null
     : > summary.csv
     : > STATUS.md
     ```

   - **Full reset**: also overwrite `policy.py` with `def act(obs): return 0`
     and clear the "Solved boundary cases" / "Compression history"
     sections in `memory.md`. Use when the user explicitly wants to
     walk the iteration arc from scratch.

   - **Inherit verbatim**: keep everything. Use when the new domain is
     so close to the template's domain that the prior history really is
     relevant (rare).

10. **Stub the env for the new domain.** Tell the user that
    `<domain>.py` currently contains the *template's* env physics
    (flappy / blackjack / aitl). They need to replace it with their
    domain's physics. The driver, policy, detectors, and skill are all
    ready to run once the env interface is reimplemented.

11. **Initialize git.**
    ```bash
    git init -q
    git add -A
    git commit -q -m "Scaffold <domain>-hs-poc from heuristic-learning-kit/<EXAMPLE>"
    ```

12. **Print the next steps:**
    ```text
    Project at ~/workspace/<domain>-hs-poc/
    1. Edit <domain>.py to implement your env (TODO markers throughout)
    2. Adjust policy.py and detectors.py to use your obs keys
    3. Seed the regression set:
         python <domain>_hs.py seeds_add --seeds 100 101 102 103 104
    4. Run a baseline eval:
         python <domain>_hs.py eval --trial-name baseline_v0 \
           --notes "first run" --files policy.py
    5. From inside Claude Code in this dir:
         /<domain>-update    # or /hs-iterate
    ```

## When to skip steps

- If the user already has the example layout and wants to **rename only**,
  skip the cp-r and just do steps 5-8.
- If the user wants to **start with a clean baseline** (reset policy.py
  to `return 0` as well), do that in step 9 alongside the state-file
  reset.

## Stop condition

Exit when the new project is on disk, git-initialized, and the user has
been told the next steps. Do not start implementing the env yourself
unless explicitly asked.
