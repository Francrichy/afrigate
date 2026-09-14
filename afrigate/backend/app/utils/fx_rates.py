"""
Daily FX rate sync. Source: open.er-api.com - a genuinely free, no-API-key
endpoint (updates once every 24h, requires attribution which we give here
in this comment: rates provided by https://www.exchangerate-api.com).

This module NEVER raises and NEVER silently corrupts pricing: if the fetch
fails for any reason (network, malformed response, currency missing), the
existing rates in PlatformSettings are left untouched and a warning is
logged. A stale-but-correct rate is always safer than a broken one.
"""
import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models import PlatformSettings
from app.utils.settings import get_platform_settings

logger = logging.getLogger("fx_rates")

FX_API_URL = "https://open.er-api.com/v6/latest/USD"

# Maps our PlatformSettings column name -> the currency code open.er-api.com uses
SUPPORTED_CURRENCIES = {
    "usd_to_tzs": "TZS",
    "usd_to_kes": "KES",
    "usd_to_ngn": "NGN",
    "usd_to_ghs": "GHS",
    "usd_to_ugx": "UGX",
}


async def fetch_live_rates() -> dict[str, float] | None:
    """Returns {'TZS': 2650.3, 'KES': 129.1, ...} or None on any failure."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(FX_API_URL)
        if resp.status_code != 200:
            logger.warning("FX rate fetch failed with status %s", resp.status_code)
            return None
        data = resp.json()
        if data.get("result") != "success":
            logger.warning("FX rate API returned non-success result: %s", data.get("result"))
            return None
        rates = data.get("rates", {})
        out = {code: rates[code] for code in SUPPORTED_CURRENCIES.values() if code in rates}
        missing = set(SUPPORTED_CURRENCIES.values()) - set(out.keys())
        if missing:
            logger.warning("FX rate response is missing currencies: %s", missing)
        return out if out else None
    except Exception as e:
        logger.warning("FX rate fetch raised an exception: %s", e)
        return None


async def sync_fx_rates(db: Session, force: bool = False) -> bool:
    """
    Fetches live rates and updates PlatformSettings IF fx_auto_update_enabled
    is True (or `force=True` for a manual "refresh now" click from the admin
    dashboard, which should work even if auto-update is paused).
    Returns True if rates were actually updated, False otherwise.
    """
    settings_row = get_platform_settings(db)
    if not settings_row.fx_auto_update_enabled and not force:
        logger.info("FX auto-update is disabled - skipping scheduled sync.")
        return False

    rates = await fetch_live_rates()
    if not rates:
        return False

    for column, currency_code in SUPPORTED_CURRENCIES.items():
        if currency_code in rates:
            setattr(settings_row, column, rates[currency_code])

    settings_row.fx_last_synced_at = datetime.utcnow()
    settings_row.fx_source = "auto:open.er-api.com"
    db.commit()
    logger.info("FX rates synced successfully: %s", rates)
    return True
