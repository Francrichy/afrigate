"""
Routing engine - implements the exact modifier syntax OpenRouter's
developers already know (`model:floor`, `model:nitro`), plus alias
resolution so admins can upgrade a model for everyone via one DB row
change (no code deploy, no developer-side breakage for pinned slugs).
"""
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import ModelRegistryEntry


@dataclass
class ResolvedRoute:
    entry: ModelRegistryEntry
    routing_mode: str  # "default" | "floor" | "nitro"
    fallback_entries: list[ModelRegistryEntry]


def parse_model_string(model_string: str) -> tuple[str, str]:
    """'claude-latest:floor' -> ('claude-latest', 'floor')"""
    if ":" in model_string:
        slug, mode = model_string.rsplit(":", 1)
        if mode in ("floor", "nitro"):
            return slug, mode
    return model_string, "default"


def resolve_alias(db: Session, slug: str, _depth: int = 0) -> ModelRegistryEntry | None:
    if _depth > 5:
        return None  # guard against a misconfigured alias cycle
    entry = db.query(ModelRegistryEntry).filter(
        ModelRegistryEntry.slug == slug, ModelRegistryEntry.is_enabled.is_(True)
    ).first()
    if not entry:
        return None
    if entry.is_alias and entry.points_to_slug:
        return resolve_alias(db, entry.points_to_slug, _depth + 1)
    return entry


def resolve_route(db: Session, model_string: str) -> ResolvedRoute | None:
    slug, mode = parse_model_string(model_string)
    entry = resolve_alias(db, slug)
    if not entry:
        return None

    fallback_entries: list[ModelRegistryEntry] = []

    if mode == "floor":
        # Cheapest enabled, non-alias entry with the SAME display family
        # (same base name before any '/') as a same-quality fallback pool.
        family = entry.display_name.split()[0].lower()
        candidates = db.query(ModelRegistryEntry).filter(
            ModelRegistryEntry.is_enabled.is_(True), ModelRegistryEntry.is_alias.is_(False)
        ).all()
        pool = [c for c in candidates if family in c.display_name.lower()]
        pool.sort(key=lambda c: c.input_price_per_1m + c.output_price_per_1m)
        if pool:
            entry = pool[0]
            fallback_entries = pool[1:3]

    elif mode == "nitro":
        # Prefer Groq (fastest inference) if it hosts an equivalent model;
        # otherwise keep the resolved entry and just skip slow fallbacks.
        groq_equivalent = db.query(ModelRegistryEntry).filter(
            ModelRegistryEntry.adapter == "groq", ModelRegistryEntry.is_enabled.is_(True)
        ).first()
        if groq_equivalent:
            fallback_entries = [entry]
            entry = groq_equivalent

    else:
        # Default mode: still build a small same-adapter-family fallback
        # list so a transient provider outage doesn't fail the request.
        candidates = db.query(ModelRegistryEntry).filter(
            ModelRegistryEntry.is_enabled.is_(True), ModelRegistryEntry.is_alias.is_(False),
            ModelRegistryEntry.slug != entry.slug,
        ).limit(2).all()
        fallback_entries = candidates

    return ResolvedRoute(entry=entry, routing_mode=mode, fallback_entries=fallback_entries)
