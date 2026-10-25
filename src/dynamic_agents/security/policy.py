"""Request-level security policy."""

from urllib.parse import urlparse

from dynamic_agents.config.settings import Settings
from dynamic_agents.core.errors import PolicyViolation


class SecurityPolicy:
    """Centralize allowlist checks for network and untrusted input."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in self.settings.allowed_domains:
            raise PolicyViolation("URL is not HTTPS or not present in ALLOWED_HTTP_DOMAINS")
