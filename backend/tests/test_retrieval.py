from app.agent.rag import KnowledgeBase
from app.config import get_settings


def test_knowledge_base_indexes_sample_transcripts():
    kb = KnowledgeBase(get_settings())
    assert kb.size > 0


def test_search_returns_relevant_chunk_for_activation_query():
    kb = KnowledgeBase(get_settings())
    results = kb.search("what is a good activation metric", top_k=3)
    assert len(results) > 0
    assert any("activation" in r.chunk.text.lower() for r in results)


def test_search_on_unrelated_query_returns_low_or_no_relevance():
    kb = KnowledgeBase(get_settings())
    results = kb.search("what is the airspeed velocity of an unladen swallow", top_k=3)
    # Either nothing relevant, or scores are low enough to be filtered by MIN_RELEVANCE upstream
    if results:
        assert all(r.score < 0.3 for r in results)


def test_chunking_respects_configured_size():
    from app.ingestion.loader import chunk_text

    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size_words=200, overlap_words=20)
    assert len(chunks) >= 2
    assert all(len(c.split()) <= 200 for c in chunks)
