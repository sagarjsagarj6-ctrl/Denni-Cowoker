"""Ranking behaviour for the knowledge retriever."""

from dynamic_agents.persistence.repositories import Repository


def _chunk(chunk_id: str, text: str, title: str = "") -> dict[str, object]:
    return {"chunk_id": chunk_id, "text": text, "title": title}


def test_exact_phrase_outranks_loose_term_match(repository: Repository) -> None:
    repository.add_knowledge_chunk("c1", None, _chunk("c1", "battery cell thermal limit study"))
    repository.add_knowledge_chunk(
        "c2", None, _chunk("c2", "thermal thermal thermal battery notes without the phrase")
    )

    results = repository.search_knowledge("battery cell thermal limit", None, top_k=2)

    assert [item["chunk_id"] for item in results][0] == "c1"


def test_title_match_is_weighted_above_body_mention(repository: Repository) -> None:
    repository.add_knowledge_chunk("body", None, _chunk("body", "supplier qualification guide"))
    repository.add_knowledge_chunk(
        "title", None, _chunk("title", "unrelated content", title="supplier qualification")
    )

    results = repository.search_knowledge("supplier qualification", None, top_k=2)

    assert results[0]["chunk_id"] == "title"


def test_company_scoped_chunk_outranks_shared_chunk(repository: Repository) -> None:
    repository.add_knowledge_chunk("shared", None, _chunk("shared", "warranty liability terms"))
    repository.add_knowledge_chunk("own", "acme", _chunk("own", "warranty liability terms"))

    results = repository.search_knowledge("warranty liability", "acme", top_k=2)

    assert results[0]["chunk_id"] == "own"


def test_stop_words_and_short_tokens_are_ignored(repository: Repository) -> None:
    repository.add_knowledge_chunk("c1", None, _chunk("c1", "the of and an"))

    assert repository.search_knowledge("the of and an", None) == []


def test_empty_query_returns_no_results(repository: Repository) -> None:
    repository.add_knowledge_chunk("c1", None, _chunk("c1", "some content"))

    assert repository.search_knowledge("", None) == []
