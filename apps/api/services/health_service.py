import asyncio
import os
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
                settings.FFMPEG_PATH, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                first_line = stdout.decode().split("\n")[0]
                return {"status": "healthy", "details": first_line}
            return {"status": "unavailable", "details": "FFmpeg exited with non-zero status"}
        except FileNotFoundError:
            return {"status": "unavailable", "details": f"FFmpeg binary '{settings.FFMPEG_PATH}' not found on PATH"}
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
            return {"status": "unavailable", "details": f"Redis connection error: {str(e)}"}

    def check_ai_providers(self) -> Dict[str, str]:
        has_gemini = bool(settings.GEMINI_API_KEY)
        has_openai = bool(settings.OPENAI_API_KEY)
        has_anthropic = bool(settings.ANTHROPIC_API_KEY)
        if has_gemini or has_openai or has_anthropic:
            providers = []
            if has_gemini: providers.append("Gemini")
            if has_openai: providers.append("OpenAI")
            if has_anthropic: providers.append("Anthropic")
            return {"status": "healthy", "details": f"Configured providers: {', '.join(providers)}"}
        return {"status": "not_configured", "details": "No AI API keys configured"}

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
            "details": f"Min Sample Threshold: {settings.MIN_RECOMMENDATION_SAMPLES} posts"
        }

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Returns real local CPU, memory, disk, and storage metrics or UNAVAILABLE."""
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(settings.STORAGE_DIR if os.path.exists(settings.STORAGE_DIR) else "/")

            db_health = await self.check_database()
            redis_health = await self.check_redis()

            return {
                "status": "AVAILABLE",
                "version": settings.APP_VERSION,
                "cpu": {
                    "usage_percent": cpu_pct,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total_mb": round(mem.total / (1024 * 1024), 2),
                    "used_mb": round(mem.used / (1024 * 1024), 2),
                    "free_mb": round(mem.available / (1024 * 1024), 2),
                    "usage_percent": mem.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": disk.percent,
                    "warning": disk.percent >= settings.STORAGE_WARNING_THRESHOLD_PERCENT
                },
                "database_connected": db_health["status"] == "healthy",
                "redis_connected": redis_health["status"] == "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except Exception:
            return {
                "status": "UNAVAILABLE",
                "version": settings.APP_VERSION,
                "cpu": None,
                "memory": None,
                "disk": None,
                "database_connected": None,
                "redis_connected": None,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

    async def get_readiness_status(self) -> Dict[str, Any]:
        """Dependency readiness check endpoint (/health/ready)."""
        db_res = await self.check_database()
        storage_res = await self.check_storage()
        ffmpeg_res = await self.check_ffmpeg()
        redis_res = await self.check_redis()
        ai_res = self.check_ai_providers()

        is_ready = (
            db_res["status"] == "healthy" and
            storage_res["status"] == "healthy" and
            ffmpeg_res["status"] == "healthy"
        )

        return {
            "status": "READY" if is_ready else "ACTION_REQUIRED",
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "dependencies": {
                "database": db_res,
                "storage": storage_res,
                "ffmpeg": ffmpeg_res,
                "redis": redis_res,
                "ai": ai_res
            }
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

        is_healthy = db_res["status"] == "healthy" and storage_res["status"] == "healthy"
        overall_status = "healthy" if is_healthy else "degraded"

        return {
            "status": overall_status,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": components
        }

health_service = HealthService()
