from fastapi import APIRouter
from config import settings

router = APIRouter(prefix="", tags=["Public API v1"])

@router.get("/", tags=["Public API v1"])
async def get_api_discovery_metadata():
    """Returns Public API v1 metadata, versioning rules, and documentation resources."""
    return {
        "name": "Reflow Public API",
        "version": "v1.0.0",
        "app_version": settings.APP_VERSION,
        "documentation": "/docs",
        "developer_portal": "/developers",
        "capabilities": [
            "content_ingest",
            "media_processing",
            "clip_discovery",
            "carousel_rendering",
            "copy_generation",
            "governance_qc",
            "multi_platform_publishing",
            "utc_scheduling",
            "analytics_telemetry",
            "experiments_ab",
            "closed_loop_automations",
            "signed_webhooks"
        ]
    }
