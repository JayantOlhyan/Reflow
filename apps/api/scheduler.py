import asyncio
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from config import settings
from database import init_db
from services.scheduler_service import scheduler_service
from utils.logging import get_logger

logger = get_logger("SchedulerDaemon")

async def run_scheduler():
    """Continuous background scheduler daemon loop."""
    logger.info(f"Starting Reflow Content Scheduler daemon (Instance: {scheduler_service.instance_id}, Interval: {settings.SCHEDULER_POLL_INTERVAL_SECONDS}s)...")
    await init_db()

    while True:
        try:
            scheduler_service.record_heartbeat()

            # 1. Recover stale claims from any crashed scheduler instances
            await scheduler_service.recover_stale_claims()

            # 2. Atomically claim due publications
            claimed_ids = await scheduler_service.claim_due_publications(limit=50)

            # 3. Dispatch claimed publications to publishing queue
            if claimed_ids:
                dispatched = await scheduler_service.dispatch_claimed_publications(claimed_ids)
                logger.info(f"Dispatched {dispatched} due publication(s) to publishing worker queue.")

            await asyncio.sleep(settings.SCHEDULER_POLL_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("Scheduler daemon shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in scheduler loop: {e}")
            await asyncio.sleep(settings.SCHEDULER_POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(run_scheduler())
