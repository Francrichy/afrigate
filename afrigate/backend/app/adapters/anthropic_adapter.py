import httpx
from app.adapters.base import BaseAdapter, NormalizedResponse, AdapterError
from app.config import get_settings

settings = get_settings()


class AnthropicAdapter(BaseAdapter):
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"
    VERSION = "2023-06-01"

    async def chat_completion(self, upstream_model_id, messages, temperature, max_tokens) -> NormalizedResponse:
        if not settings.ANTHROPIC_API_KEY:
            raise AdapterError("Anthropic adapter not configured (missing ANTHROPIC_API_KEY).", retryable=False)

        system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]

        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": self.VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "model": upstream_model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_text:
            payload["system"] = system_text

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(self.URL, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise AdapterError(f"Anthropic network error: {e}") from e

        if resp.status_code == 429:
            raise AdapterError("Anthropic rate limited.", retryable=True)
        if resp.status_code >= 500:
            raise AdapterError(f"Anthropic server error {resp.status_code}.", retryable=True)
        if resp.status_code != 200:
            raise AdapterError(f"Anthropic error {resp.status_code}: {resp.text[:300]}", retryable=False)

        data = resp.json()
        content = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        return NormalizedResponse(
            content=content,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            finish_reason=data.get("stop_reason", "stop"),
        )

    async def list_upstream_models(self) -> list[str]:
        """Anthropic exposes a real GET /v1/models list (verified against
        their docs) - different auth header shape than the OpenAI-compatible
        providers, so this can't reuse the generic helper."""
        if not settings.ANTHROPIC_API_KEY:
            return []
        headers = {"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": self.VERSION}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get("https://api.anthropic.com/v1/models", headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [m["id"] for m in data.get("data", []) if "id" in m]
        except Exception:
            return []
