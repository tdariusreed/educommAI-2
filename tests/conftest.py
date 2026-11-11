from datetime import date

import pytest

from core.assistant import Assistant

GOOD = "https://www.bls.gov/ooh/business-and-financial/financial-analysts.htm"
JOB = "https://www.indeed.com/q-finance-intern-jobs.html"
FAKE = "https://made-up.example.com/invented"


SCHOLAR = "https://gafutures.org/scholarship-example"


def results_for(query, dated=True):
    # already ranked best-first, as the real search() returns them
    out = [{"title": "Financial Analysts", "url": GOOD, "snippet": "Analysts study markets.", "text": "Analysts study markets.", "quality": "high"},
           {"title": "Finance internships", "url": JOB, "snippet": "listings", "text": "listings", "quality": "low"}]
    if "scholarship" in query:
        text = "Open to Georgia juniors." + (" The application deadline is March 1, 2027. Awards vary." if dated else " Awards vary.")
        out.insert(0, {"title": "Example Scholarship", "url": SCHOLAR, "snippet": text[:60], "text": text, "quality": "high"})
    return out


class FakeSearch:
    def __init__(self, fail=False, dated=True):
        self.queries, self.fail, self.dated = [], fail, dated

    def __call__(self, query):
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("search failed: offline")
        return results_for(query, self.dated)


class FakeLLM:
    """Stands in for LLMClient. One .chat() call per question is the whole point."""

    def __init__(self, text=None, error=None):
        self.calls, self.text, self.error, self.max_tokens = [], text, error, []

    def chat(self, messages, on_token=None, max_tokens=None):
        self.calls.append(messages)
        self.max_tokens.append(max_tokens)
        if self.error:
            raise self.error
        return self.text if self.text is not None else "Financial analysts study markets [1]."


@pytest.fixture
def make(tmp_path):
    def _make(llm=None, search=None, mode="auto", today=date(2026, 11, 9)):
        return Assistant(llm=llm, search=search or FakeSearch(), db_path=tmp_path / "t.db",
                         knowledge_dir=tmp_path / "none", mode=mode, today=lambda: today)
    return _make
