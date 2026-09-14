from app.adapters.openai_compatible_base import OpenAICompatibleAdapter
from app.config import get_settings

settings = get_settings()


class QwenAdapter(OpenAICompatibleAdapter):
    name = "qwen"
    url = f"{settings.QWEN_BASE_URL.rstrip('/')}/chat/completions"
    api_key = settings.QWEN_API_KEY
