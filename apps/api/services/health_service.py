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

    async def get_overall_health(self) -> Dict[str, Any]:
        db_res = await self.check_database()
        storage_res = await self.check_storage()
        ffmpeg_res = await self.check_ffmpeg()
        redis_res = await self.check_redis()
        ai_res = self.check_ai_providers()
        scheduler_res = self.check_scheduler()
        analytics_res = self.check_analytics()
        intelligence_res = self.check_intelligence()

        components = {
            "database": db_res,
            "storage": storage_res,
            "ffmpeg": ffmpeg_res,
            "redis": redis_res,
            "ai": ai_res,
            "scheduler": scheduler_res,
            "analytics": analytics_res,
            "intelligence": intelligence_res
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
