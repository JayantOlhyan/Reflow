import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, desc, func
from database import async_session_factory
from models.entities import Notification
from utils.logging import get_logger

logger = get_logger("NotificationService")

class NotificationService:
    """Manages persistent system notifications and user alerts."""

    async def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "INFO",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> Notification:
        """Creates and persists a new system notification."""
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        async with async_session_factory() as session:
            notif = Notification(
                id=notif_id,
                type=notification_type,
                title=title,
                message=message,
                severity=severity,
                read=False,
                entity_type=entity_type,
                entity_id=entity_id,
                created_at=datetime.utcnow()
            )
            session.add(notif)
            await session.commit()
            logger.info(f"Created notification {notif_id} [{severity}] ({notification_type}): {title}")
            return notif

    async def get_notifications(self, limit: int = 50, unread_only: bool = False) -> Dict[str, Any]:
        """Fetches recent notifications and unread count."""
        async with async_session_factory() as session:
            query = select(Notification).order_by(desc(Notification.created_at)).limit(limit)
            if unread_only:
                query = query.where(Notification.read == False)
            
            res = await session.execute(query)
            items = res.scalars().all()

            count_res = await session.execute(
                select(func.count(Notification.id)).where(Notification.read == False)
            )
            unread_count = count_res.scalar() or 0

            return {
                "items": items,
                "unread_count": unread_count
            }

    async def mark_read(self, notification_id: str) -> bool:
        """Marks a single notification as read."""
        async with async_session_factory() as session:
            res = await session.execute(
                select(Notification).where(Notification.id == notification_id)
            )
            notif = res.scalar_one_or_none()
            if notif:
                notif.read = True
                await session.commit()
                return True
            return False

    async def mark_all_read(self) -> int:
        """Marks all notifications as read."""
        async with async_session_factory() as session:
            res = await session.execute(
                update(Notification).where(Notification.read == False).values(read=True)
            )
            await session.commit()
            return res.rowcount

notification_service = NotificationService()
