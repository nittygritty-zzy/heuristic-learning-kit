"""Blackjack HS driver — mirrors flappy_hs.py for the blackjack env.

Subcommands:

    eval                run policy on every seed in eval_seeds.jsonl,
                        record one kind:"eval" trial
    probe               run policy on ad-hoc seeds, record kind:"probe"
    seeds_add           append seeds to eval_seeds.jsonl (humans only)
    report              print the agent feedback buffer
    replay              re-run eval set deterministically
    is_new_best         exit 0 yes / 1 regression / 2 CI-overlap maybe
                        / 3 unchanged (compression pass)
                        (with 1-sigma CI overlap protection)

Score = EV per hand (mean unit return). Each "seed" plays
N_HANDS_PER_SEED hands sharing one RNG stream, so a 5-seed eval is
50,000 hands. Per-hand stddev ~1.15 → per-eval SE ~ 0.0051 (across all
50k hands). Improvements smaller than ~0.01 EV are not reliably
detectable, which is why is_new_best uses CI overlap rather than strict
greater-than.

`inferences` counts policy.act() calls (i.e. hit/stand decisions made),
mirroring cumulative_env_steps in the article's Atari/MuJoCo trials.
Each hand calls act() 0..many times depending on how the policy plays.
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
N_HANDS_PER_SEED = 10000

SUMMARY_FIELDS = [
    "trial_index", "timestamp", "kind", "trial_name",
    "ev", "se", "ci95_low", "ci95_high",
    "inferences", "n_hands", "cumulative_inferences", "notes",
]


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
    return f"{t.get('kind', 'eval')}_v{i}"


def _run_seeds(seeds: list[int], n_hands: int = N_HANDS_PER_SEED) -> tuple[list[dict], int]:
    """Run policy on each seed; return (per_seed_results, total_inferences)."""
    sys.path.insert(0, str(ROOT))
    for mod in ("policy", "detectors", "blackjack"):
        sys.modules.pop(mod, None)
    import blackjack
    import policy

    results = []
    total_inferences = 0
    for seed in seeds:
        r = blackjack.play_session(policy.act, seed=seed, n_hands=n_hands)
        results.append({"seed": seed, **r})
        total_inferences += r["n_hits"] + r["n_hands"]  # one act() call per decision; many hands have just stand
    return results, total_inferences


def _aggregate(per_seed: list[dict]) -> dict:
    """Pool per-seed results into a single EV + SE for the whole eval."""
    n = sum(r["n_hands"] for r in per_seed)
    # weighted mean
    ev = sum(r["ev"] * r["n_hands"] for r in per_seed) / n
    # pooled variance approximation
    pooled_var = sum((r["stddev"] ** 2) * (r["n_hands"] - 1) for r in per_seed) / max(1, n - len(per_seed))
    se = (pooled_var / n) ** 0.5
    return {
        "ev": ev,
        "se": se,
        "ci95_low": ev - 1.96 * se,
        "ci95_high": ev + 1.96 * se,
        "n_hands": n,
    }


def cmd_eval() -> None:
    """Run policy on every eval_seeds.jsonl seed; record one kind:eval row."""
    p = argparse.ArgumentParser(prog="blackjack_hs.py eval")
    p.add_argument("--trial-name", required=True,
                   help="hypothesis label, e.g. update_v3_hard_stand_on_17")
    p.add_argument("--notes", required=True,
                   help="one-line rationale")
    p.add_argument("--files", nargs="*", default=[],
                   help="files touched in this edit")
    args = p.parse_args(sys.argv[2:])

    seeds = [r["seed"] for r in _jsonl(EVAL_SEEDS)]
    if not seeds:
        print("error: eval_seeds.jsonl is empty. seed it via `seeds_add`.")
        sys.exit(2)

    per_seed, inferences = _run_seeds(seeds)
    agg = _aggregate(per_seed)

    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "eval",
        "trial_name": args.trial_name,
        "inferences": inferences,
        "n_seeds": len(seeds),
        "n_hands": agg["n_hands"],
        "ev": agg["ev"],
        "se": agg["se"],
        "ci95_low": agg["ci95_low"],
        "ci95_high": agg["ci95_high"],
        "per_seed": per_seed,
        "files_touched": args.files,
        "notes": args.notes,
    }
    _append(TRIALS, record)
    print(
        f"recorded {args.trial_name}: "
        f"EV={agg['ev']:+.4f} ± {agg['se']:.4f} (95% CI [{agg['ci95_low']:+.4f}, {agg['ci95_high']:+.4f}])  "
        f"inferences={inferences}  hands={agg['n_hands']}"
    )
    for r in per_seed:
        print(f"  seed={r['seed']:>5}  EV={r['ev']:+.4f}  "
              f"w/l/p={r['wins']}/{r['losses']}/{r['pushes']}  "
              f"pBJ={r['player_bj']} dBJ={r['dealer_bj']}")


def cmd_probe() -> None:
    """Run policy on ad-hoc seeds (no best refresh; no eval-set pollution)."""
    p = argparse.ArgumentParser(prog="blackjack_hs.py probe")
    p.add_argument("--trial-name", required=True)
    p.add_argument("--notes", required=True)
    p.add_argument("--seeds", required=True, nargs="+", type=int)
    p.add_argument("--n-hands", type=int, default=N_HANDS_PER_SEED,
                   help=f"hands per seed (default {N_HANDS_PER_SEED})")
    args = p.parse_args(sys.argv[2:])

    per_seed, inferences = _run_seeds(args.seeds, n_hands=args.n_hands)
    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "probe",
        "trial_name": args.trial_name,
        "inferences": inferences,
        "n_seeds": len(args.seeds),
        "n_hands": args.n_hands * len(args.seeds),
        "per_seed": per_seed,
        "notes": args.notes,
    }
    _append(TRIALS, record)
    print(f"[probe {args.trial_name}]")
    for r in per_seed:
        print(f"  seed={r['seed']:>5}  EV={r['ev']:+.4f}  "
              f"w/l/p={r['wins']}/{r['losses']}/{r['pushes']}")
    print(f"\nRecorded probe (inferences={inferences})")


def cmd_seeds_add() -> None:
    """Append seeds to eval_seeds.jsonl. Humans only."""
    p = argparse.ArgumentParser(prog="blackjack_hs.py seeds_add")
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
    """Re-run policy on eval_seeds without recording."""
    seeds = [r["seed"] for r in _jsonl(EVAL_SEEDS)]
    if not seeds:
        print("(eval_seeds.jsonl is empty)")
        return
    per_seed, inferences = _run_seeds(seeds)
    agg = _aggregate(per_seed)
    for r in per_seed:
        print(f"  seed={r['seed']:>5}  EV={r['ev']:+.4f}  "
              f"w/l/p={r['wins']}/{r['losses']}/{r['pushes']}")
    print(f"\nEV={agg['ev']:+.4f} ± {agg['se']:.4f}  "
          f"95% CI [{agg['ci95_low']:+.4f}, {agg['ci95_high']:+.4f}]")


def cmd_report() -> None:
    trials = _jsonl(TRIALS)
    seeds = _jsonl(EVAL_SEEDS)
    evals = [t for t in trials if t.get("kind") == "eval"]
    probes = [t for t in trials if t.get("kind") == "probe"]

    print("=" * 64)
    print("BLACKJACK-HS REPORT")
    print("=" * 64)
    print(f"trials:      {len(trials)} total ({len(evals)} eval · {len(probes)} probe)")
    print(f"eval_seeds:  {len(seeds)}")
    cum_inf = sum(int(t.get("inferences", 0)) for t in trials)
    print(f"cumulative inferences: {cum_inf}")
    if evals:
        scored = [t for t in evals if isinstance(t.get("ev"), (int, float))]
        if scored:
            best = max(scored, key=lambda t: t["ev"])
            latest = scored[-1]
            print(f"best EV:    {best['ev']:+.4f} ± {best['se']:.4f}  ({best['trial_name']})")
            print(f"latest EV:  {latest['ev']:+.4f} ± {latest['se']:.4f}  ({latest['trial_name']})")
    print()
    for t in evals[-3:]:
        print(f"  EVAL   {t['trial_name']}")
        print(f"         EV={t.get('ev', 0):+.4f} ± {t.get('se', 0):.4f}  "
              f"CI[{t.get('ci95_low', 0):+.4f}, {t.get('ci95_high', 0):+.4f}]")
        print(f"         notes: {t.get('notes', '')}")
    for t in probes[-3:]:
        print(f"  PROBE  {t['trial_name']}")
        print(f"         notes: {t.get('notes', '')}")


def cmd_is_new_best() -> None:
    """Exit 0 with 'yes' if latest eval EV beats every prior eval AND the
    confidence intervals do not overlap (so we're confident the gain is real).

    Variance-aware version of flappy's is_new_best: blackjack EV per hand
    fluctuates ~0.005 from noise alone in 50k hands, so a strict `>` would
    crown chance fluctuations as new bests.
    """
    evals = [t for t in _jsonl(TRIALS) if t.get("kind") == "eval"
             and isinstance(t.get("ev"), (int, float))]
    if not evals:
        print("no (no eval rows yet)")
        sys.exit(1)
    if len(evals) == 1:
        print(f"yes (first eval; EV={evals[0]['ev']:+.4f})")
        sys.exit(0)
    current = evals[-1]
    prior_evs = [t["ev"] for t in evals[:-1]]
    prev_best = max(prior_evs)
    prev_best_trial = max(evals[:-1], key=lambda t: t["ev"])
    if current["ev"] == prev_best:
        # Invariant #6 mandates a compression pass after every accepted best,
        # and compression deliberately preserves EV. Exit 3 keeps that distinct
        # from 1 (regression) and from 2 (improved but CI overlaps).
        print(f"unchanged (EV={current['ev']:+.4f} == prev_best; "
              f"acceptable for a compression pass)")
        sys.exit(3)
    if current["ev"] < prev_best:
        print(f"no (EV={current['ev']:+.4f} < prev_best={prev_best:+.4f})")
        sys.exit(1)
    # Require CI95 separation: current.lower > prev_best.upper
    prev_best_high = prev_best_trial.get("ci95_high", prev_best)
    if current["ci95_low"] <= prev_best_high:
        print(
            f"maybe (EV={current['ev']:+.4f} > prev_best={prev_best:+.4f}, "
            f"but CI95 overlap: current.low={current['ci95_low']:+.4f} <= "
            f"prev_best.high={prev_best_high:+.4f} — not confidently better)"
        )
        sys.exit(2)
    print(
        f"yes (EV={current['ev']:+.4f} > prev_best={prev_best:+.4f}, "
        f"CI95 clearly separated: current.low={current['ci95_low']:+.4f} > "
        f"prev_best.high={prev_best_high:+.4f})"
    )
    sys.exit(0)


def _write_summary() -> None:
    trials = _jsonl(TRIALS)
    cum = 0
    rows: list[dict[str, Any]] = []
    for i, t in enumerate(trials):
        kind = t.get("kind", "eval")
        inferences = int(t.get("inferences", 0))
        cum += inferences
        trial_name = t.get("trial_name") or _fallback_trial_name(t, i)
        ev = t.get("ev")
        se = t.get("se")
        rows.append({
            "trial_index": i,
            "timestamp": t.get("timestamp", ""),
            "kind": kind,
            "trial_name": trial_name,
            "ev": f"{ev:+.4f}" if isinstance(ev, (int, float)) else "",
            "se": f"{se:.4f}" if isinstance(se, (int, float)) else "",
            "ci95_low": f"{t.get('ci95_low', ''):+.4f}" if isinstance(t.get("ci95_low"), (int, float)) else "",
            "ci95_high": f"{t.get('ci95_high', ''):+.4f}" if isinstance(t.get("ci95_high"), (int, float)) else "",
            "inferences": inferences,
            "n_hands": t.get("n_hands", ""),
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
    scored = [t for t in evals if isinstance(t.get("ev"), (int, float))]
    cum_inf = sum(int(t.get("inferences", 0)) for t in trials)

    out: list[str] = ["# Blackjack-HS Status", ""]
    out.append("_Auto-generated by `blackjack_hs.py`. Do not edit; regenerated on every trial append._")
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
        best = max(scored, key=lambda t: t["ev"])
        latest = scored[-1]
        out.append(f"| Best EV | **{best['ev']:+.4f}** ± {best.get('se', 0):.4f} |")
        out.append(f"| Best trial | `{best['trial_name']}` |")
        out.append(f"| Latest EV | {latest['ev']:+.4f} ± {latest.get('se', 0):.4f} |")
        out.append(f"| Latest trial | `{latest['trial_name']}` |")
    else:
        out.append("| Best EV | _no eval rows yet_ |")
    out.append(f"| Cumulative inferences | {cum_inf} |")
    out.append(f"| Trials | {len(trials)} ({len(evals)} eval · {len(probes)} probe) |")
    out.append(f"| Eval seeds | {len(seeds)} (× {N_HANDS_PER_SEED} hands each) |")
    out.append("")
    out.append("## EV progression (eval rows only)")
    out.append("")
    if scored:
        out.append("| # | trial_name | EV | SE | CI95 | inferences |")
        out.append("|---|---|---|---|---|---|")
        for i, t in enumerate(scored):
            out.append(
                f"| {i} | `{t['trial_name']}` | "
                f"{t['ev']:+.4f} | "
                f"{t.get('se', 0):.4f} | "
                f"[{t.get('ci95_low', 0):+.4f}, {t.get('ci95_high', 0):+.4f}] | "
                f"{int(t.get('inferences', 0))} |"
            )
    else:
        out.append("_(no eval rows yet)_")
    out.append("")
    out.append("## Reference EVs")
    out.append("")
    out.append("- Basic strategy (hit/stand, S17, no double/split): ~ **-0.015** to **-0.025**")
    out.append("- Always stand: ~ -0.16")
    out.append("- Always hit: ~ -0.88")
    out.append("- Always hit < 17 (mimic dealer): ~ -0.08")
    out.append("")
    out.append("## Reproduce current state")
    out.append("")
    out.append("```bash")
    out.append("python blackjack_hs.py replay")
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
        print(f"usage: python blackjack_hs.py {{{'|'.join(COMMANDS)}}}")
        sys.exit(2)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
