"""
Transcript ingestion: load -> parse frontmatter -> chunk -> trace back to source.

See architecture.md#ingestion-flow for the full diagram. In this take-home,
transcripts live as local Markdown files with YAML frontmatter
(episode_title, guest, episode_id, source_url) under `app/data/transcripts/`.
This mirrors how a production version would pull from Lenny's transcript
repository / newsletter export — swapping this loader for one that pulls
from a real repo or API is the only change needed (see README "Refreshing
the knowledge base").
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger("lenny.ingestion")

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class TranscriptDoc:
    transcript_id: str
    episode_title: str
    source_url: str
    text: str
    path: str


@dataclass
class Chunk:
    chunk_id: str
    transcript_id: str
    episode_title: str
    source_url: str
    text: str
    order: int
    metadata: dict = field(default_factory=dict)


def load_transcripts(transcripts_dir: str) -> list[TranscriptDoc]:
    docs: list[TranscriptDoc] = []
    base = Path(transcripts_dir)
    if not base.exists():
        logger.warning("Transcripts directory %s does not exist", transcripts_dir)
        return docs

    for path in sorted(base.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(raw)
        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            body = match.group(2).strip()
        else:
            meta = {}
            body = raw.strip()

        transcript_id = meta.get("episode_id", path.stem)
        docs.append(
            TranscriptDoc(
                transcript_id=transcript_id,
                episode_title=meta.get("episode_title", path.stem),
                source_url=meta.get("source_url", ""),
                text=body,
                path=str(path),
            )
        )
    logger.info("Loaded %d transcripts from %s", len(docs), transcripts_dir)
    return docs


def chunk_text(text: str, chunk_size_words: int, overlap_words: int) -> list[str]:
    """Simple sliding-window word chunker. Good enough for podcast-length
    transcripts and keeps the demo dependency-free (no tokenizer needed)."""
    words = text.split()
    if not words:
        return []
    step = max(chunk_size_words - overlap_words, 1)
    chunks = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size_words]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_size_words >= len(words):
            break
    return chunks


def build_chunks(
    docs: list[TranscriptDoc], chunk_size_words: int, overlap_words: int
) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for doc in docs:
        pieces = chunk_text(doc.text, chunk_size_words, overlap_words)
        for i, piece in enumerate(pieces):
            all_chunks.append(
                Chunk(
                    chunk_id=f"{doc.transcript_id}::chunk-{i}",
                    transcript_id=doc.transcript_id,
                    episode_title=doc.episode_title,
                    source_url=doc.source_url,
                    text=piece,
                    order=i,
                )
            )
    logger.info("Built %d chunks from %d transcripts", len(all_chunks), len(docs))
    return all_chunks
