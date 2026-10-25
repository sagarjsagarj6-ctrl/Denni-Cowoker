"""Optional OpenTelemetry-compatible tracing seam."""

from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def span(name: str) -> Iterator[dict[str, str]]:
    """Yield a lightweight span context without requiring an exporter."""
    yield {"name": name}
