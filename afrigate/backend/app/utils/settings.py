from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import PlatformSettings

env_settings = get_settings()


def get_platform_settings(db: Session) -> PlatformSettings:
    row = db.query(PlatformSettings).filter(PlatformSettings.id == "default").first()
    if not row:
        row = PlatformSettings(id="default", topup_fee_percent=env_settings.TOPUP_FEE_PERCENT)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def set_topup_fee_percent(db: Session, percent: float) -> PlatformSettings:
    row = get_platform_settings(db)
    row.topup_fee_percent = percent
    db.commit()
    db.refresh(row)
    return row


FX_COLUMNS = {"usd_to_tzs", "usd_to_kes", "usd_to_ngn", "usd_to_ghs", "usd_to_ugx"}


def set_fx_rates_manual(db: Session, rates: dict) -> PlatformSettings:
    """
    Admin manual override, e.g. {"usd_to_tzs": 2700.0}. Marks the source as
    'manual' so it's visible on the dashboard that this isn't today's
    auto-synced market rate. Does NOT disable future auto-syncs by itself -
    use set_fx_auto_update_enabled(False) if you want to freeze it.
    """
    row = get_platform_settings(db)
    for column, value in rates.items():
        if column in FX_COLUMNS and value is not None:
            setattr(row, column, value)
    row.fx_source = "manual"
    db.commit()
    db.refresh(row)
    return row


def set_fx_auto_update_enabled(db: Session, enabled: bool) -> PlatformSettings:
    row = get_platform_settings(db)
    row.fx_auto_update_enabled = enabled
    db.commit()
    db.refresh(row)
    return row
