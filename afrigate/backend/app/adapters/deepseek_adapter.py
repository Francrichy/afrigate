from app.adapters.openai_compatible_base import OpenAICompatibleAdapter
from app.config import get_settings

settings = get_settings()


class DeepSeekAdapter(OpenAICompatibleAdapter):
    name = "deepseek"
    url = "https://api.deepseek.com/chat/completions"
    api_key = settings.DEEPSEEK_API_KEY
