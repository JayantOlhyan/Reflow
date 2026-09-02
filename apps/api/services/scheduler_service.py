import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import async_session_factory
from models.entities import Publication, PlatformConnection, Content, ContentVariant, Clip, ClipVariant, Job
from services.queue_service import queue_service
from services.publishing_service import publishing_service
from utils.logging import get_logger

logger = get_logger("SchedulerService")

class SchedulerService:
    def __init__(self):
        self.instance_id = f"sched_{uuid.uuid4().hex[:8]}"
        self._last_heartbeat: Optional[datetime] = None
        self._last_processed_pub_id: Optional[str] = None
        self._last_lag_seconds: float = 0.0

    # --------------------------------------------------------------------------
    # Timezone & Date Validation
    # --------------------------------------------------------------------------

    def validate_timezone(self, tz_name: str) -> ZoneInfo:
        """Validates and returns a ZoneInfo object for standard IANA timezone names."""
        try:
            return ZoneInfo(tz_name)
        except Exception as e:
            raise ValueError(f"INVALID_TIMEZONE: '{tz_name}' is not a recognized IANA timezone.")

    def parse_and_validate_schedule_time(
        self,
        local_iso_time: str,
        tz_name: str,
        min_lead_seconds: int = 60,
        enforce_future: bool = True
    ) -> Tuple[datetime, datetime]:
        """
        Parses a local ISO datetime string and converts it to canonical UTC datetime.
        Enforces that scheduled time is in the future with minimum lead time.
        Returns (scheduled_at_utc, local_datetime).
        """
        zi = self.validate_timezone(tz_name)

        # Parse ISO string
        try:
            # Handle standard ISO formats (e.g. 2026-09-10T14:30:00 or 2026-09-10 14:30:00)
            clean_str = local_iso_time.strip().replace(" ", "T")
            if clean_str.endswith("Z"):
                clean_str = clean_str[:-1]
            # Strip off existing timezone offsets if user provided local time string
            if "+" in clean_str:
                clean_str = clean_str.split("+")[0]
            elif "-" in clean_str and clean_str.count("-") > 2: # Has negative offset
                clean_str = clean_str.rsplit("-", 1)[0]

            dt_naive = datetime.fromisoformat(clean_str)
        except Exception as e:
            raise ValueError(f"INVALID_DATETIME_FORMAT: Could not parse '{local_iso_time}' as ISO 8601.")

        # Localize to target timezone
        local_dt = dt_naive.replace(tzinfo=zi)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None) # naive UTC for database

        now_utc = datetime.utcnow()
        if enforce_future:
            if utc_dt <= now_utc:
                raise ValueError(f"SCHEDULE_TIME_IN_PAST: Scheduled time {utc_dt.isoformat()}Z is in the past (Current UTC: {now_utc.isoformat()}Z).")
            
            lead_threshold = now_utc + timedelta(seconds=min_lead_seconds)
            if utc_dt < lead_threshold:
                raise ValueError(f"MINIMUM_LEAD_TIME_VIOLATION: Scheduled time must be at least {min_lead_seconds} seconds in the future.")

        return utc_dt, local_dt

    # --------------------------------------------------------------------------
    # Scheduling Operations
    # --------------------------------------------------------------------------

    async def schedule_publications(
        self,
        content_id: str,
        destinations: List[Dict[str, Any]],
        scheduled_time_str: str,
        timezone_name: str,
        variant_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Publication]:
        """
        Creates and persists scheduled publication records in PostgreSQL with status=SCHEDULED.
        Validates content existence, variant existence, platform connection, and per-platform metadata.
        """
        if not destinations:
            raise ValueError("At least one target destination is required.")

        utc_time, _ = self.parse_and_validate_schedule_time(
            scheduled_time_str,
            timezone_name,
            min_lead_seconds=settings.SCHEDULER_MIN_LEAD_SECONDS
        )

        # 1. Verify Content
        res_cnt = await db.execute(select(Content).where(Content.id == content_id))
        content = res_cnt.scalar_one_or_none()
        if not content:
            raise ValueError(f"Content {content_id} not found.")

        # 2. Verify Variant if specified
        if variant_id:
            res_v = await db.execute(select(ContentVariant).where(ContentVariant.id == variant_id))
            var_item = res_v.scalar_one_or_none()
            if not var_item:
                res_cv = await db.execute(select(ClipVariant).where(ClipVariant.id == variant_id))
                var_item = res_cv.scalar_one_or_none()
            if not var_item:
                logger.warning(f"Variant ID {variant_id} specified but not found; proceeding with content primary asset.")

        created_publications: List[Publication] = []

        for dest in destinations:
            conn_id = dest.get("platform_connection_id")
            res_conn = await db.execute(select(PlatformConnection).where(PlatformConnection.id == conn_id))
            conn = res_conn.scalar_one_or_none()
            if not conn:
                raise ValueError(f"Platform connection {conn_id} not found.")

            title = (dest.get("title") or content.title or "Reflow Post").strip()
            desc = (dest.get("description") or "").strip()
            privacy = (dest.get("privacy") or "PRIVATE").upper()
            tags = dest.get("tags") or []

            # Connector pre-flight metadata validation
            connector = publishing_service.get_connector(conn.platform)
            if connector:
                valid, err = connector.validate_metadata({
                    "title": title,
                    "description": desc,
                    "caption": desc,
                    "tags": tags,
                    "privacy": privacy
                })
                if not valid:
                    raise ValueError(f"VALIDATION_ERROR for {conn.platform}: {err}")

            payload_hash = publishing_service.compute_idempotency_hash(
                content_id=content_id,
                variant_id=variant_id,
                platform_connection_id=conn.id,
                title=title,
                privacy=privacy
            )

            # Check existing active schedule or queued publication
            existing_res = await db.execute(
                select(Publication).where(
                    Publication.request_payload_hash == payload_hash,
                    Publication.status.in_(["SCHEDULED", "QUEUED", "UPLOADING", "PUBLISHED"])
                )
            )
            existing_pub = existing_res.scalars().first()
            if existing_pub:
                logger.info(f"Matched existing publication {existing_pub.id} for scheduled request.")
                created_publications.append(existing_pub)
                continue

            pub_id = f"pub_sch_{uuid.uuid4().hex[:10]}"
            pub = Publication(
                id=pub_id,
                content_id=content_id,
                variant_id=variant_id,
                platform_connection_id=conn.id,
                platform=conn.platform,
                status="SCHEDULED",
                title=title,
                description=desc,
                privacy=privacy,
                tags_json=json.dumps(tags),
                request_payload_hash=payload_hash,
                scheduled_at=utc_time,
                timezone=timezone_name,
                created_at=datetime.utcnow()
            )
            db.add(pub)
            created_publications.append(pub)

        await db.commit()
        for p in created_publications:
            await db.refresh(p)

        logger.info(f"Successfully scheduled {len(created_publications)} publication(s) for {utc_time.isoformat()}Z ({timezone_name}).")
        return created_publications

    # --------------------------------------------------------------------------
    # Scheduler Tick: Atomic Claiming & Dispatching
    # --------------------------------------------------------------------------

    async def claim_due_publications(self, limit: int = 50) -> List[str]:
        """
        Atomically queries and claims publications that are SCHEDULED and due (scheduled_at <= now).
        Acquires lease ownership using claimed_at and claim_owner.
        """
        now_utc = datetime.utcnow()
        claimed_ids = []

        async with async_session_factory() as session:
            # Query due publications that are not currently claimed under an active lease
            lease_threshold = now_utc - timedelta(seconds=settings.SCHEDULER_CLAIM_LEASE_SECONDS)
            stmt = (
                select(Publication.id)
                .where(
                    Publication.status == "SCHEDULED",
                    Publication.scheduled_at <= now_utc,
                    or_(
                        Publication.claimed_at == None,
                        Publication.claimed_at < lease_threshold
                    )
                )
                .order_by(Publication.scheduled_at.asc())
                .limit(limit)
            )

            res = await session.execute(stmt)
            candidate_ids = res.scalars().all()

            if not candidate_ids:
                return []

            # Atomically claim candidates checking claimed_at condition
            claimed_ids = []
            for pub_id in candidate_ids:
                claim_stmt = (
                    update(Publication)
                    .where(
                        Publication.id == pub_id,
                        Publication.status == "SCHEDULED",
                        or_(
                            Publication.claimed_at == None,
                            Publication.claimed_at < lease_threshold
                        )
                    )
                    .values(
                        claimed_at=now_utc,
                        claim_owner=self.instance_id,
                        updated_at=now_utc
                    )
                )
                res_claim = await session.execute(claim_stmt)
                if res_claim.rowcount > 0:
                    claimed_ids.append(pub_id)
            await session.commit()

        if claimed_ids:
            logger.info(f"Scheduler '{self.instance_id}' atomically claimed {len(claimed_ids)} due publication(s).")
        return claimed_ids

    async def dispatch_claimed_publications(self, claimed_ids: List[str]) -> int:
        """
        Transitions claimed publications from SCHEDULED -> QUEUED, creates PLATFORM_PUBLISH Jobs,
        and enqueues them into Redis / fallback queue.
        """
        if not claimed_ids:
            return 0

        dispatched_count = 0
        now_utc = datetime.utcnow()

        async with async_session_factory() as session:
            for pub_id in claimed_ids:
                res = await session.execute(select(Publication).where(Publication.id == pub_id))
                pub = res.scalar_one_or_none()
                if not pub or pub.status != "SCHEDULED":
                    continue

                # Calculate lag metrics
                if pub.scheduled_at:
                    lag = (now_utc - pub.scheduled_at).total_seconds()
                    self._last_lag_seconds = max(0.0, lag)

                # Check missed-schedule policy (e.g. if server was offline for > 2 hours)
                if pub.scheduled_at and (now_utc - pub.scheduled_at).total_seconds() > 7200:
                    if settings.SCHEDULER_MISSED_POLICY == "MARK_FAILED":
                        pub.status = "FAILED"
                        pub.error_code = "MISSED_SCHEDULE"
                        pub.error_message = f"Publication missed its scheduled window by {(now_utc - pub.scheduled_at).total_seconds() / 60:.1f} minutes."
                        pub.failed_at = now_utc
                        await session.commit()
                        logger.warning(f"Marked missed publication {pub.id} as FAILED per policy.")
                        continue

                # Transition to QUEUED
                pub.status = "QUEUED"
                pub.claimed_at = None
                pub.claim_owner = None
                pub.updated_at = now_utc

                # Create Job
                job_id = f"job_sch_{uuid.uuid4().hex[:8]}"
                job = Job(
                    id=job_id,
                    content_id=pub.content_id,
                    type="PLATFORM_PUBLISH",
                    status="QUEUED",
                    created_at=now_utc
                )
                session.add(job)
                await session.commit()

                # Push to Queue
                await queue_service.enqueue_media_job(
                    job_id=job_id,
                    content_id=pub.content_id,
                    job_type="PLATFORM_PUBLISH",
                    publication_id=pub.id
                )

                self._last_processed_pub_id = pub.id
                dispatched_count += 1
                logger.info(f"Dispatched scheduled publication {pub.id} to queue (Job {job_id}, Platform: {pub.platform}).")

        return dispatched_count

    async def recover_stale_claims(self) -> int:
        """
        Recovers publications that were claimed by a crashed scheduler instance
        whose lease has expired without completing job queueing.
        """
        now_utc = datetime.utcnow()
        lease_threshold = now_utc - timedelta(seconds=settings.SCHEDULER_CLAIM_LEASE_SECONDS)

        async with async_session_factory() as session:
            stmt = (
                update(Publication)
                .where(
                    Publication.status == "SCHEDULED",
                    Publication.claimed_at != None,
                    Publication.claimed_at < lease_threshold
                )
                .values(
                    claimed_at=None,
                    claim_owner=None,
                    updated_at=now_utc
                )
            )
            res = await session.execute(stmt)
            await session.commit()
            count = res.rowcount or 0

        if count > 0:
            logger.warning(f"Recovered {count} stale scheduled publication claim(s).")
        return count

    # --------------------------------------------------------------------------
    # Modification & Cancellation
    # --------------------------------------------------------------------------

    async def reschedule_publication(
        self,
        publication_id: str,
        new_time_str: str,
        timezone_name: Optional[str] = None,
        db: AsyncSession = None
    ) -> Publication:
        """Reschedules an existing publication while in SCHEDULED or DRAFT state."""
        res = await db.execute(select(Publication).where(Publication.id == publication_id))
        pub = res.scalar_one_or_none()
        if not pub:
            raise ValueError(f"Publication {publication_id} not found.")

        if pub.status not in ["SCHEDULED", "DRAFT"]:
            raise ValueError(f"Cannot reschedule publication in '{pub.status}' state. Only pending SCHEDULED posts can be rescheduled.")

        target_tz = timezone_name or pub.timezone or "UTC"
        utc_time, _ = self.parse_and_validate_schedule_time(
            new_time_str,
            target_tz,
            min_lead_seconds=settings.SCHEDULER_MIN_LEAD_SECONDS
        )

        pub.scheduled_at = utc_time
        pub.timezone = target_tz
        pub.status = "SCHEDULED"
        pub.claimed_at = None
        pub.claim_owner = None
        pub.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(pub)
        logger.info(f"Rescheduled publication {publication_id} to {utc_time.isoformat()}Z ({target_tz}).")
        return pub

    async def cancel_publication(
        self,
        publication_id: str,
        db: AsyncSession = None
    ) -> Publication:
        """Cancels a pending scheduled or queued publication."""
        res = await db.execute(select(Publication).where(Publication.id == publication_id))
        pub = res.scalar_one_or_none()
        if not pub:
            raise ValueError(f"Publication {publication_id} not found.")

        if pub.status in ["PUBLISHED", "UPLOADING", "PUBLISHING"]:
            raise ValueError(f"Cannot cancel publication in '{pub.status}' state.")

        pub.status = "CANCELLED"
        pub.cancelled_at = datetime.utcnow()
        pub.claimed_at = None
        pub.claim_owner = None
        pub.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(pub)
        logger.info(f"Cancelled publication {publication_id}.")
        return pub

    # --------------------------------------------------------------------------
    # Calendar Range Query
    # --------------------------------------------------------------------------

    async def get_calendar_events(
        self,
        start_utc: datetime,
        end_utc: datetime,
        view_timezone: str = "UTC",
        platform: Optional[str] = None,
        status: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Queries all publications scheduled or published within a specific UTC time range.
        Converts timestamps to the viewer's target timezone for display.
        """
        zi = self.validate_timezone(view_timezone)

        query = (
            select(Publication, Content, PlatformConnection)
            .join(Content, Publication.content_id == Content.id, isouter=True)
            .join(PlatformConnection, Publication.platform_connection_id == PlatformConnection.id, isouter=True)
            .where(
                or_(
                    and_(Publication.scheduled_at >= start_utc, Publication.scheduled_at <= end_utc),
                    and_(Publication.published_at >= start_utc, Publication.published_at <= end_utc)
                )
            )
            .order_by(Publication.scheduled_at.asc().nullslast(), Publication.created_at.asc())
        )

        if platform:
            query = query.where(Publication.platform == platform.lower())
        if status:
            query = query.where(Publication.status == status.upper())

        res = await db.execute(query)
        rows = res.all()

        events = []
        for pub, content, conn in rows:
            target_time_utc = pub.scheduled_at or pub.published_at or pub.created_at
            
            # Localize time to view timezone
            if target_time_utc:
                local_dt = target_time_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(zi)
                local_time_str = local_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                local_time_str = ""

            events.append({
                "id": f"event_{pub.id}",
                "publication_id": pub.id,
                "content_id": pub.content_id,
                "content_title": content.title if content else "Untitled Content",
                "content_type": content.content_type if content else "UNKNOWN",
                "thumbnail_path": content.thumbnail_path if content else None,
                "variant_id": pub.variant_id,
                "platform": pub.platform,
                "platform_connection_id": pub.platform_connection_id,
                "account_name": conn.account_name if conn else "",
                "handle": conn.handle if conn else "",
                "status": pub.status,
                "title": pub.title,
                "description": pub.description or "",
                "privacy": pub.privacy,
                "scheduled_at": pub.scheduled_at or target_time_utc,
                "scheduled_at_local": local_time_str,
                "timezone": pub.timezone or view_timezone,
                "published_at": pub.published_at,
                "external_post_id": pub.external_post_id,
                "external_url": pub.external_url,
                "error_code": pub.error_code,
                "error_message": pub.error_message
            })

        return events

    # --------------------------------------------------------------------------
    # Telemetry & Heartbeat
    # --------------------------------------------------------------------------

    def record_heartbeat(self):
        self._last_heartbeat = datetime.utcnow()

    def get_telemetry(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        is_healthy = False
        if self._last_heartbeat:
            is_healthy = (now - self._last_heartbeat).total_seconds() < (settings.SCHEDULER_POLL_INTERVAL_SECONDS * 4)

        return {
            "status": "HEALTHY" if is_healthy else "IDLE",
            "instance_id": self.instance_id,
            "last_heartbeat": self._last_heartbeat.isoformat() if self._last_heartbeat else None,
            "last_processed_pub_id": self._last_processed_pub_id,
            "lag_seconds": round(self._last_lag_seconds, 2)
        }

scheduler_service = SchedulerService()
