"""Knowledge store over trusted documents in data/knowledge/.

Right now this is lexical (TF-IDF-style) search using only the standard library, so it runs
anywhere. The interface (`search(query, k)`) is what the rest of the app uses, so you can swap
in Chroma/FAISS embeddings later without touching any agent.

Document format (markdown or text), optional header:
    ---
    source: https://studentaid.gov/...
    title: Federal Student Aid basics
    ---
    body text...
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

_STOP = set("a an and are as at be by for from has have how i in is it its of on or that the this to was what when where which who will with you your can do my me".split())


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1]


def _parse(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    meta = {}
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            raw = parts[2]
    return meta, raw


class KnowledgeStore:
    def __init__(self, directory: Path | None = None, chunk_chars: int = 800):
        self.chunks: list[dict] = []
        self._df: Counter = Counter()
        if directory and Path(directory).exists():
            for path in sorted(Path(directory).glob("**/*")):
                if path.suffix.lower() in (".md", ".txt") and not path.name.lower().startswith("readme"):
                    self._add_document(path, chunk_chars)
        for chunk in self.chunks:
            self._df.update(chunk["tf"])

    def _add_document(self, path: Path, chunk_chars: int) -> None:
        meta, body = _parse(path)
        source = meta.get("source", "")
        title = meta.get("title", path.stem)
        buf = ""
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if not para:
                continue
            if buf and len(buf) + len(para) > chunk_chars:
                self._add_chunk(buf, title, source)
                buf = ""
            buf = f"{buf}\n\n{para}".strip()
        if buf:
            self._add_chunk(buf, title, source)

    def _add_chunk(self, text: str, title: str, source: str) -> None:
        self.chunks.append({"text": text, "title": title, "source": source, "tf": Counter(_tokens(text))})

    @staticmethod
    def has_documents(directory) -> bool:
        """Cheap check so we never build an index (or hold it in memory) when there is nothing to index."""
        d = Path(directory)
        return d.exists() and any(p.suffix.lower() in (".md", ".txt") and not p.name.lower().startswith("readme")
                                  for p in d.glob("**/*"))

    def __len__(self) -> int:
        return len(self.chunks)

    def search(self, query: str, k: int = 3) -> list[dict]:
        q = _tokens(query)
        if not q or not self.chunks:
            return []
        n = len(self.chunks)
        scored = []
        for chunk in self.chunks:
            tf = chunk["tf"]
            score = sum((1 + math.log(tf[t])) * math.log(1 + n / (1 + self._df[t])) for t in q if tf[t])
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda s: s[0], reverse=True)
        return [{"title": c["title"], "url": c["source"], "text": c["text"][:700]} for _, c in scored[:k]]
