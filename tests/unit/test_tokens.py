import pytest

from dynamic_agents.core.errors import NotFoundError
from dynamic_agents.persistence.tokens import TokenManager


def test_resume_token_is_opaque_and_server_side(repository) -> None:
    manager = TokenManager(repository)
    raw = manager.issue("snap_123")
    assert raw != repository.get_token_by_hash(manager._hash(raw)).token_hash
    assert manager.resolve(raw).snapshot_id == "snap_123"
    with pytest.raises(NotFoundError):
        manager.resolve("not-a-token")
