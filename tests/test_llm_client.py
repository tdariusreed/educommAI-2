import json

import pytest

from core.llm_client import LLMClient, LLMError


class Resp:
    def __init__(self, body=b"", lines=(), error=None):
        self.body, self.lines, self.error = body, lines, error

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        if self.error:
            raise self.error
        return self.body

    def __iter__(self):
        yield from self.lines
        if self.error:
            raise self.error


def client(resp):
    c = LLMClient(base_url="http://localhost:1/v1")
    c._open = lambda req, timeout: resp
    return c


def test_plain_and_streaming_reply():
    assert client(Resp(json.dumps({"choices": [{"message": {"content": " hi "}}]}).encode())).chat([]) == "hi"
    lines = [b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n', b'data: {"choices":[{"delta":{"content":"lo"}}]}\n', b"data: [DONE]\n"]
    seen = []
    assert client(Resp(lines=lines)).chat([], on_token=seen.append) == "Hello" and seen == ["Hel", "Hello"]


def test_connection_dropped_mid_answer_becomes_llmerror():   # e.g. Ollama killed for memory
    with pytest.raises(LLMError):
        client(Resp(lines=[b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n'], error=ConnectionResetError("reset"))).chat([], on_token=lambda t: None)
    with pytest.raises(LLMError):
        client(Resp(error=ConnectionResetError("reset"))).chat([])


def test_cooldown_skips_a_model_that_just_failed():
    c = client(Resp(error=ConnectionResetError("reset")))
    with pytest.raises(LLMError):
        c.chat([])
    c._open = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not be called during cooldown"))
    with pytest.raises(LLMError, match="a moment ago"):
        c.chat([])


def test_unreachable_server_message():
    with pytest.raises(LLMError, match="Cannot reach"):
        LLMClient(base_url="http://127.0.0.1:1/v1", timeout=2).chat([])
