"""Convenience constructors for request envelopes."""

from uuid import uuid4

from dynamic_agents.models.domain import InputEnvelope, InputFile


def make_envelope(
    text: str = "",
    files: list[str] | None = None,
    company_id: str | None = None,
    case_id: str | None = None,
    **metadata: object,
) -> InputEnvelope:
    """Create an envelope with a fresh request ID."""
    return InputEnvelope(
        request_id=f"req_{uuid4().hex}",
        text=text,
        files=[InputFile(path=path) for path in files or []],
        company_id=company_id,
        case_id=case_id,
        metadata=metadata,
    )
