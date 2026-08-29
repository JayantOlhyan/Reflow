import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import async_session_factory
from models.entities import Publication, PostMetricSnapshot, PlatformConnection, Content, ContentVariant, Clip, Carousel, Job
from services.publishing_service import publishing_service
from services.queue_service import queue_service
from utils.logging import get_logger

logger = get_logger("AnalyticsService")

class AnalyticsService:

    # --------------------------------------------------------------------------
    # Metric Normalization & Calculations
    # --------------------------------------------------------------------------

    def calculate_engagement_rate(
        self,
        likes: Optional[int],
        comments: Optional[int],
        shares: Optional[int],
        saves: Optional[int],
        reach: Optional[int],
        impressions: Optional[int]
    ) -> Optional[float]:
        """
        Calculates engagement rate percentage: (likes + comments + shares + saves) / (reach or impressions).
        Returns None (Unavailable) if denominator is None or <= 0 (Strict zero division protection).
        """
        denominator = reach if (reach is not None and reach > 0) else (impressions if (impressions is not None and impressions > 0) else None)
        if denominator is None or denominator <= 0:
            return None

        numerator = (likes or 0) + (comments or 0) + (shares or 0) + (saves or 0)
        return round((numerator / denominator) * 100.0, 2)

    def calculate_view_rate(self, views: Optional[int], impressions: Optional[int]) -> Optional[float]:
        """Calculates views / impressions rate percentage."""
        if impressions is None or impressions <= 0 or views is None:
            return None
        return round((views / impressions) * 100.0, 2)

    def normalize_metrics(self, platform: str, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes raw platform-specific dictionary into Reflow standard dimensions.
        Strictly preserves None for unavailable fields.
        """
        views = raw_metrics.get("views")
        impressions = raw_metrics.get("impressions")
        reach = raw_metrics.get("reach")
        likes = raw_metrics.get("likes")
        comments = raw_metrics.get("comments")
        shares = raw_metrics.get("shares")
        saves = raw_metrics.get("saves")
        clicks = raw_metrics.get("clicks")
        reposts = raw_metrics.get("reposts")
        replies = raw_metrics.get("replies")
        watch_time = raw_metrics.get("watch_time_seconds")
        avg_watch_time = raw_metrics.get("average_watch_time_seconds")
        completion_rate = raw_metrics.get("completion_rate")
        followers_gained = raw_metrics.get("followers_gained")

        # Compute total engagements if any engagement metric is present
        eng_components = [likes, comments, shares, saves, clicks, reposts, replies]
        has_eng = any(c is not None for c in eng_components)
        engagements = sum(c for c in eng_components if c is not None) if has_eng else None

        return {
            "views": int(views) if views is not None else None,
            "impressions": int(impressions) if impressions is not None else None,
            "reach": int(reach) if reach is not None else None,
            "likes": int(likes) if likes is not None else None,
            "comments": int(comments) if comments is not None else None,
            "shares": int(shares) if shares is not None else None,
            "saves": int(saves) if saves is not None else None,
            "clicks": int(clicks) if clicks is not None else None,
            "reposts": int(reposts) if reposts is not None else None,
            "replies": int(replies) if replies is not None else None,
            "engagements": engagements,
            "watch_time_seconds": float(watch_time) if watch_time is not None else None,
            "average_watch_time_seconds": float(avg_watch_time) if avg_watch_time is not None else None,
            "completion_rate": float(completion_rate) if completion_rate is not None else None,
            "followers_gained": int(followers_gained) if followers_gained is not None else None
        }

    # --------------------------------------------------------------------------
    # Sync Execution & Snapshot Creation
    # --------------------------------------------------------------------------

    async def sync_publication_metrics(
        self,
        publication_id: str,
        db: AsyncSession = None
    ) -> Optional[PostMetricSnapshot]:
        """
        Synchronizes live post metrics from the social platform API for a single Publication.
        Creates a new immutable PostMetricSnapshot row.
        """
        async with async_session_factory() as session:
            res = await session.execute(select(Publication).where(Publication.id == publication_id))
            pub = res.scalar_one_or_none()
            if not pub:
                logger.warning(f"Publication {publication_id} not found for analytics sync.")
                return None

            if pub.status != "PUBLISHED" or not pub.external_post_id:
                logger.info(f"Publication {publication_id} is not PUBLISHED or missing external_post_id (Status: {pub.status}).")
                pub.analytics_status = "UNAVAILABLE"
                pub.last_analytics_sync_at = datetime.utcnow()
                await session.commit()
                return None

            # Get Platform Connection & Token
            token = ""
            if pub.platform_connection_id:
                c_res = await session.execute(
                    select(PlatformConnection).where(PlatformConnection.id == pub.platform_connection_id)
                )
                conn = c_res.scalar_one_or_none()
                if conn:
                    if conn.status != "CONNECTED":
                        pub.analytics_status = "REAUTH_REQUIRED"
                        pub.analytics_error_code = "CONNECTION_NOT_CONNECTED"
                        pub.analytics_error_message = f"Platform connection is in '{conn.status}' state."
                        pub.last_analytics_sync_at = datetime.utcnow()
                        await session.commit()
                        return None

                    try:
                        token = await publishing_service.get_valid_access_token(conn, session)
                    except Exception as te:
                        logger.error(f"Failed to obtain valid access token for {pub.platform}: {te}")
                        pub.analytics_status = "REAUTH_REQUIRED"
                        pub.analytics_error_code = "TOKEN_REFRESH_FAILED"
                        pub.analytics_error_message = str(te)
                        pub.last_analytics_sync_at = datetime.utcnow()
                        await session.commit()
                        return None

            connector = publishing_service.get_connector(pub.platform)
            if not connector:
                pub.analytics_status = "UNAVAILABLE"
                pub.last_analytics_sync_at = datetime.utcnow()
                await session.commit()
                return None

            caps = connector.get_capabilities()
            if not caps.supports_analytics:
                pub.analytics_status = "UNAVAILABLE"
                pub.last_analytics_sync_at = datetime.utcnow()
                await session.commit()
                return None

            pub.analytics_status = "SYNCING"
            await session.commit()

            # Execute fetch via connector
            try:
                raw_metrics = await connector.get_post_metrics(
                    external_post_id=pub.external_post_id,
                    access_token=token
                )
            except ValueError as ve:
                err_str = str(ve)
                if "REAUTH_REQUIRED" in err_str:
                    pub.analytics_status = "REAUTH_REQUIRED"
                    pub.analytics_error_code = "AUTH_FAILED"
                elif "RATE_LIMITED" in err_str:
                    pub.analytics_status = "FAILED"
                    pub.analytics_error_code = "RATE_LIMITED"
                else:
                    pub.analytics_status = "FAILED"
                    pub.analytics_error_code = "ANALYTICS_FETCH_ERROR"
                pub.analytics_error_message = err_str
                pub.last_analytics_sync_at = datetime.utcnow()
                await session.commit()
                return None
            except Exception as e:
                logger.error(f"Analytics connector fetch error for {pub.id} ({pub.platform}): {e}")
                pub.analytics_status = "FAILED"
                pub.analytics_error_code = "ANALYTICS_PROVIDER_RESPONSE_INVALID"
                pub.analytics_error_message = str(e)
                pub.last_analytics_sync_at = datetime.utcnow()
                await session.commit()
                return None

            if raw_metrics is None:
                pub.analytics_status = "UNAVAILABLE"
                pub.last_analytics_sync_at = datetime.utcnow()
                await session.commit()
                return None

            # Normalize dimensions
            norm = self.normalize_metrics(pub.platform, raw_metrics)

            snap_id = f"snap_{uuid.uuid4().hex[:10]}"
            now_utc = datetime.utcnow()

            snapshot = PostMetricSnapshot(
                id=snap_id,
                publication_id=pub.id,
                platform=pub.platform,
                external_post_id=pub.external_post_id,
                captured_at=now_utc,
                views=norm["views"],
                impressions=norm["impressions"],
                reach=norm["reach"],
                likes=norm["likes"],
                comments=norm["comments"],
                shares=norm["shares"],
                saves=norm["saves"],
                clicks=norm["clicks"],
                reposts=norm["reposts"],
                replies=norm["replies"],
                engagements=norm["engagements"],
                watch_time_seconds=norm["watch_time_seconds"],
                average_watch_time_seconds=norm["average_watch_time_seconds"],
                completion_rate=norm["completion_rate"],
                followers_gained=norm["followers_gained"],
                raw_metrics_json=json.dumps(raw_metrics.get("raw", raw_metrics)),
                created_at=now_utc
            )
            session.add(snapshot)

            # Determine status (PARTIAL or AVAILABLE)
            has_views = norm["views"] is not None or norm["impressions"] is not None
            has_eng = norm["engagements"] is not None or norm["likes"] is not None
            if has_views and has_eng:
                pub.analytics_status = "AVAILABLE"
            elif has_views or has_eng:
                pub.analytics_status = "PARTIAL"
            else:
                pub.analytics_status = "AVAILABLE"

            pub.last_analytics_sync_at = now_utc
            pub.analytics_error_code = None
            pub.analytics_error_message = None

            await session.commit()
            await session.refresh(snapshot)
            logger.info(f"Created metric snapshot {snap_id} for Publication {pub.id} ({pub.platform}). Views: {norm['views']}, Likes: {norm['likes']}.")
            return snapshot

    # --------------------------------------------------------------------------
    # Aggregation & Overview Queries
    # --------------------------------------------------------------------------

    async def get_overview_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Computes aggregated KPI metrics and period comparison (Current Period vs Previous Period).
        """
        # Current Period
        current_stats = await self._calculate_period_stats(start_date, end_date, platform, content_type, db)

        # Previous Equivalent Period
        duration = end_date - start_date
        prev_end = start_date
        prev_start = prev_end - duration
        prev_stats = await self._calculate_period_stats(prev_start, prev_end, platform, content_type, db)

        # Compute percentage deltas
        comparison = {}
        for key in ["total_publications", "total_views", "total_engagements", "total_impressions"]:
            cur_val = current_stats.get(key)
            prv_val = prev_stats.get(key)
            if prv_val is not None and prv_val > 0 and cur_val is not None:
                pct = round(((cur_val - prv_val) / prv_val) * 100.0, 1)
                comparison[f"{key}_change_pct"] = pct
            else:
                comparison[f"{key}_change_pct"] = None # N/A or unavailable

        return {
            **current_stats,
            "period_comparison": comparison,
            "start_date": start_date,
            "end_date": end_date,
            "last_synced_at": datetime.utcnow()
        }

    async def _calculate_period_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[str],
        content_type: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        query = (
            select(Publication, Content)
            .join(Content, Publication.content_id == Content.id, isouter=True)
            .where(
                Publication.status == "PUBLISHED",
                Publication.published_at >= start_date,
                Publication.published_at <= end_date
            )
        )
        if platform:
            query = query.where(Publication.platform == platform.lower())
        if content_type:
            query = query.where(Content.content_type == content_type.upper())

        res = await db.execute(query)
        rows = res.all()

        pub_count = len(rows)
        if pub_count == 0:
            return {
                "total_publications": 0,
                "total_views": None,
                "total_impressions": None,
                "total_reach": None,
                "total_engagements": None,
                "average_engagement_rate": None,
                "average_views_per_publication": None
            }

        total_views = 0
        has_views_data = False
        total_impressions = 0
        has_impressions_data = False
        total_reach = 0
        has_reach_data = False
        total_engagements = 0
        has_eng_data = False
        eng_rate_accum = []

        for pub, cnt in rows:
            # Fetch latest snapshot for this publication
            snap_res = await db.execute(
                select(PostMetricSnapshot)
                .where(PostMetricSnapshot.publication_id == pub.id)
                .order_by(PostMetricSnapshot.captured_at.desc())
                .limit(1)
            )
            snap = snap_res.scalar_one_or_none()
            if snap:
                if snap.views is not None:
                    total_views += snap.views
                    has_views_data = True
                if snap.impressions is not None:
                    total_impressions += snap.impressions
                    has_impressions_data = True
                if snap.reach is not None:
                    total_reach += snap.reach
                    has_reach_data = True
                if snap.engagements is not None:
                    total_engagements += snap.engagements
                    has_eng_data = True

                rate = self.calculate_engagement_rate(
                    likes=snap.likes,
                    comments=snap.comments,
                    shares=snap.shares,
                    saves=snap.saves,
                    reach=snap.reach,
                    impressions=snap.impressions
                )
                if rate is not None:
                    eng_rate_accum.append(rate)

        avg_eng_rate = round(sum(eng_rate_accum) / len(eng_rate_accum), 2) if eng_rate_accum else None
        avg_views = round(total_views / pub_count, 1) if has_views_data else None

        return {
            "total_publications": pub_count,
            "total_views": total_views if has_views_data else None,
            "total_impressions": total_impressions if has_impressions_data else None,
            "total_reach": total_reach if has_reach_data else None,
            "total_engagements": total_engagements if has_eng_data else None,
            "average_engagement_rate": avg_eng_rate,
            "average_views_per_publication": avg_views
        }

    # --------------------------------------------------------------------------
    # Timeseries & Trend Query
    # --------------------------------------------------------------------------

    async def get_timeseries_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """Aggregates daily performance buckets across the date range."""
        days_map: Dict[str, Dict[str, Any]] = {}
        curr = start_date.date()
        end_d = end_date.date()

        while curr <= end_d:
            d_str = curr.isoformat()
            days_map[d_str] = {
                "date": d_str,
                "views": None,
                "engagements": None,
                "publications_count": 0
            }
            curr += timedelta(days=1)

        query = (
            select(Publication)
            .where(
                Publication.status == "PUBLISHED",
                Publication.published_at >= start_date,
                Publication.published_at <= end_date
            )
        )
        if platform:
            query = query.where(Publication.platform == platform.lower())

        res = await db.execute(query)
        pubs = res.scalars().all()

        for pub in pubs:
            if not pub.published_at:
                continue
            d_str = pub.published_at.date().isoformat()
            if d_str in days_map:
                days_map[d_str]["publications_count"] += 1

                # Get latest snapshot
                snap_res = await db.execute(
                    select(PostMetricSnapshot)
                    .where(PostMetricSnapshot.publication_id == pub.id)
                    .order_by(PostMetricSnapshot.captured_at.desc())
                    .limit(1)
                )
                snap = snap_res.scalar_one_or_none()
                if snap:
                    if snap.views is not None:
                        days_map[d_str]["views"] = (days_map[d_str]["views"] or 0) + snap.views
                    if snap.engagements is not None:
                        days_map[d_str]["engagements"] = (days_map[d_str]["engagements"] or 0) + snap.engagements

        return list(days_map.values())

    # --------------------------------------------------------------------------
    # Platform & Content Breakdown Queries
    # --------------------------------------------------------------------------

    async def get_platform_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """Returns per-platform metrics breakdown."""
        platforms = ["youtube", "instagram", "linkedin", "x", "facebook", "tiktok", "pinterest", "threads"]
        result = []

        for p in platforms:
            connector = publishing_service.get_connector(p)
            caps = connector.get_capabilities() if connector else None

            query = (
                select(Publication)
                .where(
                    Publication.platform == p,
                    Publication.status == "PUBLISHED",
                    Publication.published_at >= start_date,
                    Publication.published_at <= end_date
                )
            )
            res = await db.execute(query)
            pubs = res.scalars().all()

            if not pubs and not (caps and caps.supports_analytics):
                continue

            total_views = None
            total_impressions = None
            total_engagements = None
            eng_rates = []

            for pub in pubs:
                snap_res = await db.execute(
                    select(PostMetricSnapshot)
                    .where(PostMetricSnapshot.publication_id == pub.id)
                    .order_by(PostMetricSnapshot.captured_at.desc())
                    .limit(1)
                )
                snap = snap_res.scalar_one_or_none()
                if snap:
                    if snap.views is not None:
                        total_views = (total_views or 0) + snap.views
                    if snap.impressions is not None:
                        total_impressions = (total_impressions or 0) + snap.impressions
                    if snap.engagements is not None:
                        total_engagements = (total_engagements or 0) + snap.engagements

                    rate = self.calculate_engagement_rate(
                        likes=snap.likes,
                        comments=snap.comments,
                        shares=snap.shares,
                        saves=snap.saves,
                        reach=snap.reach,
                        impressions=snap.impressions
                    )
                    if rate is not None:
                        eng_rates.append(rate)

            avg_rate = round(sum(eng_rates) / len(eng_rates), 2) if eng_rates else None

            result.append({
                "platform": p,
                "publication_count": len(pubs),
                "total_views": total_views,
                "total_impressions": total_impressions,
                "total_engagements": total_engagements,
                "engagement_rate": avg_rate,
                "supports_analytics": bool(caps and caps.supports_analytics),
                "supported_metrics": caps.supported_metrics if caps else []
            })

        return result

    async def get_content_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        content_type: Optional[str] = None,
        sort_by: str = "views",
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """Returns performance attributed to Source Content and Variants."""
        query = (
            select(Content)
            .join(Publication, Publication.content_id == Content.id)
            .where(
                Publication.status == "PUBLISHED",
                Publication.published_at >= start_date,
                Publication.published_at <= end_date
            )
            .distinct()
        )
        if content_type:
            query = query.where(Content.content_type == content_type.upper())

        res = await db.execute(query)
        contents = res.scalars().all()

        items = []
        for cnt in contents:
            # Fetch all publications for this content
            p_res = await db.execute(
                select(Publication).where(
                    Publication.content_id == cnt.id,
                    Publication.status == "PUBLISHED"
                )
            )
            pubs = p_res.scalars().all()

            platforms = list(set(p.platform for p in pubs))
            total_views = None
            total_engagements = None
            eng_rates = []
            latest_pub_at = None

            for p in pubs:
                if p.published_at and (latest_pub_at is None or p.published_at > latest_pub_at):
                    latest_pub_at = p.published_at

                snap_res = await db.execute(
                    select(PostMetricSnapshot)
                    .where(PostMetricSnapshot.publication_id == p.id)
                    .order_by(PostMetricSnapshot.captured_at.desc())
                    .limit(1)
                )
                snap = snap_res.scalar_one_or_none()
                if snap:
                    if snap.views is not None:
                        total_views = (total_views or 0) + snap.views
                    if snap.engagements is not None:
                        total_engagements = (total_engagements or 0) + snap.engagements

                    rate = self.calculate_engagement_rate(
                        likes=snap.likes,
                        comments=snap.comments,
                        shares=snap.shares,
                        saves=snap.saves,
                        reach=snap.reach,
                        impressions=snap.impressions
                    )
                    if rate is not None:
                        eng_rates.append(rate)

            avg_rate = round(sum(eng_rates) / len(eng_rates), 2) if eng_rates else None

            items.append({
                "content_id": cnt.id,
                "title": cnt.title or "Untitled Content",
                "content_type": cnt.content_type,
                "thumbnail_path": cnt.thumbnail_path,
                "publication_count": len(pubs),
                "platforms": platforms,
                "total_views": total_views,
                "total_engagements": total_engagements,
                "engagement_rate": avg_rate,
                "top_platform": platforms[0] if platforms else None,
                "latest_published_at": latest_pub_at
            })

        # Sort
        if sort_by == "engagement_rate":
            items.sort(key=lambda x: (x["engagement_rate"] is not None, x["engagement_rate"] or 0), reverse=True)
        elif sort_by == "engagements":
            items.sort(key=lambda x: (x["total_engagements"] is not None, x["total_engagements"] or 0), reverse=True)
        else:
            items.sort(key=lambda x: (x["total_views"] is not None, x["total_views"] or 0), reverse=True)

        return items

    # --------------------------------------------------------------------------
    # Single Publication Drill-down & Velocity
    # --------------------------------------------------------------------------

    async def get_publication_analytics(
        self,
        publication_id: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Returns single publication analytics, snapshot history, and velocity."""
        res = await db.execute(
            select(Publication, Content)
            .join(Content, Publication.content_id == Content.id, isouter=True)
            .where(Publication.id == publication_id)
        )
        row = res.first()
        if not row:
            raise ValueError(f"Publication {publication_id} not found.")

        pub, content = row

        snap_res = await db.execute(
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.publication_id == publication_id)
            .order_by(PostMetricSnapshot.captured_at.asc())
        )
        snapshots = snap_res.scalars().all()

        latest_snap = snapshots[-1] if snapshots else None

        # Calculate growth velocities
        views_per_hour = None
        eng_per_hour = None
        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]
            hours = (last.captured_at - first.captured_at).total_seconds() / 3600.0
            if hours >= 0.05: # At least 3 minutes delta
                if last.views is not None and first.views is not None:
                    views_per_hour = round(max(0.0, (last.views - first.views) / hours), 1)
                if last.engagements is not None and first.engagements is not None:
                    eng_per_hour = round(max(0.0, (last.engagements - first.engagements) / hours), 1)

        # Check staleness
        now_utc = datetime.utcnow()
        is_stale = False
        if latest_snap:
            is_stale = (now_utc - latest_snap.captured_at).total_seconds() > (settings.ANALYTICS_STALE_AFTER_HOURS * 3600)

        return {
            "publication": pub,
            "content_title": content.title if content else "Untitled Content",
            "content_type": content.content_type if content else "UNKNOWN",
            "latest_snapshot": latest_snap,
            "snapshot_count": len(snapshots),
            "snapshots": snapshots,
            "views_per_hour": views_per_hour,
            "engagements_per_hour": eng_per_hour,
            "is_stale": is_stale
        }

    # --------------------------------------------------------------------------
    # Backfill & CSV Export
    # --------------------------------------------------------------------------

    async def backfill_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platform: Optional[str] = None,
        limit: int = 50,
        db: AsyncSession = None
    ) -> int:
        """Enqueues ANALYTICS_SYNC jobs for historical published posts within a controlled window."""
        now_utc = datetime.utcnow()
        s_date = start_date or (now_utc - timedelta(days=30))
        e_date = end_date or now_utc

        query = (
            select(Publication)
            .where(
                Publication.status == "PUBLISHED",
                Publication.external_post_id != None,
                Publication.published_at >= s_date,
                Publication.published_at <= e_date
            )
            .order_by(Publication.published_at.desc())
            .limit(limit)
        )
        if platform:
            query = query.where(Publication.platform == platform.lower())

        res = await db.execute(query)
        pubs = res.scalars().all()

        enqueued = 0
        for pub in pubs:
            job_id = f"job_ana_{uuid.uuid4().hex[:8]}"
            job = Job(
                id=job_id,
                content_id=pub.content_id,
                type="ANALYTICS_SYNC",
                status="QUEUED",
                created_at=now_utc
            )
            db.add(job)
            await db.commit()

            await queue_service.enqueue_media_job(
                job_id=job_id,
                content_id=pub.content_id,
                job_type="ANALYTICS_SYNC",
                publication_id=pub.id
            )
            enqueued += 1

        logger.info(f"Enqueued {enqueued} ANALYTICS_SYNC backfill jobs.")
        return enqueued

    async def export_analytics_csv(
        self,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[str] = None,
        db: AsyncSession = None
    ) -> str:
        """Formats CSV of performance metrics with honest NULL preservation (empty strings)."""
        query = (
            select(Publication, Content)
            .join(Content, Publication.content_id == Content.id, isouter=True)
            .where(
                Publication.status == "PUBLISHED",
                Publication.published_at >= start_date,
                Publication.published_at <= end_date
            )
            .order_by(Publication.published_at.desc())
        )
        if platform:
            query = query.where(Publication.platform == platform.lower())

        res = await db.execute(query)
        rows = res.all()

        lines = [
            "Publication ID,Content Title,Platform,Published At,External Post ID,Views,Impressions,Reach,Likes,Comments,Shares,Saves,Engagement Rate %"
        ]

        for pub, cnt in rows:
            snap_res = await db.execute(
                select(PostMetricSnapshot)
                .where(PostMetricSnapshot.publication_id == pub.id)
                .order_by(PostMetricSnapshot.captured_at.desc())
                .limit(1)
            )
            snap = snap_res.scalar_one_or_none()

            v = str(snap.views) if (snap and snap.views is not None) else ""
            imp = str(snap.impressions) if (snap and snap.impressions is not None) else ""
            r = str(snap.reach) if (snap and snap.reach is not None) else ""
            l = str(snap.likes) if (snap and snap.likes is not None) else ""
            c = str(snap.comments) if (snap and snap.comments is not None) else ""
            sh = str(snap.shares) if (snap and snap.shares is not None) else ""
            sv = str(snap.saves) if (snap and snap.saves is not None) else ""
            
            rate_str = ""
            if snap:
                rate = self.calculate_engagement_rate(snap.likes, snap.comments, snap.shares, snap.saves, snap.reach, snap.impressions)
                if rate is not None:
                    rate_str = f"{rate:.2f}%"

            title_clean = (cnt.title if cnt else "Untitled").replace(",", " ")
            pub_date = pub.published_at.isoformat() if pub.published_at else ""

            lines.append(
                f"{pub.id},{title_clean},{pub.platform},{pub_date},{pub.external_post_id or ''},{v},{imp},{r},{l},{c},{sh},{sv},{rate_str}"
            )

        return "\n".join(lines)

analytics_service = AnalyticsService()
