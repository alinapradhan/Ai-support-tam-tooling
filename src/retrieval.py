"""
Lightweight retrieval over the knowledge-base markdown corpus.

Uses BM25 (rank_bm25) rather than embeddings: the KB is small (a handful of docs),
so a full embedding + vector-DB stack would be overkill and adds latency/cost for
no real quality gain at this corpus size. This is documented as a deliberate
latency-vs-complexity trade-off in DESIGN.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

KB_ROOT = Path(__file__).resolve().parent.parent / "knowledge-base"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class KBDoc:
    path: str          # relative path, e.g. "products/databridge-pro.md"
    title: str          # first H1 in the doc
    text: str
    chunks: list[str]   # split by ## sections for finer-grained matching


def _load_docs() -> list[KBDoc]:
    docs = []
    for path in sorted(KB_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        chunks = re.split(r"\n##\s+", text)
        rel = str(path.relative_to(KB_ROOT))
        docs.append(KBDoc(path=rel, title=title, text=text, chunks=chunks))
    return docs


class KnowledgeBase:
    def __init__(self):
        self.docs = _load_docs()
        self._corpus_tokens = [_tokenize(d.text) for d in self.docs]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None

    def search(self, query: str, top_k: int = 2, min_score: float = 0.5) -> list[KBDoc]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in ranked[:top_k] if score >= min_score]

    def as_prompt_context(self, docs: list[KBDoc]) -> str:
        parts = []
        for d in docs:
            snippet = d.text[:1200]
            parts.append(f"### {d.title} ({d.path})\n{snippet}")
        return "\n\n".join(parts)


_kb_singleton: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb_singleton
    if _kb_singleton is None:
        _kb_singleton = KnowledgeBase()
    return _kb_singleton
