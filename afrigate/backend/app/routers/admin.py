from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ModelRegistryEntry, ModelSuggestion
from app.schemas import (
    AdminModelUpsertRequest, AdminAliasRequest, AdminModelEntry,
    ModelSuggestionResponse, PlatformSettingsResponse, UpdatePlatformSettingsRequest,
    UpdateFxRatesRequest, SetFxAutoUpdateRequest,
)
from app.security import require_admin
from app.utils.settings import (
    get_platform_settings, set_topup_fee_percent, set_fx_rates_manual, set_fx_auto_update_enabled,
)
from app.utils.model_discovery import discover_new_models
from app.utils.fx_rates import sync_fx_rates

router = APIRouter(prefix="/api/admin/models", tags=["admin"])

# Separate router (still under /api/admin) for the parts that aren't
# specifically about one model: suggestions feed + platform-wide settings.
misc_router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("", response_model=list[AdminModelEntry])
def list_all_models(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(ModelRegistryEntry).order_by(ModelRegistryEntry.slug).all()


@router.post("", response_model=AdminModelEntry, status_code=201)
def upsert_model(body: AdminModelUpsertRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """
    Add a brand-new model, or update an existing one by slug (e.g. bump
    pricing after a provider changes theirs). This is the entire workflow
    for onboarding a new model version - no deploy required.
    """
    entry = db.query(ModelRegistryEntry).filter(ModelRegistryEntry.slug == body.slug).first()
    if entry:
        for field, value in body.model_dump().items():
            setattr(entry, field, value)
    else:
        entry = ModelRegistryEntry(**body.model_dump())
        db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/alias", response_model=AdminModelEntry, status_code=201)
def set_alias(body: AdminAliasRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """
    Create or repoint an alias, e.g. alias_slug='claude-latest' pointing
    to points_to_slug='anthropic/claude-sonnet-4-5'. Every developer using
    'claude-latest' upgrades instantly; anyone pinned to the real slug is
    unaffected. This is the "zero-downtime model upgrade" mechanism.
    """
    target = db.query(ModelRegistryEntry).filter(ModelRegistryEntry.slug == body.points_to_slug).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"Target slug '{body.points_to_slug}' does not exist yet.")

    alias = db.query(ModelRegistryEntry).filter(ModelRegistryEntry.slug == body.alias_slug).first()
    if alias:
        alias.points_to_slug = body.points_to_slug
        alias.is_alias = True
    else:
        alias = ModelRegistryEntry(
            slug=body.alias_slug, display_name=f"{target.display_name} (alias)",
            adapter=target.adapter, upstream_model_id=target.upstream_model_id,
            is_alias=True, points_to_slug=body.points_to_slug,
            input_price_per_1m=target.input_price_per_1m, output_price_per_1m=target.output_price_per_1m,
            context_window=target.context_window, tier=target.tier,
        )
        db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


@router.post("/{slug:path}/deprecate", response_model=AdminModelEntry)
def deprecate_model(slug: str, sunset_in_days: int = 180,
                     admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Marks a model deprecated with a scheduled sunset date, giving
    developers advance warning (per the original spec's 6-month cycle
    recommendation - default here is ~6 months, adjustable per call)."""
    entry = db.query(ModelRegistryEntry).filter(ModelRegistryEntry.slug == slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Model not found.")
    entry.deprecated_at = datetime.utcnow()
    entry.sunset_at = datetime.utcnow() + timedelta(days=max(sunset_in_days, 0))
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{slug:path}/toggle", response_model=AdminModelEntry)
def toggle_model(slug: str, enabled: bool, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Enable/disable a model instantly - no server restart, matches the
    original spec's requirement exactly."""
    entry = db.query(ModelRegistryEntry).filter(ModelRegistryEntry.slug == slug).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Model not found.")
    entry.is_enabled = enabled
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# Model discovery (the daily-cron feature) - suggestions feed
# ---------------------------------------------------------------------------

@misc_router.get("/suggestions", response_model=list[ModelSuggestionResponse])
def list_suggestions(status: str = "new", admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """
    The 'new models detected' feed shown on the admin dashboard. Defaults
    to only pending ('new') suggestions - pass status=dismissed/added to
    review history.
    """
    return (
        db.query(ModelSuggestion)
        .filter(ModelSuggestion.status == status)
        .order_by(ModelSuggestion.first_seen_at.desc())
        .all()
    )


@misc_router.post("/suggestions/{suggestion_id}/dismiss", response_model=ModelSuggestionResponse)
def dismiss_suggestion(suggestion_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(ModelSuggestion).filter(ModelSuggestion.id == suggestion_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    row.status = "dismissed"
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@misc_router.post("/suggestions/{suggestion_id}/promote", response_model=AdminModelEntry, status_code=201)
def promote_suggestion(
    suggestion_id: str, body: AdminModelUpsertRequest,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    """
    Turns a suggestion into a real, live model. The suggestion already
    told you the adapter + upstream_model_id - you (the admin) only need
    to fill in display_name, pricing, context_window, and tier in the
    request body. This is the one step that still needs a human: pricing
    can't be reliably scraped from a provider's models-list endpoint.
    """
    suggestion = db.query(ModelSuggestion).filter(ModelSuggestion.id == suggestion_id).first()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found.")

    entry = ModelRegistryEntry(**body.model_dump())
    db.add(entry)
    suggestion.status = "added"
    suggestion.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return entry


@misc_router.post("/suggestions/run-now")
async def run_discovery_now(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Manually triggers a discovery pass immediately, instead of waiting
    for the daily schedule - useful right after adding new provider keys,
    or just to check things are working."""
    new_count = await discover_new_models(db)
    return {"new_suggestions_found": new_count}


# ---------------------------------------------------------------------------
# Platform-wide settings (top-up fee % + FX rates - see EXCHANGE_RATES.md)
# ---------------------------------------------------------------------------

@misc_router.get("/settings", response_model=PlatformSettingsResponse)
def get_settings_endpoint(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return get_platform_settings(db)


@misc_router.put("/settings", response_model=PlatformSettingsResponse)
def update_settings_endpoint(
    body: UpdatePlatformSettingsRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    """Changes the top-up fee % instantly - no .env edit, no redeploy.
    Applies to every top-up from the next request onward."""
    if body.topup_fee_percent is None:
        return get_platform_settings(db)
    return set_topup_fee_percent(db, body.topup_fee_percent)


@misc_router.put("/settings/fx-rates", response_model=PlatformSettingsResponse)
def update_fx_rates_endpoint(
    body: UpdateFxRatesRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    """
    Manual override for one or more exchange rates, e.g. after checking a
    bank's rate yourself. This does NOT pause the daily auto-sync - use
    PUT /settings/fx-auto-update to do that if you want a manual rate to
    stick until you change it again.
    """
    return set_fx_rates_manual(db, body.model_dump(exclude_none=True))


@misc_router.put("/settings/fx-auto-update", response_model=PlatformSettingsResponse)
def set_fx_auto_update_endpoint(
    body: SetFxAutoUpdateRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    """Pause/resume the daily automatic FX sync. Paused = your manually-set
    rates are never overwritten until you turn this back on."""
    return set_fx_auto_update_enabled(db, body.enabled)


@misc_router.post("/settings/sync-fx-now", response_model=PlatformSettingsResponse)
async def sync_fx_now_endpoint(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """
    Manually pulls today's live rates right now, instead of waiting for the
    daily schedule. Works even if fx_auto_update_enabled is paused (force=True) -
    a manual click should always be allowed to succeed.
    """
    await sync_fx_rates(db, force=True)
    return get_platform_settings(db)
