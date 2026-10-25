"""Ingest local company documents into the repository."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from dynamic_agents.config.settings import Settings
from dynamic_agents.input.normalizer import InputNormalizer
from dynamic_agents.knowledge.chunking import chunk_text
from dynamic_agents.models.domain import InputEnvelope, InputFile
from dynamic_agents.persistence.repositories import Repository


class KnowledgeIngestor:
    """Parse, chunk, and persist evidence with source metadata."""

    def __init__(self, settings: Settings, repository: Repository) -> None:
        self.settings = settings
        self.repository = repository
        self.normalizer = InputNormalizer(settings)

    def ingest(self, directory: str, company_id: str | None = None) -> int:
        root = Path(directory).resolve()
        files = [path for path in root.rglob("*") if path.is_file()]
        count = 0
        for path in files:
            normalized = self.normalizer.normalize(
                InputEnvelope(
                    request_id=f"req_ingest_{uuid4().hex}", files=[InputFile(path=str(path))]
                )
            )
            for evidence in normalized.evidence:
                for index, text in enumerate(chunk_text(evidence.extracted_text)):
                    chunk_id = f"chunk_{uuid4().hex[:12]}"
                    self.repository.add_knowledge_chunk(
                        chunk_id,
                        company_id,
                        {
                            "chunk_id": chunk_id,
                            "text": text,
                            "source_name": evidence.source_name,
                            "evidence_id": evidence.evidence_id,
                            "chunk_index": index,
                            "checksum_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        },
                    )
                    count += 1
        return count
