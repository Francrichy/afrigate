from app.config import get_settings
from app.adapters.openai_compatible_base import OpenAICompatibleAdapter

settings = get_settings()


class GeminiAdapter(OpenAICompatibleAdapter):
    """
    Google exposes Gemini through a native API and also an OpenAI-compatible
    surface at generativelanguage.googleapis.com/v1beta/openai - this lets
    us reuse the exact same adapter base class as every other provider.
    """
    name = "Gemini"
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    api_key = settings.GEMINI_API_KEY
