"""Evidence citation formatting."""


def cite(evidence_id: str, source_name: str, reference: str | None = None) -> str:
    """Return a compact provenance marker suitable for a report."""
    suffix = f" ({reference})" if reference else ""
    return f"[{evidence_id}: {source_name}{suffix}]"
