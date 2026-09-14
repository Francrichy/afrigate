import httpx
from app.adapters.base import BaseAdapter, NormalizedResponse, AdapterError
from app.config import get_settings

settings = get_settings()


class OpenAIAdapter(BaseAdapter):
    name = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    async def chat_completion(self, upstream_model_id, messages, temperature, max_tokens) -> NormalizedResponse:
        if not settings.OPENAI_API_KEY:
            raise AdapterError("OpenAI adapter not configured (missing OPENAI_API_KEY).", retryable=False)

        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": upstream_model_id,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(self.URL, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise AdapterError(f"OpenAI network error: {e}") from e

        if resp.status_code == 429:
            raise AdapterError("OpenAI rate limited.", retryable=True)
        if resp.status_code >= 500:
            raise AdapterError(f"OpenAI server error {resp.status_code}.", retryable=True)
        if resp.status_code != 200:
            raise AdapterError(f"OpenAI error {resp.status_code}: {resp.text[:300]}", retryable=False)

        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return NormalizedResponse(
            content=choice["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def list_upstream_models(self) -> list[str]:
        """OpenAI exposes a real GET /v1/models list - this is what lets
        the daily discovery job notice a new release (e.g. a future
        'gpt-6') automatically instead of you having to watch their blog."""
        if not settings.OPENAI_API_KEY:
            return []
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get("https://api.openai.com/v1/models", headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [m["id"] for m in data.get("data", []) if "id" in m]
        except Exception:
            return []
