"""AITL-HL driver: serve queries, record trials, expose feedback channels.

This is the only file the human runs directly. Subcommands:

    ask                 serve one customer query and prompt for annotation
    report              print the full agent feedback buffer
    replay              run every golden case, print pass/fail
    paraphrase_check    run paraphrase robustness check
    probe               run respond() on a list of queries; record as probe
    record              append an eval-kind trial row (used by skills)
    is_new_best         exit 0 if the latest eval is a new best score

The inference path uses zero LLM calls. The /aitl-update skill is the
maintenance path; it reads `report` output and edits policy/detectors,
then closes the loop by calling `record` so trials.jsonl and summary.csv
hold the agent's footprint, not just the human's.

Trial schema follows the article's pattern:
- kind: "ask"  — one customer query served by the policy
- kind: "eval" — one maintenance evaluation (score_mean = regression_pass_rate)
- kind: "probe"— exploratory inference that does not score (future use)

Every row carries `trial_name` (hypothesis label), `inferences` (count of
respond() calls during this trial), and — for eval rows — `score_mean`.
summary.csv aggregates into `cumulative_inferences`, the single
sample-efficiency denominator the article requires.
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
GOLDEN = ROOT / "golden.jsonl"
PARAPHRASES = ROOT / "paraphrases.jsonl"
SUMMARY = ROOT / "summary.csv"
STATUS = ROOT / "STATUS.md"

SUMMARY_FIELDS = [
    "trial_index", "timestamp", "kind", "trial_name",
    "score_mean", "inferences",
    "regression_pass", "regression_total",
    "paraphrase_pass", "paraphrase_total",
    "cumulative_inferences", "notes",
]


def _load_respond() -> Callable[[str], str]:
    sys.path.insert(0, str(ROOT))
    for mod in ("policy", "detectors"):
        sys.modules.pop(mod, None)
    import policy
    return policy.respond


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


def _write_summary() -> None:
    """Regenerate summary.csv from trials.jsonl. Idempotent; safe to call often."""
    trials = _jsonl(TRIALS)
    cum_inferences = 0
    rows: list[dict[str, Any]] = []
    for i, t in enumerate(trials):
        kind = t.get("kind", "ask")
        inferences = int(t.get("inferences", 0))
        cum_inferences += inferences
        trial_name = t.get("trial_name") or _fallback_trial_name(t, i)
        if kind == "ask":
            if t.get("adopted"):
                notes = "adopted"
            elif t.get("fix"):
                notes = f"fix: {t['fix']}"
            else:
                notes = "non-adopt"
            score_mean = reg_p = reg_t = par_p = par_t = ""
        elif kind == "probe":
            notes = t.get("notes", "")
            score_mean = reg_p = reg_t = par_p = par_t = ""
        else:  # eval
            notes = t.get("notes", "")
            reg_p = t.get("regression_pass", "")
            reg_t = t.get("regression_total", "")
            par_p = t.get("paraphrase_pass", "")
            par_t = t.get("paraphrase_total", "")
            sm = t.get("score_mean")
            score_mean = f"{sm:.4f}" if isinstance(sm, (int, float)) else ""
        rows.append({
            "trial_index": i,
            "timestamp": t.get("timestamp", ""),
            "kind": kind,
            "trial_name": trial_name,
            "score_mean": score_mean,
            "inferences": inferences,
            "regression_pass": reg_p,
            "regression_total": reg_t,
            "paraphrase_pass": par_p,
            "paraphrase_total": par_t,
            "cumulative_inferences": cum_inferences,
            "notes": notes,
        })
    with SUMMARY.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_status() -> None:
    """Regenerate STATUS.md — a human-readable snapshot of system state.

    Like summary.csv but markdown. Both are derived from trials.jsonl and
    regenerated on every append. Mirrors the per-run README.md the article
    requires for bounded Atari57 runs — adapted for a continual system.
    """
    trials = _jsonl(TRIALS)
    goldens = _jsonl(GOLDEN)
    paraphrases = _jsonl(PARAPHRASES)

    asks = [t for t in trials if t.get("kind", "ask") == "ask"]
    evals = [t for t in trials if t.get("kind") == "eval"]
    probes = [t for t in trials if t.get("kind") == "probe"]
    scored = [t for t in evals if isinstance(t.get("score_mean"), (int, float))]
    cum_inferences = sum(int(t.get("inferences", 0)) for t in trials)
    n_paraphrase_variants = sum(len(c.get("paraphrases", [])) for c in paraphrases)

    out: list[str] = []
    out.append("# AITL-HL Status")
    out.append("")
    out.append("_Auto-generated by `aitl_hl.py`. Do not edit; regenerated on every trial append._")
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
        out.append(f"| Best score (regression pass rate) | **{best['score_mean']:.4f}** |")
        out.append(f"| Best trial | `{best['trial_name']}` |")
        out.append(f"| Latest score | {latest['score_mean']:.4f} |")
        out.append(f"| Latest trial | `{latest['trial_name']}` |")
    else:
        out.append("| Best score | _no eval rows yet_ |")
    out.append(f"| Cumulative inferences | {cum_inferences} |")
    out.append(
        f"| Trials | {len(trials)} total "
        f"({len(asks)} ask · {len(evals)} eval · {len(probes)} probe) |"
    )
    out.append(f"| Golden set | {len(goldens)} cases |")
    out.append(
        f"| Paraphrase set | {len(paraphrases)} canonical · "
        f"{n_paraphrase_variants} variants |"
    )
    out.append("")
    out.append("## Recent trials (last 5)")
    out.append("")
    if trials:
        out.append("| # | when | kind | trial_name | score | inferences |")
        out.append("|---|---|---|---|---|---|")
        start = max(0, len(trials) - 5)
        for i, t in enumerate(trials[start:], start=start):
            ts = t.get("timestamp", "")
            when = ts.split("T")[1][:8] if "T" in ts else ts
            name = t.get("trial_name") or _fallback_trial_name(t, i)
            sm = t.get("score_mean")
            score = f"{sm:.4f}" if isinstance(sm, (int, float)) else "—"
            out.append(
                f"| {i} | {when} | {t.get('kind', 'ask')} | "
                f"`{name}` | {score} | {int(t.get('inferences', 0))} |"
            )
    else:
        out.append("_(no trials yet)_")
    out.append("")
    out.append("## Reproduce current state")
    out.append("")
    out.append("```bash")
    out.append("python aitl_hl.py replay")
    out.append("```")
    if goldens:
        out.append("")
        out.append(f"Expected: {len(goldens)}/{len(goldens)} passing.")
    out.append("")
    STATUS.write_text("\n".join(out))


def _fallback_trial_name(t: dict[str, Any], index: int) -> str:
    """For legacy rows missing a trial_name, generate a stable placeholder."""
    kind = t.get("kind", "ask")
    if kind == "ask":
        return f"ask_v{index}"
    return f"{t.get('skill', kind)}_v{index}"


def _inferences_count() -> int:
    """How many respond() calls a full replay + paraphrase_check performs.

    Mirrors what _replay() and _paraphrase_check() do internally. Used by
    `record` to fill the `inferences` field deterministically without
    instrumenting respond() itself.
    """
    n_goldens = len(_jsonl(GOLDEN))
    paraphrase_rows = _jsonl(PARAPHRASES)
    n_paraphrases = sum(1 + len(c.get("paraphrases", [])) for c in paraphrase_rows)
    return n_goldens + n_paraphrases


def _next_ask_index() -> int:
    return sum(1 for t in _jsonl(TRIALS) if t.get("kind", "ask") == "ask") + 1


def _replay() -> list[dict[str, Any]]:
    respond = _load_respond()
    out = []
    for case in _jsonl(GOLDEN):
        got = respond(case["query"])
        out.append({
            "query": case["query"],
            "expected": case["adopted_response"],
            "got": got,
            "pass": got == case["adopted_response"],
        })
    return out


def _paraphrase_check() -> list[dict[str, Any]]:
    respond = _load_respond()
    out = []
    for case in _jsonl(PARAPHRASES):
        canonical = respond(case["canonical_query"])
        variants = [
            {"text": p, "response": respond(p)} for p in case.get("paraphrases", [])
        ]
        consistent = all(v["response"] == canonical for v in variants)
        out.append({
            "canonical_query": case["canonical_query"],
            "canonical_response": canonical,
            "variants": variants,
            "consistent": consistent,
        })
    return out


def cmd_ask() -> None:
    respond = _load_respond()
    q = input("Customer query: ").strip()
    if not q:
        print("(empty query, nothing to do)")
        return
    a = respond(q)
    print(f"\nA: {a}\n")
    adopted = input("Adopt without edits? (y/n) ").strip().lower() == "y"
    fix = ""
    if not adopted:
        fix = input("Correct response (what should it have said): ").strip()
    _append(TRIALS, {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "ask",
        "trial_name": f"ask_v{_next_ask_index()}",
        "inferences": 1,
        "query": q,
        "response": a,
        "adopted": adopted,
        "fix": fix,
    })
    if adopted:
        _append(GOLDEN, {"query": q, "adopted_response": a})
    print(f"\n(logged. trials={len(_jsonl(TRIALS))} golden={len(_jsonl(GOLDEN))})")


def cmd_probe() -> None:
    """Run respond() on a list of queries, append a kind: 'probe' row.

    Probes are exploratory inference: they touch the policy (counted toward
    cumulative_inferences) but produce no score_mean. Use to verify
    detector coverage on synthetic queries before deciding what to edit,
    or to interrogate edge cases.
    """
    p = argparse.ArgumentParser(prog="aitl_hl.py probe")
    p.add_argument("--trial-name", required=True,
                   help="hypothesis label, e.g. intent_coverage_v1_refund_synonyms")
    p.add_argument("--notes", required=True,
                   help="one-line description of what you're investigating")
    p.add_argument("--queries", required=True, nargs="+",
                   help="queries to run respond() on")
    args = p.parse_args(sys.argv[2:])

    sys.path.insert(0, str(ROOT))
    for mod in ("policy", "detectors"):
        sys.modules.pop(mod, None)
    import detectors
    import policy

    print(f"[probe {args.trial_name}]")
    responses: list[str] = []
    for q in args.queries:
        r = policy.respond(q)
        i = detectors.intent(q)
        responses.append(r)
        r_short = r if len(r) <= 56 else r[:53] + "..."
        print(f"  {q!r:42}  intent={i:<8}  resp={r_short!r}")

    _append(TRIALS, {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "probe",
        "trial_name": args.trial_name,
        "inferences": len(args.queries),
        "queries": args.queries,
        "responses": responses,
        "notes": args.notes,
    })
    cum = sum(int(t.get("inferences", 0)) for t in _jsonl(TRIALS))
    print(f"\nRecorded probe (inferences={len(args.queries)}, cumulative={cum})")


def cmd_record() -> None:
    """Append an eval-kind trial row capturing the current report state.

    Skills call this at the end of their work. The recorded row holds what
    the new policy state DID (regression pass rate, paraphrase consistency)
    — not metadata about the edit. The edit itself lives in git.
    """
    p = argparse.ArgumentParser(prog="aitl_hl.py record")
    p.add_argument("--skill", required=True,
                   choices=["aitl-update", "aitl-simplify", "aitl-paraphrase"])
    p.add_argument("--trial-name", required=True,
                   help="hypothesis label, e.g. update_v3_broaden_return_regex")
    p.add_argument("--notes", required=True,
                   help="one-line rationale for this eval")
    p.add_argument("--files", nargs="*", default=[],
                   help="files touched (e.g. policy.py detectors.py)")
    args = p.parse_args(sys.argv[2:])

    replay_results = _replay()
    paraphrase_results = _paraphrase_check()

    regression_pass = sum(r["pass"] for r in replay_results)
    regression_total = len(replay_results)
    paraphrase_pass = sum(r["consistent"] for r in paraphrase_results)
    paraphrase_total = len(paraphrase_results)

    score_mean: float | None = (
        regression_pass / regression_total if regression_total > 0 else None
    )

    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "eval",
        "trial_name": args.trial_name,
        "skill": args.skill,
        "inferences": _inferences_count(),
        "score_mean": score_mean,
        "regression_pass": regression_pass,
        "regression_total": regression_total,
        "paraphrase_pass": paraphrase_pass,
        "paraphrase_total": paraphrase_total,
        "files_touched": args.files,
        "notes": args.notes,
    }
    _append(TRIALS, record)
    score_str = f"{score_mean:.4f}" if score_mean is not None else "n/a"
    print(
        f"recorded {args.trial_name} ({args.skill}): "
        f"score_mean={score_str}  "
        f"regression={regression_pass}/{regression_total}  "
        f"paraphrase={paraphrase_pass}/{paraphrase_total}  "
        f"inferences={record['inferences']}"
    )


def cmd_is_new_best() -> None:
    """Print 'yes' (and exit 0) if the latest eval beats every prior eval.

    The /aitl-update skill calls this after `record` to decide whether to
    auto-trigger /aitl-simplify. Mirrors the Atari57 prompt rule:
    "每当你刷新当前 run 的 best_score 时…先进入一次「代码简化阶段」".

    Prints 'no' (and exits 1) if not a refresh, or if no eval rows exist.
    """
    evals = [t for t in _jsonl(TRIALS) if t.get("kind") == "eval"
             and isinstance(t.get("score_mean"), (int, float))]
    if not evals:
        print("no (no eval rows yet)")
        sys.exit(1)
    if len(evals) == 1:
        print(f"yes (first eval; score_mean={evals[0]['score_mean']:.4f})")
        sys.exit(0)
    current = evals[-1]["score_mean"]
    prev_best = max(t["score_mean"] for t in evals[:-1])
    if current > prev_best:
        print(f"yes (score_mean={current:.4f} > prev_best={prev_best:.4f})")
        sys.exit(0)
    if current == prev_best:
        # Invariant #6 mandates a compression pass after every accepted best,
        # and compression deliberately preserves score. Without a distinct
        # verdict the driver rejects the very step CLAUDE.md requires, and the
        # loop cannot tell "compressed cleanly" from "made it worse".
        print(f"unchanged (score_mean={current:.4f} == prev_best; "
              f"acceptable for a compression pass)")
        sys.exit(3)
    print(f"no (score_mean={current:.4f} < prev_best={prev_best:.4f})")
    sys.exit(1)


def cmd_report() -> None:
    trials = _jsonl(TRIALS)
    golden = _jsonl(GOLDEN)
    paraphrases = _jsonl(PARAPHRASES)
    replay_results = _replay()
    paraphrase_results = _paraphrase_check()

    asks = [t for t in trials if t.get("kind", "ask") == "ask"]
    non_adopted = [t for t in asks if not t.get("adopted")]
    escalations = [t for t in asks if "escalating" in t.get("response", "")]
    probes = [t for t in trials if t.get("kind") == "probe"]
    passing = sum(r["pass"] for r in replay_results)
    consistent = sum(r["consistent"] for r in paraphrase_results)

    print("=" * 64)
    print("AITL-HL REPORT")
    print("=" * 64)
    print(f"trials:      {len(trials)} total · {len(non_adopted)} non-adopted asks")
    print(f"golden:      {len(golden)}")
    print(f"paraphrases: {len(paraphrases)}")
    print(f"probes:      {len(probes)}")
    print(f"escalations: {len(escalations)}")
    print(f"regression:  {passing}/{len(replay_results)} passing")
    print(f"paraphrase:  {consistent}/{len(paraphrase_results)} consistent")
    print()

    for r in replay_results:
        if not r["pass"]:
            print(f"  REGRESSION   q:        {r['query']!r}")
            print(f"               expected: {r['expected']!r}")
            print(f"               got:      {r['got']!r}")
    for r in paraphrase_results:
        if not r["consistent"]:
            print(f"  INCONSISTENT q:          {r['canonical_query']!r}")
            print(f"               canonical:  {r['canonical_response']!r}")
            for v in r["variants"]:
                if v["response"] != r["canonical_response"]:
                    print(f"               paraphrase: {v['text']!r}")
                    print(f"               got:        {v['response']!r}")
    for t in non_adopted[-5:]:
        print(f"  NON-ADOPT    q:   {t['query']!r}")
        print(f"               got: {t['response']!r}")
        print(f"               fix: {t['fix']!r}")
    for t in probes[-3:]:
        print(f"  PROBE        name:    {t.get('trial_name', '?')}")
        print(f"               notes:   {t.get('notes', '')}")
        print(f"               queries: {t.get('queries', [])}")


def cmd_replay() -> None:
    results = _replay()
    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"[{status}] {r['query']!r}")
        if not r["pass"]:
            print(f"        expected: {r['expected']!r}")
            print(f"        got:      {r['got']!r}")
    passing = sum(r["pass"] for r in results)
    print(f"\n{passing}/{len(results)} passing")


def cmd_paraphrase_check() -> None:
    results = _paraphrase_check()
    for r in results:
        status = "OK" if r["consistent"] else "DIVERGE"
        print(f"[{status}] {r['canonical_query']!r}")
        if not r["consistent"]:
            print(f"        canonical: {r['canonical_response']!r}")
            for v in r["variants"]:
                if v["response"] != r["canonical_response"]:
                    print(f"        diverged on {v['text']!r}: {v['response']!r}")
    consistent = sum(r["consistent"] for r in results)
    print(f"\n{consistent}/{len(results)} consistent")


COMMANDS: dict[str, Callable[[], None]] = {
    "ask": cmd_ask,
    "report": cmd_report,
    "replay": cmd_replay,
    "paraphrase_check": cmd_paraphrase_check,
    "probe": cmd_probe,
    "record": cmd_record,
    "is_new_best": cmd_is_new_best,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: python aitl_hl.py {{{'|'.join(COMMANDS)}}}")
        sys.exit(2)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
