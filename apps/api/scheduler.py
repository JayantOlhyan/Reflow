import asyncio
import os
import sys
from datetime import datetime, timedelta

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

    last_analytics_sweep = datetime.utcnow() - timedelta(minutes=settings.ANALYTICS_SYNC_INTERVAL_MINUTES)
    last_intelligence_sweep = datetime.utcnow() - timedelta(hours=settings.INTELLIGENCE_STALE_AFTER_HOURS)
    last_experiment_sweep = datetime.utcnow() - timedelta(minutes=15)

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

            # 4. Periodic analytics sync sweep
            now_utc = datetime.utcnow()
            if (now_utc - last_analytics_sweep).total_seconds() >= (settings.ANALYTICS_SYNC_INTERVAL_MINUTES * 60):
                from services.analytics_service import analytics_service
                logger.info("Executing scheduled analytics sync sweep for published posts...")
                await analytics_service.backfill_analytics(limit=50)
                last_analytics_sweep = now_utc

            # 5. Periodic intelligence pattern analysis sweep
            if (now_utc - last_intelligence_sweep).total_seconds() >= (settings.INTELLIGENCE_STALE_AFTER_HOURS * 3600):
                from services.intelligence_service import intelligence_service
                logger.info("Executing scheduled content intelligence analysis sweep...")
                await intelligence_service.run_full_analysis()
                last_intelligence_sweep = now_utc

            # 6. Periodic experiment evaluation sweep (every 15 minutes or when stale)
            if (now_utc - last_experiment_sweep).total_seconds() >= (15 * 60):
                from database import async_session_factory
                from models.entities import Experiment, Job
                from services.queue_service import queue_service
                import uuid
                logger.info("Executing scheduled content experiments evaluation sweep...")
                async with async_session_factory() as session:
                    res = await session.execute(
                        select(Experiment).where(Experiment.status == "RUNNING")
                    )
                    running_exps = res.scalars().all()
                    for exp in running_exps:
                        job_id = f"job_exp_{uuid.uuid4().hex[:8]}"
                        eval_job = Job(
                            id=job_id,
                            type="EXPERIMENT_EVALUATION",
                            status="QUEUED",
                            created_at=datetime.utcnow()
                        )
                        session.add(eval_job)
                        await session.commit()
                        await queue_service.enqueue_media_job(
                            job_id=job_id,
                            job_type="EXPERIMENT_EVALUATION",
                            experiment_id=exp.id
                        )
                last_experiment_sweep = now_utc

            await asyncio.sleep(settings.SCHEDULER_POLL_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("Scheduler daemon shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in scheduler loop: {e}")
            await asyncio.sleep(settings.SCHEDULER_POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(run_scheduler())
