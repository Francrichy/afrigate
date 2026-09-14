from app.config import get_settings
from app.adapters.openai_compatible_base import OpenAICompatibleAdapter

settings = get_settings()


class CerebrasAdapter(OpenAICompatibleAdapter):
    name = "Cerebras"
    url = "https://api.cerebras.ai/v1/chat/completions"
    api_key = settings.CEREBRAS_API_KEY
