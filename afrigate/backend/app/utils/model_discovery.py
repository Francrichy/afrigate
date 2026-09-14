"""
Daily model-discovery job. For each registered adapter that supports
`list_upstream_models()`, fetch what the provider currently offers and
compare against what AfriGate already knows about (by adapter +
upstream_model_id). Anything new gets a ModelSuggestion row with a short,
plain-language note - so a non-technical admin sees "here's a new model,
here's roughly what it might be for" on the dashboard instead of having
to read provider changelogs themselves.

This module NEVER touches the live gateway or a user's wallet - it only
writes to `model_suggestions`, which is purely advisory until an admin
acts on it via /api/admin/models.
"""
import logging

from sqlalchemy.orm import Session

from app.adapters import ADAPTER_REGISTRY
from app.models import ModelRegistryEntry, ModelSuggestion
from app.adapters.base import AdapterError

logger = logging.getLogger("model_discovery")

# A tiny, dependency-free heuristic so this works even with zero AI provider
# keys configured (the note is still useful, just less specific). If a cheap
# adapter IS configured, we upgrade to a one-sentence AI-written note below.
_FAMILY_HINTS = {
    "openai": "Likely a GPT-family update from OpenAI - check platform.openai.com/docs/models for context window and pricing before adding.",
    "anthropic": "Likely a new Claude model - check platform.claude.com/docs for its tier (Haiku/Sonnet/Opus) and pricing before adding.",
    "gemini": "Likely a new Gemini release from Google - check ai.google.dev/gemini-api/docs/models for free-tier eligibility.",
    "mistral": "Likely a new Mistral model - check mistral.ai/products for whether it's a 'Small' (cheap) or 'Large' (professional) release.",
    "deepseek": "Likely a DeepSeek update - these are almost always very cheap; consider the 'cheap' tier.",
    "qwen": "Likely a new Qwen release from Alibaba - typically cheap-tier pricing.",
    "groq": "Groq hosts open-weight models (Llama, etc.) at very high speed - often free-tier eligible.",
    "cerebras": "Cerebras hosts open-weight models with a generous free daily quota - check if it qualifies for the free tier.",
    "oxalpha": "A new Oxalpha release - these are free-tier by nature.",
}


async def _write_suggestion_note(adapter_name: str, upstream_model_id: str) -> str:
    """
    Tries to get a one-sentence recommendation from one of OUR OWN cheap/free
    gateway models (self-referential: AfriGate uses AfriGate to advise on
    AfriGate). Falls back to the static hint above if no provider is
    configured or the call fails - this function must never raise.
    """
    fallback = _FAMILY_HINTS.get(adapter_name, "New model detected - review its official pricing page before adding.")

    for advisor_adapter_name in ("groq", "cerebras", "deepseek"):
        adapter = ADAPTER_REGISTRY.get(advisor_adapter_name)
        if not adapter:
            continue
        try:
            prompt = (
                f"A new AI model was just detected: '{upstream_model_id}' from provider '{adapter_name}'. "
                f"In ONE short sentence, guess what kind of model this likely is (flagship/mid/small, "
                f"reasoning-focused, etc.) from its name, and suggest whether it probably belongs in a "
                f"'free', 'cheap', or 'professional' pricing tier. Be concise, no preamble."
            )
            # upstream_model_id used as the model id only works if this
            # advisor adapter also serves general chat models - use a
            # reasonable default id per advisor rather than the new model.
            advisor_model_id = {
                "groq": "llama-3.1-8b-instant",
                "cerebras": "llama3.1-8b",
                "deepseek": "deepseek-chat",
            }[advisor_adapter_name]
            result = await adapter.chat_completion(advisor_model_id, [{"role": "user", "content": prompt}], 0.3, 120)
            note = result.content.strip()
            if note:
                return note
        except AdapterError:
            continue
        except Exception:
            continue

    return fallback


async def discover_new_models(db: Session) -> int:
    """Runs one full discovery pass. Returns the number of NEW suggestions written."""
    known = {
        (row.adapter, row.upstream_model_id)
        for row in db.query(ModelRegistryEntry.adapter, ModelRegistryEntry.upstream_model_id).all()
    }
    already_suggested = {
        (row.adapter, row.upstream_model_id)
        for row in db.query(ModelSuggestion.adapter, ModelSuggestion.upstream_model_id).all()
    }

    new_count = 0
    for adapter_name, adapter in ADAPTER_REGISTRY.items():
        try:
            upstream_ids = await adapter.list_upstream_models()
        except Exception as e:
            logger.warning("Discovery skipped for '%s' (list_upstream_models failed): %s", adapter_name, e)
            continue

        for upstream_id in upstream_ids:
            key = (adapter_name, upstream_id)
            if key in known or key in already_suggested:
                continue

            note = await _write_suggestion_note(adapter_name, upstream_id)
            db.add(ModelSuggestion(adapter=adapter_name, upstream_model_id=upstream_id, suggestion_note=note))
            already_suggested.add(key)
            new_count += 1

    if new_count:
        db.commit()
        logger.info("Model discovery: %d new suggestion(s) recorded.", new_count)
    return new_count
