from app.adapters.openai_compatible_base import OpenAICompatibleAdapter
from app.config import get_settings

settings = get_settings()


class GroqAdapter(OpenAICompatibleAdapter):
    """Groq hosts open-weight models (Llama 3.1, etc.) on custom inference
    chips - used here for the ':nitro' (speed-optimized) routing demo."""
    name = "groq"
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = settings.GROQ_API_KEY
