from app.config import get_settings
from app.adapters.openai_compatible_base import OpenAICompatibleAdapter

settings = get_settings()


class OxalphaAdapter(OpenAICompatibleAdapter):
    """Free tier via TokenRa (tokenra.io) - verified endpoint/model id
    during the SwahiliBot build in this same workspace."""
    name = "Oxalpha"
    url = f"{settings.OXALPHA_BASE_URL.rstrip('/')}/chat/completions"
    api_key = settings.OXALPHA_API_KEY
