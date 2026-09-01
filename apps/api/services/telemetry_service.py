import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func

from database import async_session_factory
from models.entities import Content, Publication, SystemJob, DeadLetterJob, Incident, SystemEvent, QualityCheck, Clip, Carousel
from utils.logging import get_logger

logger = get_logger("TelemetryService")

class TelemetryService:
    """
    Real Telemetry & End-to-End Correlation Trace Service for Reflow.
    Resolves request_id, job_id, and content_id timelines and maintains
    histogram metrics distributions without high-cardinality label pollution.
    """
    _instance: Optional['TelemetryService'] = None

    def __init__(self):
        self._histograms: Dict[str, List[float]] = {
            "api_request_duration_ms": [],
            "media_processing_duration_ms": [],
            "ai_generation_duration_ms": [],
            "publication_duration_ms": [],
            "automation_duration_ms": []
        }
        self._max_samples = 1000

    @classmethod
    def get_instance(cls) -> 'TelemetryService':
        if cls._instance is None:
            cls._instance = TelemetryService()
        return cls._instance

    def record_duration(self, metric_name: str, duration_ms: float):
        """Records a duration sample in metric histogram distribution."""
        if metric_name not in self._histograms:
            self._histograms[metric_name] = []

        samples = self._histograms[metric_name]
        samples.append(float(duration_ms))
        if len(samples) > self._max_samples:
            samples.pop(0)

    def get_histogram_stats(self, metric_name: str) -> Dict[str, Any]:
        """Calculates count, p50, p90, p99 latency stats for metric histogram."""
        samples = sorted(self._histograms.get(metric_name, []))
        if not samples:
            return {"count": 0, "p50_ms": 0.0, "p90_ms": 0.0, "p99_ms": 0.0}

        n = len(samples)
        p50 = samples[int(n * 0.50)]
        p90 = samples[min(int(n * 0.90), n - 1)]
        p99 = samples[min(int(n * 0.99), n - 1)]
        return {
            "count": n,
            "p50_ms": round(p50, 2),
            "p90_ms": round(p90, 2),
            "p99_ms": round(p99, 2)
        }

    async def trace_request(self, session, request_id: str) -> Dict[str, Any]:
        """Traces end-to-end timeline for a request_id."""
        j_res = await session.execute(select(SystemJob).where(SystemJob.payload_json.like(f"%{request_id}%")))
        jobs = j_res.scalars().all()

        e_res = await session.execute(select(SystemEvent).where(SystemEvent.payload_json.like(f"%{request_id}%")))
        events = e_res.scalars().all()

        timeline = []
        for j in jobs:
            timeline.append({
                "type": "JOB",
                "id": j.id,
                "job_type": j.job_type,
                "status": j.status,
                "timestamp": j.queued_at
            })
        for e in events:
            timeline.append({
                "type": "EVENT",
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "timestamp": e.created_at
            })

        timeline.sort(key=lambda x: str(x["timestamp"]))
        return {
            "trace_id": request_id,
            "trace_type": "REQUEST",
            "items": timeline,
            "created_at": datetime.utcnow().isoformat()
        }

    async def trace_job(self, session, job_id: str) -> Dict[str, Any]:
        """Traces complete execution lifecycle for a job_id."""
        j_res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
        job = j_res.scalar_one_or_none()
        if not job:
            return {"trace_id": job_id, "trace_type": "JOB", "items": [], "created_at": datetime.utcnow().isoformat()}

        d_res = await session.execute(select(DeadLetterJob).where(DeadLetterJob.job_id == job_id))
        dlq = d_res.scalar_one_or_none()

        items = [
            {"step": "QUEUED", "timestamp": job.queued_at, "details": f"Job enqueued (type={job.job_type})"},
        ]
        if job.started_at:
            items.append({"step": "STARTED", "timestamp": job.started_at, "details": "Execution started by worker"})
        if job.completed_at:
            items.append({"step": "COMPLETED", "timestamp": job.completed_at, "details": f"Finished in {job.duration_ms}ms"})
        if job.failed_at:
            items.append({"step": "FAILED", "timestamp": job.failed_at, "details": f"Failed ({job.error_code}): {job.last_error}"})
        if dlq:
            items.append({"step": "DEAD_LETTER_QUEUE", "timestamp": dlq.failed_at, "details": f"Routed to DLQ after {dlq.attempts} attempts"})

        return {
            "trace_id": job_id,
            "trace_type": "JOB",
            "items": items,
            "created_at": datetime.utcnow().isoformat()
        }

    async def trace_content(self, session, content_id: str) -> Dict[str, Any]:
        """Traces full lifecycle chain for a content_id."""
        c_res = await session.execute(select(Content).where(Content.id == content_id))
        content = c_res.scalar_one_or_none()

        j_res = await session.execute(select(SystemJob).where(SystemJob.content_id == content_id).order_by(SystemJob.queued_at.asc()))
        jobs = j_res.scalars().all()

        cl_res = await session.execute(select(Clip).where(Clip.content_id == content_id))
        clips = cl_res.scalars().all()

        p_res = await session.execute(select(Publication).where(Publication.content_id == content_id))
        pubs = p_res.scalars().all()

        timeline = []
        if content:
            timeline.append({"step": "CONTENT_INGESTED", "timestamp": content.created_at, "details": content.title})
        for j in jobs:
            timeline.append({"step": f"JOB_{j.job_type}", "timestamp": j.queued_at, "details": f"Status: {j.status}"})
        for c in clips:
            timeline.append({"step": "CLIP_DISCOVERED", "timestamp": c.created_at, "details": c.title})
        for p in pubs:
            timeline.append({"step": "PUBLISHED", "timestamp": p.created_at, "details": f"Platform: {p.platform}, Status: {p.status}"})

        timeline.sort(key=lambda x: str(x["timestamp"]))
        return {
            "trace_id": content_id,
            "trace_type": "CONTENT",
            "items": timeline,
            "created_at": datetime.utcnow().isoformat()
        }

    async def get_metrics_telemetry(self, session) -> Dict[str, Any]:
        """Gets telemetry metrics distributions."""
        j_succ = await session.execute(select(func.count(SystemJob.id)).where(SystemJob.status == "SUCCEEDED"))
        j_fail = await session.execute(select(func.count(SystemJob.id)).where(SystemJob.status == "FAILED"))

        p_succ = await session.execute(select(func.count(Publication.id)).where(Publication.status == "PUBLISHED"))
        p_fail = await session.execute(select(func.count(Publication.id)).where(Publication.status == "FAILED"))

        return {
            "jobs": {
                "succeeded": j_succ.scalar() or 0,
                "failed": j_fail.scalar() or 0,
                "duration_histogram": self.get_histogram_stats("media_processing_duration_ms")
            },
            "publications": {
                "succeeded": p_succ.scalar() or 0,
                "failed": p_fail.scalar() or 0,
                "duration_histogram": self.get_histogram_stats("publication_duration_ms")
            },
            "api": {
                "request_duration_histogram": self.get_histogram_stats("api_request_duration_ms")
            },
            "ai": {
                "duration_histogram": self.get_histogram_stats("ai_generation_duration_ms")
            }
        }

telemetry_service = TelemetryService.get_instance()
