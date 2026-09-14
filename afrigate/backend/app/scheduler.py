"""
Runs the model-discovery job automatically, once a day, for as long as the
backend process is running - no separate worker/infra needed for Phase 1.

If you scale to multiple Render instances later, move this to a single
dedicated worker (or a Render Cron Job hitting a protected internal
endpoint) so the scan doesn't run once per instance.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.utils.model_discovery import discover_new_models

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


def start_scheduler():
    scheduler.add_job(_run_discovery_job, "interval", hours=24, id="model_discovery", replace_existing=True)
    scheduler.start()
    logger.info("Model-discovery scheduler started - runs every 24h.")
