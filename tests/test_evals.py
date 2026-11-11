import json
from pathlib import Path
from types import SimpleNamespace

from core.tracing import Trace
from evals import run_evals as ev

CASES = [json.loads(l) for l in (Path(ev.ROOT) / "cases.jsonl").read_text().splitlines() if l.strip()]


def test_pass_at_k_math():
    assert ev.pass_at_k(3, 0, 3) == 0.0 and ev.pass_at_k(3, 3, 3) == 1.0 and ev.pass_at_k(3, 1, 3) == 1.0
    assert ev.pass_at_k(3, 1, 1) == 1 - 2 / 3          # = c/n when k=1
    assert abs(ev.pass_at_k(5, 2, 2) - (1 - 3 / 10)) < 1e-9


def test_case_file_meets_the_assignment_minimums():
    assert len(CASES) >= 10 and sum(c["category"] == "adversarial" for c in CASES) >= 2
    assert len({c["id"] for c in CASES}) == len(CASES) and all(c["checks"] for c in CASES)
    assert all(name in ev.CHECKS for c in CASES for name in c["checks"])


def _turn(**kw):
    t = Trace()
    t.add("search", "programs", query="Atlanta history summer programs")
    base = dict(answer="", sources=[], agents_used=[], blocked=False, needs_input=False, action="", offer_quiz=False, ics="", trace=t)
    return SimpleNamespace(**{**base, **kw})


def test_checks_can_actually_fail():
    """A harness that cannot fail proves nothing: each check must reject a bad turn."""
    bad = {
        "agents_include": (_turn(), ["plan"]), "answer_contains_any": (_turn(answer="x"), ["988"]),
        "answer_excludes": (_turn(answer="call 404-555-1234"), ["404-555-1234"]), "blocked": (_turn(), True),
        "needs_input": (_turn(), True), "action": (_turn(), "quiz"), "offer_quiz": (_turn(), True), "has_ics": (_turn(), True),
        "min_sources": (_turn(), 1), "max_sources": (_turn(sources=["u"]), 0),
        "only_cited_urls": (_turn(answer="see http://fake.example/x", sources=["https://real.org"]), True),
        "no_invented_dates": (_turn(answer="Apply by March 1, 2027."), True), "queries_include": (_turn(), ["art"]),
    }
    assert set(bad) == set(ev.CHECKS)
    for name, (turn, expected) in bad.items():
        assert not ev.CHECKS[name](turn, expected), name
    assert ev.CHECKS["only_cited_urls"](_turn(answer="[1](https://real.org/a).", sources=["https://real.org/a"]), True)


def test_offline_harness_end_to_end(tmp_path):
    assert ev.main(["--offline", "--runs", "3", "--out", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "latest.json").read_text())
    assert len(data["results"]) == len(CASES) and all(r["n"] == 3 for r in data["results"])
    assert data["summary"]["adversarial"]["pass@1"] == 1.0          # safety rules hold offline too
    assert "pass@1" in (tmp_path / "RESULTS.md").read_text()
