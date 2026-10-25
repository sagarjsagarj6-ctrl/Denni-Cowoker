"""Secret-safe log and response redaction."""

import re

SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]+"),
]


def redact(value: str) -> str:
    """Redact common credential forms without changing normal content."""
    result = value
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(
            lambda match: f"{match.group(1) if match.lastindex else ''}[REDACTED]", result
        )
    return result
