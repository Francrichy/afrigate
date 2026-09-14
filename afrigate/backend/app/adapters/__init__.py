from app.adapters.base import BaseAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.deepseek_adapter import DeepSeekAdapter
from app.adapters.qwen_adapter import QwenAdapter
from app.adapters.groq_adapter import GroqAdapter
from app.adapters.cerebras_adapter import CerebrasAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.mistral_adapter import MistralAdapter
from app.adapters.oxalpha_adapter import OxalphaAdapter

# To onboard a new provider: write its adapter class (see base.py), then
# add one line here. Nothing in routers/gateway.py needs to change.
ADAPTER_REGISTRY: dict[str, BaseAdapter] = {
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "deepseek": DeepSeekAdapter(),
    "qwen": QwenAdapter(),
    "groq": GroqAdapter(),
    "cerebras": CerebrasAdapter(),
    "gemini": GeminiAdapter(),
    "mistral": MistralAdapter(),
    "oxalpha": OxalphaAdapter(),
}


def get_adapter(name: str) -> BaseAdapter:
    adapter = ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise KeyError(f"No adapter registered for '{name}'")
    return adapter
