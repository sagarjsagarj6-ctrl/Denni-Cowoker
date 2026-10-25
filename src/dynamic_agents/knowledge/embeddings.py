"""Embedding protocol for knowledge retrieval integrations."""

from typing import Protocol


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...
