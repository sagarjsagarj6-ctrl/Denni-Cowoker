"""Permission-aware lexical retrieval reference implementation."""

from dynamic_agents.persistence.repositories import Repository


class KnowledgeRetriever:
    """Retrieve chunks within a company scope."""

    def __init__(self, repository: Repository, top_k: int = 8) -> None:
        self.repository = repository
        self.top_k = top_k

    def search(self, query: str, *, company_id: str | None = None) -> list[dict[str, object]]:
        return self.repository.search_knowledge(query, company_id, self.top_k)
