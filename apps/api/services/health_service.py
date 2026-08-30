import asyncio
import os
import subprocess
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text
from database import engine
from config import settings
from services.storage_service import storage_service

class HealthService:
    async def check_database(self) -> Dict[str, str]:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "healthy", "details": "Database responding to ping"}
        except Exception as e:
            return {"status": "unavailable", "details": f"Database connection error: {str(e)}"}

    async def check_storage(self) -> Dict[str, str]:
        try:
            test_file = ".health_check"
            await storage_service.put(test_file, b"ok")
            exists = await storage_service.exists(test_file)
            await storage_service.delete(test_file)
            if exists:
                return {"status": "healthy", "details": f"Storage accessible ({settings.STORAGE_PROVIDER})"}
            return {"status": "degraded", "details": "Storage write test failed"}
        except Exception as e:
            return {"status": "unavailable", "details": f"Storage error: {str(e)}"}

    async def check_ffmpeg(self) -> Dict[str, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                first_line = stdout.decode().split("\n")[0]
                return {"status": "healthy", "details": first_line}
            return {"status": "unavailable", "details": "FFmpeg exited with non-zero status"}
        except FileNotFoundError:
            return {"status": "unavailable", "details": "FFmpeg binary not found on PATH"}
        except Exception as e:
            return {"status": "unavailable", "details": str(e)}

    async def check_redis(self) -> Dict[str, str]:
        if not settings.REDIS_URL:
            return {"status": "not_configured", "details": "Redis URL is not set"}
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.0)
            await client.ping()
            await client.aclose()
            return {"status": "healthy", "details": "Redis ping successful"}
        except Exception as e:
            return {"status": "degraded", "details": f"Redis unavailable: {str(e)} (Optional in Phase 0)"}

    def check_ai_providers(self) -> Dict[str, str]:
        has_gemini = bool(settings.GEMINI_API_KEY)
        has_openai = bool(settings.OPENAI_API_KEY)
        if has_gemini or has_openai:
            providers = []
            if has_gemini: providers.append("Gemini")
            if has_openai: providers.append("OpenAI")
            return {"status": "healthy", "details": f"Configured providers: {', '.join(providers)}"}
        return {"status": "not_configured", "details": "No API keys configured (offline mock active)"}

    def check_scheduler(self) -> Dict[str, str]:
        from services.scheduler_service import scheduler_service
        telemetry = scheduler_service.get_telemetry()
        return {
            "status": "healthy" if telemetry["status"] == "HEALTHY" else "idle",
            "details": f"Instance: {telemetry['instance_id']}, Lag: {telemetry['lag_seconds']}s"
        }

    def check_analytics(self) -> Dict[str, str]:
        return {
            "status": "healthy",
            "details": f"Sync Interval: {settings.ANALYTICS_SYNC_INTERVAL_MINUTES}m, Stale Threshold: {settings.ANALYTICS_STALE_AFTER_HOURS}h"
        }

    def check_intelligence(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "details": f"Min Sample Threshold: {settings.MIN_RECOMMENDATION_SAMPLES} posts, Stale Threshold: {settings.INTELLIGENCE_STALE_AFTER_HOURS}h"
        }

    async def check_experiment_engine(self) -> Dict[str, Any]:
        try:
            from database import async_session_factory
            from models.entities import Experiment, Job
            from sqlalchemy import select, func, and_
            async with async_session_factory() as session:
                active_res = await session.execute(
                    select(func.count(Experiment.id)).where(Experiment.status == "RUNNING")
                )
                active_count = active_res.scalar() or 0

                queued_res = await session.execute(
                    select(func.count(Job.id)).where(
                        and_(Job.type == "EXPERIMENT_EVALUATION", Job.status == "QUEUED")
                    )
                )
                queued_count = queued_res.scalar() or 0

                last_success_res = await session.execute(
                    select(Job.completed_at)
                    .where(and_(Job.type == "EXPERIMENT_EVALUATION", Job.status == "SUCCEEDED"))
                    .order_by(Job.completed_at.desc())
                    .limit(1)
                )
                last_success = last_success_res.scalar()

                last_fail_res = await session.execute(
                    select(Job.completed_at)
                    .where(and_(Job.type == "EXPERIMENT_EVALUATION", Job.status == "FAILED"))
                    .order_by(Job.completed_at.desc())
                    .limit(1)
                )
                last_fail = last_fail_res.scalar()

            status = "healthy"
            if queued_count > 10:
                status = "degraded"

            return {
                "status": status,
                "details": f"Active: {active_count}, Queued: {queued_count}",
                "metrics": {
                    "active_experiments": active_count,
                    "queued_evaluations": queued_count,
                    "last_successful_evaluation": last_success.isoformat() if last_success else None,
                    "last_failed_evaluation": last_fail.isoformat() if last_fail else None
                }
            }
        except Exception as e:
            return {"status": "degraded", "details": f"Error: {e}"}

    async def check_automation_engine(self) -> Dict[str, Any]:
        try:
            from database import async_session_factory
            from models.entities import AutomationRule, AutomationExecution
            from sqlalchemy import select, func, or_
            async with async_session_factory() as session:
                active_rules_res = await session.execute(
                    select(func.count(AutomationRule.id)).where(AutomationRule.status == "ACTIVE")
                )
                active_rules = active_rules_res.scalar() or 0

                active_execs_res = await session.execute(
                    select(func.count(AutomationExecution.id)).where(
                        AutomationExecution.status.in_(["QUEUED", "RUNNING"])
                    )
                )
                active_execs = active_execs_res.scalar() or 0

                succeeded_res = await session.execute(
                    select(func.count(AutomationExecution.id)).where(AutomationExecution.status == "SUCCEEDED")
                )
                succeeded = succeeded_res.scalar() or 0

                failed_res = await session.execute(
                    select(func.count(AutomationExecution.id)).where(AutomationExecution.status == "FAILED")
                )
                failed = failed_res.scalar() or 0

                last_exec_res = await session.execute(
                    select(AutomationExecution.created_at)
                    .order_by(AutomationExecution.created_at.desc())
                    .limit(1)
                )
                last_exec = last_exec_res.scalar()

                last_fail_res = await session.execute(
                    select(AutomationExecution.completed_at)
                    .where(AutomationExecution.status == "FAILED")
                    .order_by(AutomationExecution.completed_at.desc())
                    .limit(1)
                )
                last_fail = last_fail_res.scalar()

            status = "healthy"
            if active_execs > 20:
                status = "degraded"

            return {
                "status": status,
                "details": f"Active Rules: {active_rules}, Running: {active_execs}",
                "metrics": {
                    "active_rules": active_rules,
                    "running_executions": active_execs,
                    "successful_executions": succeeded,
                    "failed_executions": failed,
                    "last_execution": last_exec.isoformat() if last_exec else None,
                    "last_failure": last_fail.isoformat() if last_fail else None
                }
            }
        except Exception as e:
            return {"status": "degraded", "details": f"Error: {e}"}

    async def get_overall_health(self) -> Dict[str, Any]:
        db_res = await self.check_database()
        storage_res = await self.check_storage()
        ffmpeg_res = await self.check_ffmpeg()
        redis_res = await self.check_redis()
        ai_res = self.check_ai_providers()
        scheduler_res = self.check_scheduler()
        analytics_res = self.check_analytics()
        intelligence_res = self.check_intelligence()
        experiments_res = await self.check_experiment_engine()
        automations_res = await self.check_automation_engine()

        components = {
            "database": db_res,
            "storage": storage_res,
            "ffmpeg": ffmpeg_res,
            "redis": redis_res,
            "ai": ai_res,
            "scheduler": scheduler_res,
            "analytics": analytics_res,
            "intelligence": intelligence_res,
            "experiments": experiments_res,
            "automations": automations_res
        }

        # Overall status is healthy if critical services (db & storage) are healthy
        is_healthy = db_res["status"] == "healthy" and storage_res["status"] == "healthy"
        overall_status = "healthy" if is_healthy else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": components
        }

health_service = HealthService()
