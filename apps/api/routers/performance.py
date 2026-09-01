import os
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, engine
from services.resource_manager import resource_manager
from services.tmp_storage_service import tmp_storage_service
from services.queue_service import queue_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PerformanceRouter")
router = APIRouter(prefix="/system", tags=["Observability & Performance"])

@router.get("/performance")
async def get_system_performance_telemetry(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns real-time telemetry metrics for CPU, Memory, Disk, DB pool, Redis depth, and Worker concurrency.
    Contains zero fake mock data.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    
    disk_capacity = resource_manager.check_disk_capacity()
    queue_metrics = await queue_service.get_queue_metrics()
    concurrency_limits = resource_manager.get_worker_concurrency_limits()

    # DB Connection Pool Info
    pool_info = {
        "size": engine.pool.size() if hasattr(engine.pool, "size") else 0,
        "checked_in": engine.pool.checkedin() if hasattr(engine.pool, "checkedin") else 0,
        "checked_out": engine.pool.checkedout() if hasattr(engine.pool, "checkedout") else 0,
        "overflow": engine.pool.overflow() if hasattr(engine.pool, "overflow") else 0
    }

    return {
        "status": "HEALTHY" if not queue_metrics["is_saturated"] and disk_capacity["is_sufficient"] else "DEGRADED",
        "cpu": {
            "usage_percent": cpu_percent,
            "core_count": psutil.cpu_count(logical=True)
        },
        "memory": {
            "total_mb": round(memory.total / (1024 ** 2), 2),
            "used_mb": round(memory.used / (1024 ** 2), 2),
            "available_mb": round(memory.available / (1024 ** 2), 2),
            "usage_percent": memory.percent
        },
        "disk": disk_capacity,
        "database_pool": pool_info,
        "queue": queue_metrics,
        "concurrency_limits": concurrency_limits
    }

@router.get("/storage")
async def get_storage_breakdown(
    db: AsyncSession = Depends(get_db)
):
    """Returns actual storage breakdown across originals, variants, clips, carousels, exports, and temp files."""
    return await tmp_storage_service.get_storage_breakdown(db)

@router.post("/storage/cleanup")
async def trigger_storage_cleanup(
    db: AsyncSession = Depends(get_db)
):
    """Purges expired temporary files and partial renders safely from disk."""
    res = await tmp_storage_service.purge_expired_tmp_files(db)
    return {
        "status": "success",
        "message": f"Cleaned up {res['purged_count']} temporary artifacts.",
        "freed_mb": res["freed_mb"]
    }
