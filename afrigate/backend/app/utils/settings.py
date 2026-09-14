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
