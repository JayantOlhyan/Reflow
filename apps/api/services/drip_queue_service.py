from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import zoneinfo

from utils.logging import get_logger

logger = get_logger("DripQueueService")

class DripQueueService:
    """
    Calculates spaced-out publication schedules (drip feeding) to prevent
    burst-posting penalties and respect social platform rate limits.
    """

    def calculate_drip_schedule(
        self,
        count: int,
        interval_hours: int = 4,
        active_hours_start: int = 9,
        active_hours_end: int = 21,
        start_time: Optional[datetime] = None,
        timezone_str: str = "UTC"
    ) -> List[datetime]:
        """
        Generates sequential UTC timestamps for 'count' items, ensuring each post
        lands within creator-specified active hours in their local timezone.
        """
        if count <= 0:
            return []

        try:
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        now = start_time or datetime.now(tz)
        if now.tzinfo is None:
            now = now.replace(tzinfo=tz)

        scheduled_times: List[datetime] = []
        current_cursor = now

        for _ in range(count):
            # Advance by interval
            current_cursor = current_cursor + timedelta(hours=interval_hours)

            # Check if outside active hours (e.g. before 9:00 or after 21:00)
            if current_cursor.hour < active_hours_start:
                # Push forward to active_hours_start today
                current_cursor = current_cursor.replace(
                    hour=active_hours_start,
                    minute=0,
                    second=0,
                    microsecond=0
                )
            elif current_cursor.hour >= active_hours_end:
                # Push forward to active_hours_start tomorrow
                tomorrow = current_cursor + timedelta(days=1)
                current_cursor = tomorrow.replace(
                    hour=active_hours_start,
                    minute=0,
                    second=0,
                    microsecond=0
                )

            # Convert to canonical UTC datetime (naive or tz-aware matching Reflow)
            utc_time = current_cursor.astimezone(zoneinfo.ZoneInfo("UTC")).replace(tzinfo=None)
            scheduled_times.append(utc_time)

        logger.info(f"Generated drip schedule for {count} posts with {interval_hours}h interval.")
        return scheduled_times

drip_queue_service = DripQueueService()
