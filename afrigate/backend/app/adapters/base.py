"""
The Adapter Pattern that makes AfriGate's "add a new provider without
touching the gateway" promise real. Every provider adapter implements
the same `chat_completion()` signature and returns the same normalized
shape, regardless of how different the upstream API actually looks.

To onboard a brand-new AI provider: write ONE new file in this folder
implementing BaseAdapter, then register it in ADAPTER_REGISTRY at the
bottom of __init__.py. Nothing in routers/gateway.py ever changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NormalizedResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str = "stop"


class AdapterError(Exception):
    """Raised for any upstream failure - network, auth, rate limit, etc.
    The gateway catches this uniformly for fallback routing, regardless
    of which provider raised it."""
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class BaseAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def chat_completion(
        self,
        upstream_model_id: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> NormalizedResponse:
        """Send the request upstream and return a NormalizedResponse.
        Must raise AdapterError (not a raw exception) on any failure so
        the gateway's fallback loop can react uniformly."""
        raise NotImplementedError

    async def list_upstream_models(self) -> list[str]:
        """
        Returns the provider's own list of currently-available model ids.
        Used ONLY by the daily model-discovery job (utils/model_discovery.py)
        to detect new releases - never used on the hot request path.

        Default: not supported. Override in a subclass if the provider
        exposes a real models-list endpoint. Must NEVER raise - the
        discovery job treats an empty list as "nothing to report" rather
        than crashing the whole scan over one provider's outage.
        """
        return []
