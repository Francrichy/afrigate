from app.config import get_settings
from app.adapters.openai_compatible_base import OpenAICompatibleAdapter

settings = get_settings()


class MistralAdapter(OpenAICompatibleAdapter):
    name = "Mistral"
    url = "https://api.mistral.ai/v1/chat/completions"
    api_key = settings.MISTRAL_API_KEY
