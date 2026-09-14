import httpx
from app.adapters.base import BaseAdapter, NormalizedResponse, AdapterError


class OpenAICompatibleAdapter(BaseAdapter):
    """
    Shared implementation for any provider exposing an OpenAI-compatible
    /chat/completions endpoint (DeepSeek, Qwen/DashScope, Groq, and most
    open-weight model hosts). Subclasses just set url/api_key/name.
    """
    url: str = ""
    api_key: str = ""

    async def chat_completion(self, upstream_model_id, messages, temperature, max_tokens) -> NormalizedResponse:
        if not self.api_key:
            raise AdapterError(f"{self.name} adapter not configured (missing API key).", retryable=False)

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": upstream_model_id,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(self.url, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise AdapterError(f"{self.name} network error: {e}") from e

        if resp.status_code == 429:
            raise AdapterError(f"{self.name} rate limited.", retryable=True)
        if resp.status_code >= 500:
            raise AdapterError(f"{self.name} server error {resp.status_code}.", retryable=True)
        if resp.status_code != 200:
            raise AdapterError(f"{self.name} error {resp.status_code}: {resp.text[:300]}", retryable=False)

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
        """
        Generic implementation for any OpenAI-compatible provider: derives
        GET {base}/models from the same URL used for chat completions.
        Silently returns [] on any failure - see base.py docstring for why.
        """
        if not self.api_key or not self.url.endswith("/chat/completions"):
            return []

        models_url = self.url[: -len("/chat/completions")] + "/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(models_url, headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [m["id"] for m in data.get("data", []) if "id" in m]
        except Exception:
            return []
