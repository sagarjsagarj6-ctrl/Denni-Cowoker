"""Opaque, server-side resume token management."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dynamic_agents.core.errors import NotFoundError
from dynamic_agents.models.domain import ResumeTokenRecord
from dynamic_agents.persistence.repositories import Repository


class TokenManager:
    """Issue random bearer tokens while persisting only a one-way hash."""

    def __init__(self, repository: Repository, ttl_days: int = 90) -> None:
        self.repository = repository
        self.ttl_days = ttl_days

    def issue(self, snapshot_id: str) -> str:
        raw = secrets.token_urlsafe(32)
        record = ResumeTokenRecord(
            token_id=f"tok_{uuid4().hex}",
            token_hash=self._hash(raw),
            snapshot_id=snapshot_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.ttl_days),
        )
        self.repository.save_token(record)
        return raw

    def resolve(self, raw: str) -> ResumeTokenRecord:
        record = self.repository.get_token_by_hash(self._hash(raw))
        if not record or record.revoked:
            raise NotFoundError("resume token is invalid or revoked")
        if record.expires_at and record.expires_at < datetime.now(timezone.utc):
            raise NotFoundError("resume token has expired")
        return record

    @staticmethod
    def _hash(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
