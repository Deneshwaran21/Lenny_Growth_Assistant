"""
Retrieval layer.

Backend default is TF-IDF cosine similarity (scikit-learn) so the demo has
zero external embedding-model dependency and works fully offline. Set
EMBEDDING_BACKEND=sentence-transformers to swap in dense embeddings
(all-MiniLM-L6-v2) without touching any router or agent code — this class
is the only integration point (see architecture.md#retrieval).
"""
from __future__ import annotations

import logging
import threading

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import Settings
from app.ingestion.loader import Chunk, build_chunks, load_transcripts

logger = logging.getLogger("lenny.rag")


class RetrievalResult:
    def __init__(self, chunk: Chunk, score: float):
        self.chunk = chunk
        self.score = score


class KnowledgeBase:
    """In-memory TF-IDF index over transcript chunks.

    Thread-safe singleton built once at startup and rebuilt on demand via
    POST /api/kb/refresh (see routers/health.py) to simulate periodic
    transcript refresh without a restart.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self.chunks: list[Chunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self.refresh()

    def refresh(self) -> int:
        with self._lock:
            docs = load_transcripts(self.settings.TRANSCRIPTS_DIR)
            self.chunks = build_chunks(
                docs, self.settings.CHUNK_SIZE_WORDS, self.settings.CHUNK_OVERLAP_WORDS
            )
            if self.chunks:
                self._vectorizer = TfidfVectorizer(stop_words="english")
                self._matrix = self._vectorizer.fit_transform(
                    [c.text for c in self.chunks]
                )
            else:
                self._vectorizer = None
                self._matrix = None
            logger.info("Knowledge base refreshed: %d chunks indexed", len(self.chunks))
            return len(self.chunks)

    @property
    def size(self) -> int:
        return len(self.chunks)

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        if not self.chunks or self._vectorizer is None:
            return []
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(
            zip(self.chunks, sims, strict=True), key=lambda pair: pair[1], reverse=True
        )
        results = [
            RetrievalResult(chunk, float(score))
            for chunk, score in ranked[:top_k]
            if score > 0.0
        ]
        return results


_kb_instance: KnowledgeBase | None = None
_kb_lock = threading.Lock()


def get_knowledge_base(settings: Settings) -> KnowledgeBase:
    global _kb_instance
    with _kb_lock:
        if _kb_instance is None:
            _kb_instance = KnowledgeBase(settings)
        return _kb_instance
