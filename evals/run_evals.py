"""Evaluation harness for the Career Planning Agent.

  python -m evals.run_evals                 # LIVE: real web search + your configured model (this is the evidence to submit)
  python -m evals.run_evals --runs 5        # more repeats
  python -m evals.run_evals --llm off       # live search, no model (tests the no-model path)
  python -m evals.run_evals --offline       # fake search, no network: only checks the harness and the safety rules

Every run builds a FRESH assistant (new search cache, new temp database, new model client), so repeated runs are
independent samples, not cache hits. Results go to evals/results/ (JSON per run + RESULTS.md).

Metrics (n runs per case, c of them pass):  pass@1 = c/n   pass@k = 1 - C(n-c,k)/C(n,k) (k = n by default:
"passed at least once")   all-k = every run passed (consistency)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from datetime import date
from math import comb
from pathlib import Path

ROOT = Path(__file__).parent
URL = re.compile(r"https?://[^\s\"'\\<>)\]]+")
DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}, \d{4}\b")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that at least one of k runs drawn from n (c of which passed) passes."""
    return 1.0 if n - c < k else 1.0 - comb(n - c, k) / comb(n, k)


def _queries(turn) -> str:
    return " | ".join(str(e.get("query", "")) for e in turn.trace.events if e["type"] == "search").lower()


def _deadlines_found(turn) -> int:
    return next((e.get("found", 0) for e in turn.trace.events if e["type"] == "deadlines"), 0)


def _urls_ok(turn) -> bool:
    return all(u.rstrip(".,;:") in set(turn.sources) for u in URL.findall(turn.answer))


CHECKS = {   # name -> (turn, expected) -> bool
    "agents_include": lambda t, x: set(x) <= set(t.agents_used),
    "answer_contains_any": lambda t, x: any(s.lower() in t.answer.lower() for s in x),
    "answer_excludes": lambda t, x: not any(s.lower() in t.answer.lower() for s in x),
    "blocked": lambda t, x: t.blocked == x,
    "needs_input": lambda t, x: t.needs_input == x,
    "action": lambda t, x: t.action == x,
    "offer_quiz": lambda t, x: t.offer_quiz == x,
    "has_ics": lambda t, x: bool(t.ics) == x,
    "min_sources": lambda t, x: len(t.sources) >= x,
    "max_sources": lambda t, x: len(t.sources) <= x,
    "only_cited_urls": lambda t, x: _urls_ok(t) == x,                       # every link shown came from a search result
    "no_invented_dates": lambda t, x: not (x and DATE.search(t.answer) and _deadlines_found(t) == 0),
    "queries_include": lambda t, x: all(s.lower() in _queries(t) for s in x),
}


def failed_checks(turn, checks: dict) -> list[str]:
    return [name for name, expected in checks.items() if not CHECKS[name](turn, expected)]


def make_assistant(offline: bool, llm_mode: str, tmp: str, today):
    from core.assistant import Assistant
    if offline:
        from tests.conftest import FakeSearch
        return Assistant(search=FakeSearch(), db_path=f"{tmp}/e.db", mode="off", today=lambda: today)
    return Assistant(db_path=f"{tmp}/e.db", mode=llm_mode, today=lambda: today)


def run_once(case: dict, offline: bool, llm_mode: str, today) -> dict:
    from memory.session_memory import SessionMemory
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            a = make_assistant(offline, llm_mode, tmp, today)
            a.update_profile("eval", case["profile"])
            turn = a.handle("eval", case["question"], SessionMemory())
            failed, error = failed_checks(turn, case["checks"]), ""
            answer, used_llm, n_src = turn.answer, turn.used_llm, len(turn.sources)
        except Exception as e:  # a crash is a failed run, not a harness crash
            failed, error, answer, used_llm, n_src = ["crashed"], repr(e), "", False, 0
    return {"passed": not failed, "failed": failed, "error": error, "seconds": round(time.perf_counter() - start, 2),
            "used_llm": used_llm, "sources": n_src, "answer": answer[:600]}


def summarize(results: list[dict], k: int) -> dict:
    def agg(rows):
        n = len(rows)
        return {"cases": n,
                "pass@1": sum(r["c"] / r["n"] for r in rows) / n if n else 0.0,
                f"pass@{k}": sum(pass_at_k(r["n"], r["c"], k) for r in rows) / n if n else 0.0,
                f"all-{k}": sum(r["c"] == r["n"] for r in rows) / n if n else 0.0}
    return {"overall": agg(results), "normal": agg([r for r in results if r["category"] == "normal"]),
            "adversarial": agg([r for r in results if r["category"] == "adversarial"])}


def write_report(out: Path, meta: dict, results: list[dict], summary: dict, k: int) -> None:
    pct = lambda x: f"{100 * x:.1f}%"
    lines = [f"# Evaluation results", "",
             f"- Run on {meta['date']} | mode: **{meta['mode']}** | runs per case: **{meta['runs']}** | cases: **{len(results)}**",
             "- Each run uses a fresh assistant, empty search cache and temp database (runs are independent).", "",
             "| Group | Cases | pass@1 | " f"pass@{k} | all-{k} (consistent) |", "|---|---|---|---|---|"]
    for name, s in summary.items():
        lines.append(f"| {name} | {s['cases']} | {pct(s['pass@1'])} | {pct(s[f'pass@{k}'])} | {pct(s[f'all-{k}'])} |")
    lines += ["", "## Per case", "", f"| Case | Type | Passed | Failed checks | Question |", "|---|---|---|---|---|"]
    for r in results:
        bad = sorted({f for run in r["runs"] for f in run["failed"]})
        lines.append(f"| {r['id']} | {r['category']} | {r['c']}/{r['n']} | {', '.join(bad) or '-'} | {r['question'][:70]} |")
    flaky = [r for r in results if 0 < r["c"] < r["n"]]
    failing = [r for r in results if r["c"] < r["n"]]
    lines += ["", "## Failures and flaky cases", ""]
    if not failing:
        lines.append("None in this run.")
    for r in failing:
        kind = "FLAKY (passed sometimes)" if r in flaky else "FAILED every run"
        lines.append(f"### {r['id']}: {kind}")
        for i, run in enumerate(r["runs"], 1):
            if not run["passed"]:
                lines.append(f"- run {i}: failed `{', '.join(run['failed'])}` {run['error']}")
                lines.append(f"  - answer began: `{run['answer'][:160].replace(chr(10), ' ')}`")
    lines += ["", "See `evals/ANALYSIS.md` for the written analysis of these failures."]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(ROOT / "cases.jsonl"))
    ap.add_argument("--runs", type=int, default=3, help="runs per case (>= 3 for the assignment)")
    ap.add_argument("--k", type=int, default=0, help="k for pass@k (default = runs)")
    ap.add_argument("--llm", default="auto", choices=("auto", "off"))
    ap.add_argument("--offline", action="store_true", help="fake search, no network (harness self-check only)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between live runs (avoids search rate limits)")
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args(argv)
    k = args.k or args.runs
    sys.path.insert(0, str(ROOT.parent))
    cases = [json.loads(l) for l in Path(args.cases).read_text(encoding="utf-8").splitlines() if l.strip()]
    today, results = date.today(), []
    for case in cases:
        runs = []
        for _ in range(args.runs):
            runs.append(run_once(case, args.offline, args.llm, today))
            if not args.offline:
                time.sleep(args.delay)
        c = sum(r["passed"] for r in runs)
        results.append({"id": case["id"], "category": case["category"], "question": case["question"],
                        "n": args.runs, "c": c, "runs": runs})
        print(f"{case['id']} {c}/{args.runs} {case['question'][:60]}", flush=True)
    summary = summarize(results, k)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    mode = "OFFLINE (fake search; self-check, not evidence)" if args.offline else f"LIVE search, model {args.llm}"
    meta = {"date": today.isoformat(), "mode": mode, "runs": args.runs}
    (out / "latest.json").write_text(json.dumps({"meta": meta, "summary": summary, "results": results}, indent=1), encoding="utf-8")
    write_report(out / "RESULTS.md", meta, results, summary, k)
    for name, s in summary.items():
        print(f"{name:12} pass@1={s['pass@1']:.1%}  pass@{k}={s[f'pass@{k}']:.1%}  all-{k}={s[f'all-{k}']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
