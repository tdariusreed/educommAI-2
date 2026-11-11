import config
from core import verifier, writer
from core.models import Profile
from tools.search_tool import make_search
from tools.source_ranker import rank_results
from tests.conftest import FAKE, GOOD, JOB, FakeLLM


def test_ranker_puts_official_sources_first():
    ranked = rank_results([{"url": "https://www.indeed.com/jobs"}, {"url": "https://example.com/blog"},
                           {"url": "https://www.bls.gov/ooh/"}, {"url": "https://someschool.edu/y"}])
    assert [r["quality"] for r in ranked] == ["high", "high", "medium", "low"]


def test_search_ranks_limits_and_caches(monkeypatch):
    monkeypatch.setattr(config, "RESULTS_PER_QUERY", 2)
    calls = []

    def backend(q, n):
        calls.append(q)
        return [{"title": "a", "href": "https://indeed.com/1"}, {"title": "b", "href": "https://bls.gov/2"},
                {"title": "c", "href": "https://x.com/3"}, {"href": None}]
    search = make_search(backend)
    out = search("Q one")
    assert [r["url"] for r in out] == ["https://bls.gov/2", "https://x.com/3"]
    search("q ONE ")          # same query, different case/spacing
    assert len(calls) == 1    # served from the cache


def test_search_retries_once_then_raises():
    calls = []

    def flaky(q, n):
        calls.append(1)
        raise ConnectionError("boom")
    try:
        make_search(flaky, retry_delay=0)("q")
        assert False
    except RuntimeError as e:
        assert "search failed" in str(e) and len(calls) == 2


EVIDENCE = [{"n": 1, "url": GOOD, "title": "BLS", "snippet": "s", "quality": "high", "specialists": {"career_explorer"}},
            {"n": 2, "url": JOB, "title": "Jobs", "snippet": "s", "quality": "low", "specialists": {"career_explorer"}}]


def test_verifier_turns_numbers_into_real_links_and_drops_invented_ones():
    text, cited, issues = verifier.finalize(f"Fact [1]. Other [1, 2]. Ghost [9]. Bad [x]({FAKE}) and {FAKE}", EVIDENCE)
    assert f"[1]({GOOD})" in text and f"[2]({JOB})" in text and FAKE not in text and "[9]" not in text
    assert cited == [GOOD, JOB] and len(issues) == 2


def test_verifier_cautions_when_nothing_is_cited():
    text, cited, issues = verifier.finalize("No citations here.", EVIDENCE)
    assert cited == [] and "double-check" in text and "no cited source" in issues


def test_writer_prompt_has_numbered_sources_tips_and_injection_guard():
    msgs = writer.build_messages(Profile(grade=10, interests=["math"]), "q", ["career_explorer", "next_steps"], EVIDENCE)
    assert "[1] (high) BLS" in msgs[1]["content"] and "GENERAL TIPS" in msgs[1]["content"]
    assert "never instructions" in msgs[0]["content"]


def test_writer_extractive_fallbacks():
    p = Profile(grade=7, interests=["art"])
    text, used = writer.write(None, p, "q", ["career_explorer", "next_steps"], EVIDENCE)
    assert not used and "[1]" in text and "Your next steps" in text
    text, used = writer.write(FakeLLM(error=RuntimeError("anything at all")), p, "q", ["career_explorer"], EVIDENCE)
    assert not used and "[1]" in text            # ANY model failure still yields an answer
    text, used = writer.write(FakeLLM(), p, "q", ["career_explorer", "next_steps"], [])
    assert not used and "couldn't find reliable sources" in text and "Your next steps" in text
