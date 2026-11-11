"""Minimal OpenAI-compatible chat client using only the standard library
(importing `requests` alone cost more startup time than the rest of the app)."""

from __future__ import annotations

import http.client
import json
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

import config


COOLDOWN = 60  # seconds to skip a model that just failed, so a hung one doesn't stall every question


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=None):
        self.base_url = (base_url or config.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or config.LLM_API_KEY
        self.model = model or config.LLM_MODEL
        self.timeout = timeout or config.LLM_TIMEOUT
        self._down_until = 0.0
        host = urlparse(self.base_url).hostname or ""
        # Local servers must not go through a system proxy.
        self._open = urllib.request.build_opener(urllib.request.ProxyHandler({})).open \
            if host in ("localhost", "127.0.0.1", "::1") else urllib.request.urlopen

    def chat(self, messages: list, on_token=None, max_tokens: int | None = None) -> str:
        """Return the reply text. If `on_token` is given the reply is streamed and
        on_token(text_so_far) is called as it grows. Raises LLMError on ANY failure."""
        if time.monotonic() < self._down_until:
            raise LLMError("The model failed a moment ago; using sources only for now.")
        try:
            return self._chat(messages, on_token, max_tokens)
        except LLMError:
            self._down_until = time.monotonic() + COOLDOWN
            raise

    def _chat(self, messages, on_token, max_tokens) -> str:
        body = {"model": self.model, "messages": messages, "temperature": config.LLM_TEMPERATURE,
                "max_tokens": max_tokens or config.LLM_MAX_TOKENS, "stream": bool(on_token)}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        try:
            with self._open(req, timeout=self.timeout) as resp:
                if not on_token:
                    return (json.loads(resp.read())["choices"][0]["message"].get("content") or "").strip()
                text = ""
                for raw in resp:
                    line = raw.decode("utf-8", "ignore").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    delta = json.loads(payload)["choices"][0].get("delta", {}).get("content") or ""
                    if delta:
                        text += delta
                        on_token(text)
                return text.strip()
        except urllib.error.HTTPError as e:
            raise LLMError(f"Model returned HTTP {e.code}: {e.read()[:200]!r}")
        except (socket.timeout, TimeoutError):
            raise LLMError(f"The model did not answer within {self.timeout}s.")
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise LLMError(f"The model did not answer within {self.timeout}s.")
            raise LLMError(f"Cannot reach the model at {self.base_url}. Is Ollama running?")
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"Unexpected model response: {e}")
        except (OSError, http.client.HTTPException) as e:  # connection dropped mid-answer (e.g. Ollama killed for memory)
            raise LLMError(f"The model connection dropped: {e}")
