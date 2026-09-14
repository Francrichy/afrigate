"""
Runs two daily background jobs automatically for as long as the backend
process is running - no separate worker/infra needed for Phase 1:

  1. Model discovery  - checks each AI provider for new models.
  2. FX rate sync      - refreshes local-currency exchange rates.

If you scale to multiple Render instances later, move both to a single
dedicated worker (or a Render Cron Job hitting a protected internal
endpoint) so they don't run once per instance.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.utils.model_discovery import discover_new_models
from app.utils.fx_rates import sync_fx_rates

logger = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler()


async def _run_discovery_job():
    db = SessionLocal()
    try:
        await discover_new_models(db)
    except Exception as e:
        logger.error("Scheduled model discovery run failed: %s", e)
    finally:
        db.close()


async def _run_fx_sync_job():
    db = SessionLocal()
    try:
        await sync_fx_rates(db)
    except Exception as e:
        logger.error("Scheduled FX rate sync failed: %s", e)
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(_run_discovery_job, "interval", hours=24, id="model_discovery", replace_existing=True)
    scheduler.add_job(_run_fx_sync_job, "interval", hours=24, id="fx_sync", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started - model discovery + FX rate sync run every 24h.")
