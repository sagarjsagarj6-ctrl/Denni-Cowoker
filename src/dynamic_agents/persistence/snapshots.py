"""Snapshot helpers."""

from dynamic_agents.models.domain import TeamSnapshot
from dynamic_agents.persistence.repositories import Repository


class SnapshotRepository:
    """Named adapter useful for swapping SQLite for a production object store."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def save(self, snapshot: TeamSnapshot) -> None:
        self.repository.save_snapshot(snapshot)

    def get(self, snapshot_id: str) -> TeamSnapshot | None:
        return self.repository.get_snapshot(snapshot_id)
