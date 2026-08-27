"""Flappy HS driver — mirrors aitl_hl.py but for the flappy bird env.

Subcommands:

    eval                run policy on every seed in eval_seeds.jsonl,
                        record one kind:"eval" trial
    probe               run policy on ad-hoc seeds, record kind:"probe"
    seeds_add           append seeds to eval_seeds.jsonl (humans only)
    report              print the agent feedback buffer
    replay              re-run eval set deterministically
    is_new_best         exit 0 if last eval is a new best score_mean

Inference path uses zero LLM calls — policy.act() is pure stdlib.
Maintenance path is /flappy-update inside Claude Code.

Trial schema (all rows have `kind`, `trial_name`, `inferences`):
    kind="eval"   — policy run over eval_seeds; carries score_mean/min/max
                    and per-seed scores
    kind="probe"  — policy run over ad-hoc seeds; carries per-seed scores
                    but no score_mean (so probe doesn't refresh best)

`inferences` counts policy.act() calls (i.e. environment ticks consumed),
mirroring cumulative_env_steps in the article's Atari/MuJoCo trials.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
TRIALS = ROOT / "trials.jsonl"
EVAL_SEEDS = ROOT / "eval_seeds.jsonl"
SUMMARY = ROOT / "summary.csv"
STATUS = ROOT / "STATUS.md"
MAX_TICKS = 5000

SUMMARY_FIELDS = [
    "trial_index", "timestamp", "kind", "trial_name",
    "score_mean", "score_min", "score_max", "inferences",
    "n_seeds", "cumulative_inferences", "notes",
]


def _load_act() -> Callable[[dict], int]:
    sys.path.insert(0, str(ROOT))
    for mod in ("policy", "detectors", "flappy"):
        sys.modules.pop(mod, None)
    import policy
    return policy.act


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _append(path: Path, record: dict[str, Any]) -> None:
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
    if path == TRIALS:
        _write_summary()
        _write_status()


def _fallback_trial_name(t: dict[str, Any], i: int) -> str:
    kind = t.get("kind", "eval")
    return f"{kind}_v{i}"


def _run_seeds(seeds: list[int], max_ticks: int = MAX_TICKS) -> tuple[list[dict], int]:
    """Run policy on each seed; return (per_seed_results, total_inferences)."""
    sys.path.insert(0, str(ROOT))
    for mod in ("policy", "detectors", "flappy"):
        sys.modules.pop(mod, None)
    import flappy
    import policy

    results = []
    total_inferences = 0
    for seed in seeds:
        r = flappy.play(policy.act, seed=seed, max_ticks=max_ticks)
        results.append({"seed": seed, **r})
        total_inferences += r["ticks"]
    return results, total_inferences


def cmd_eval() -> None:
    """Run policy on every eval_seeds.jsonl seed; record one kind:eval row."""
    p = argparse.ArgumentParser(prog="flappy_hs.py eval")
    p.add_argument("--trial-name", required=True,
                   help="hypothesis label, e.g. update_v3_velocity_aware")
    p.add_argument("--notes", required=True,
                   help="one-line rationale")
    p.add_argument("--files", nargs="*", default=[],
                   help="files touched in this edit")
    args = p.parse_args(sys.argv[2:])

    seeds = [r["seed"] for r in _jsonl(EVAL_SEEDS)]
    if not seeds:
        print("error: eval_seeds.jsonl is empty. seed it via `seeds_add`.")
        sys.exit(2)

    results, inferences = _run_seeds(seeds)
    scores = [r["score"] for r in results]
    score_mean = sum(scores) / len(scores)
    score_min = min(scores)
    score_max = max(scores)

    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "eval",
        "trial_name": args.trial_name,
        "inferences": inferences,
        "n_seeds": len(seeds),
        "score_mean": score_mean,
        "score_min": score_min,
        "score_max": score_max,
        "per_seed": results,
        "files_touched": args.files,
        "notes": args.notes,
    }
    _append(TRIALS, record)
    print(f"recorded {args.trial_name}: "
          f"score_mean={score_mean:.2f}  min={score_min}  max={score_max}  "
          f"inferences={inferences}  seeds={len(seeds)}")
    for r in results:
        alive = "alive" if r["alive_at_end"] else "dead"
        print(f"  seed={r['seed']:>5}  score={r['score']:>3}  "
              f"ticks={r['ticks']:>4}  {alive}")


def cmd_probe() -> None:
    """Run policy on ad-hoc seeds (no score_mean recorded; no best refresh)."""
    p = argparse.ArgumentParser(prog="flappy_hs.py probe")
    p.add_argument("--trial-name", required=True)
    p.add_argument("--notes", required=True)
    p.add_argument("--seeds", required=True, nargs="+", type=int,
                   help="ad-hoc seeds to test")
    p.add_argument("--max-ticks", type=int, default=MAX_TICKS,
                   help=f"override episode length (default {MAX_TICKS}); "
                        f"use a larger value to find the policy's real ceiling")
    args = p.parse_args(sys.argv[2:])

    results, inferences = _run_seeds(args.seeds, max_ticks=args.max_ticks)
    scores = [r["score"] for r in results]

    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "probe",
        "trial_name": args.trial_name,
        "inferences": inferences,
        "n_seeds": len(args.seeds),
        "max_ticks": args.max_ticks,
        "per_seed": results,
        "notes": args.notes,
    }
    _append(TRIALS, record)
    print(f"[probe {args.trial_name}]")
    for r in results:
        alive = "alive" if r["alive_at_end"] else "dead"
        print(f"  seed={r['seed']:>5}  score={r['score']:>3}  "
              f"ticks={r['ticks']:>4}  {alive}")
    print(f"\nRecorded probe (inferences={inferences}, scores={scores})")


def cmd_seeds_add() -> None:
    """Append seeds to eval_seeds.jsonl. Humans only — not for the agent."""
    p = argparse.ArgumentParser(prog="flappy_hs.py seeds_add")
    p.add_argument("--seeds", required=True, nargs="+", type=int)
    args = p.parse_args(sys.argv[2:])
    existing = {r["seed"] for r in _jsonl(EVAL_SEEDS)}
    added = 0
    for s in args.seeds:
        if s in existing:
            continue
        with EVAL_SEEDS.open("a") as f:
            f.write(json.dumps({"seed": s}) + "\n")
        existing.add(s)
        added += 1
    print(f"added {added} seed(s); eval_seeds.jsonl now has {len(existing)} seeds")


def cmd_replay() -> None:
    """Re-run policy on eval_seeds without recording. Sanity check / diff."""
    seeds = [r["seed"] for r in _jsonl(EVAL_SEEDS)]
    if not seeds:
        print("(eval_seeds.jsonl is empty)")
        return
    results, inferences = _run_seeds(seeds)
    for r in results:
        alive = "alive" if r["alive_at_end"] else "dead"
        print(f"  seed={r['seed']:>5}  score={r['score']:>3}  "
              f"ticks={r['ticks']:>4}  {alive}")
    scores = [r["score"] for r in results]
    print(f"\nscore_mean={sum(scores)/len(scores):.2f}  "
          f"min={min(scores)}  max={max(scores)}  inferences={inferences}")


def cmd_report() -> None:
    trials = _jsonl(TRIALS)
    seeds = _jsonl(EVAL_SEEDS)
    evals = [t for t in trials if t.get("kind") == "eval"]
    probes = [t for t in trials if t.get("kind") == "probe"]

    print("=" * 64)
    print("FLAPPY-HS REPORT")
    print("=" * 64)
    print(f"trials:      {len(trials)} total ({len(evals)} eval · {len(probes)} probe)")
    print(f"eval_seeds:  {len(seeds)}")
    cum_inf = sum(int(t.get("inferences", 0)) for t in trials)
    print(f"cumulative inferences: {cum_inf}")
    if evals:
        scored = [t for t in evals if isinstance(t.get("score_mean"), (int, float))]
        if scored:
            best = max(scored, key=lambda t: t["score_mean"])
            latest = scored[-1]
            print(f"best score_mean: {best['score_mean']:.2f}  ({best['trial_name']})")
            print(f"latest:          {latest['score_mean']:.2f}  ({latest['trial_name']})")
    print()
    for t in evals[-3:]:
        print(f"  EVAL   {t['trial_name']}")
        print(f"         score_mean={t.get('score_mean', '?'):.2f}  "
              f"min={t.get('score_min', '?')}  max={t.get('score_max', '?')}")
        print(f"         notes: {t.get('notes', '')}")
    for t in probes[-3:]:
        print(f"  PROBE  {t['trial_name']}")
        print(f"         notes: {t.get('notes', '')}")
        for r in t.get("per_seed", [])[:5]:
            print(f"         seed={r['seed']}  score={r['score']}  "
                  f"ticks={r['ticks']}")


def cmd_is_new_best() -> None:
    """Exit 0 with 'yes' if latest eval beats every prior eval."""
    evals = [t for t in _jsonl(TRIALS) if t.get("kind") == "eval"
             and isinstance(t.get("score_mean"), (int, float))]
    if not evals:
        print("no (no eval rows yet)")
        sys.exit(1)
    if len(evals) == 1:
        print(f"yes (first eval; score_mean={evals[0]['score_mean']:.2f})")
        sys.exit(0)
    current = evals[-1]["score_mean"]
    prev_best = max(t["score_mean"] for t in evals[:-1])
    if current > prev_best:
        print(f"yes (score_mean={current:.2f} > prev_best={prev_best:.2f})")
        sys.exit(0)
    if current == prev_best:
        # Invariant #6 mandates a compression pass after every accepted best,
        # and compression deliberately preserves score. Without a distinct
        # verdict the driver rejects the very step CLAUDE.md requires, and the
        # loop cannot tell "compressed cleanly" from "made it worse".
        print(f"unchanged (score_mean={current:.2f} == prev_best; "
              f"acceptable for a compression pass)")
        sys.exit(3)
    print(f"no (score_mean={current:.2f} < prev_best={prev_best:.2f})")
    sys.exit(1)


def _write_summary() -> None:
    trials = _jsonl(TRIALS)
    cum = 0
    rows: list[dict[str, Any]] = []
    for i, t in enumerate(trials):
        kind = t.get("kind", "eval")
        inferences = int(t.get("inferences", 0))
        cum += inferences
        trial_name = t.get("trial_name") or _fallback_trial_name(t, i)
        if kind == "eval":
            sm = t.get("score_mean")
            score_mean = f"{sm:.4f}" if isinstance(sm, (int, float)) else ""
            score_min = t.get("score_min", "")
            score_max = t.get("score_max", "")
        else:  # probe
            score_mean = score_min = score_max = ""
        rows.append({
            "trial_index": i,
            "timestamp": t.get("timestamp", ""),
            "kind": kind,
            "trial_name": trial_name,
            "score_mean": score_mean,
            "score_min": score_min,
            "score_max": score_max,
            "inferences": inferences,
            "n_seeds": t.get("n_seeds", ""),
            "cumulative_inferences": cum,
            "notes": t.get("notes", ""),
        })
    with SUMMARY.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        w.writerows(rows)


def _write_status() -> None:
    trials = _jsonl(TRIALS)
    seeds = _jsonl(EVAL_SEEDS)
    evals = [t for t in trials if t.get("kind") == "eval"]
    probes = [t for t in trials if t.get("kind") == "probe"]
    scored = [t for t in evals if isinstance(t.get("score_mean"), (int, float))]
    cum_inf = sum(int(t.get("inferences", 0)) for t in trials)

    out: list[str] = ["# Flappy-HS Status", ""]
    out.append("_Auto-generated by `flappy_hs.py`. Do not edit; regenerated on every trial append._")
    out.append("")
    if trials:
        out.append(f"Last update: `{trials[-1].get('timestamp', '?')}`")
    else:
        out.append("Last update: _(no trials yet)_")
    out.append("")
    out.append("## Current state")
    out.append("")
    out.append("| Metric | Value |")
    out.append("|---|---|")
    if scored:
        best = max(scored, key=lambda t: t["score_mean"])
        latest = scored[-1]
        out.append(f"| Best score_mean | **{best['score_mean']:.2f}** |")
        out.append(f"| Best trial | `{best['trial_name']}` |")
        out.append(f"| Latest score_mean | {latest['score_mean']:.2f} |")
        out.append(f"| Latest trial | `{latest['trial_name']}` |")
    else:
        out.append("| Best score | _no eval rows yet_ |")
    out.append(f"| Cumulative inferences | {cum_inf} |")
    out.append(f"| Trials | {len(trials)} ({len(evals)} eval · {len(probes)} probe) |")
    out.append(f"| Eval seeds | {len(seeds)} |")
    out.append("")
    out.append("## Score progression (eval rows only)")
    out.append("")
    if scored:
        out.append("| # | trial_name | score_mean | min | max | inferences |")
        out.append("|---|---|---|---|---|---|")
        for i, t in enumerate(scored):
            out.append(
                f"| {i} | `{t['trial_name']}` | "
                f"{t['score_mean']:.2f} | "
                f"{t.get('score_min', '?')} | "
                f"{t.get('score_max', '?')} | "
                f"{int(t.get('inferences', 0))} |"
            )
    else:
        out.append("_(no eval rows yet)_")
    out.append("")
    out.append("## Reproduce current best")
    out.append("")
    out.append("```bash")
    out.append("python flappy_hs.py replay")
    out.append("```")
    out.append("")
    STATUS.write_text("\n".join(out))


COMMANDS: dict[str, Callable[[], None]] = {
    "eval": cmd_eval,
    "probe": cmd_probe,
    "seeds_add": cmd_seeds_add,
    "replay": cmd_replay,
    "report": cmd_report,
    "is_new_best": cmd_is_new_best,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: python flappy_hs.py {{{'|'.join(COMMANDS)}}}")
        sys.exit(2)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
