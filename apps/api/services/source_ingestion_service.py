import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from utils.logging import get_logger
from models.entities import InboundSource, SourceFeedItem, Content, Asset, Job
from services.podcast_ingestion_service import podcast_ingestion_service
from services.storage_service import storage_service
from services.queue_service import queue_service

logger = get_logger("SourceIngestionService")

class SourceIngestionService:
    """
    Coordinates polling and ingestion from all configured inbound sources.
    Handles deduplication, media downloading, Content entity creation,
    and automatic job dispatch.
    """

    async def poll_source(self, db: AsyncSession, source_id: str) -> Dict[str, Any]:
        """
        Polls a specific source by ID, checks for new feed items, and ingests them.
        """
        source = await db.get(InboundSource, source_id)
        if not source:
            raise ValueError(f"InboundSource '{source_id}' not found.")

        if not source.is_active:
            logger.info(f"Source '{source.name}' ({source_id}) is inactive, skipping poll.")
            return {"status": "skipped", "message": "Source is inactive", "new_items": 0}

        config = source.config
        new_items_count = 0
        ingested_items = []

        try:
            if source.source_type == "PODCAST_RSS":
                feed_url = config.get("feed_url")
                if not feed_url:
                    raise ValueError("Missing 'feed_url' in source configuration.")

                parsed_feed = await podcast_ingestion_service.fetch_and_parse_feed(feed_url, limit=config.get("max_items", 10))
                episodes = parsed_feed.get("episodes", [])

                for ep in episodes:
                    # Check if already seen
                    stmt = select(SourceFeedItem).where(
                        SourceFeedItem.source_id == source.id,
                        SourceFeedItem.external_id == ep["guid"]
                    )
                    existing = (await db.execute(stmt)).scalar_one_or_none()

                    if existing:
                        continue # Already processed

                    # Record new feed item
                    feed_item = SourceFeedItem(
                        id=f"item_{uuid.uuid4().hex[:12]}",
                        source_id=source.id,
                        external_id=ep["guid"],
                        title=ep["title"],
                        media_url=ep["media_url"],
                        description=ep.get("description", ""),
                        metadata_json=json.dumps({
                            "duration_seconds": ep.get("duration_seconds"),
                            "image_url": ep.get("image_url"),
                            "published_at_str": ep.get("published_at_str"),
                            "mime_type": ep.get("mime_type")
                        }),
                        ingestion_status="PENDING"
                    )
                    db.add(feed_item)
                    await db.flush()

                    # Ingest the item into Reflow Content
                    try:
                        content = await self._ingest_audio_item(db, source, feed_item, ep)
                        feed_item.content_id = content.id
                        feed_item.ingestion_status = "INGESTED"
                        new_items_count += 1
                        ingested_items.append({
                            "feed_item_id": feed_item.id,
                            "content_id": content.id,
                            "title": feed_item.title
                        })
                    except Exception as e:
                        logger.error(f"Failed to ingest feed item '{ep['title']}': {e}")
                        feed_item.ingestion_status = "FAILED"
                        feed_item.metadata_json = json.dumps({"error": str(e)})

                source.last_polled_at = datetime.utcnow()
                if episodes:
                    source.last_item_external_id = episodes[0]["guid"]
                await db.commit()

            elif source.source_type in ("LOCAL_FOLDER", "CLOUD_FOLDER"):
                folder_path = config.get("folder_path")
                if not folder_path or not os.path.exists(folder_path):
                    logger.warning(f"Watch folder does not exist: {folder_path}")
                    return {"status": "error", "message": f"Folder not found: {folder_path}", "new_items": 0}

                allowed_exts = (".mp4", ".mov", ".mkv", ".mp3", ".wav", ".m4a")
                files = [f for f in os.listdir(folder_path) if f.lower().endswith(allowed_exts)]

                for fname in sorted(files):
                    fpath = os.path.join(folder_path, fname)
                    file_stat = os.stat(fpath)
                    ext_id = f"{fname}_{file_stat.st_mtime}_{file_stat.st_size}"

                    stmt = select(SourceFeedItem).where(
                        SourceFeedItem.source_id == source.id,
                        SourceFeedItem.external_id == ext_id
                    )
                    existing = (await db.execute(stmt)).scalar_one_or_none()
                    if existing:
                        continue

                    feed_item = SourceFeedItem(
                        id=f"item_{uuid.uuid4().hex[:12]}",
                        source_id=source.id,
                        external_id=ext_id,
                        title=os.path.splitext(fname)[0],
                        media_url=f"file://{fpath}",
                        description=f"Auto-detected from watch folder: {fname}",
                        metadata_json=json.dumps({"local_path": fpath, "file_size": file_stat.st_size}),
                        ingestion_status="PENDING"
                    )
                    db.add(feed_item)
                    await db.flush()

                    content = await self._ingest_local_file(db, source, feed_item, fpath, fname)
                    feed_item.content_id = content.id
                    feed_item.ingestion_status = "INGESTED"
                    new_items_count += 1
                    ingested_items.append({
                        "feed_item_id": feed_item.id,
                        "content_id": content.id,
                        "title": feed_item.title
                    })

                source.last_polled_at = datetime.utcnow()
                await db.commit()

            else:
                logger.info(f"Source type '{source.source_type}' queued for scheduled adapter.")

        except Exception as e:
            logger.error(f"Error polling source '{source.name}': {e}", exc_info=True)
            await db.rollback()
            raise

        return {
            "status": "success",
            "source_id": source.id,
            "source_name": source.name,
            "new_items_count": new_items_count,
            "ingested_items": ingested_items
        }

    async def _ingest_audio_item(self, db: AsyncSession, source: InboundSource, feed_item: SourceFeedItem, ep_data: Dict[str, Any]) -> Content:
        """Downloads audio file and initializes Content + Asset + Transcription job."""
        content_id = f"cnt_{uuid.uuid4().hex[:12]}"
        asset_id = f"ast_{uuid.uuid4().hex[:12]}"

        # Download remote audio
        download_res = await podcast_ingestion_service.download_episode_audio(
            media_url=ep_data["media_url"],
            content_id=content_id,
            asset_id=asset_id
        )

        content = Content(
            id=content_id,
            title=ep_data["title"],
            content_type="AUDIO",
            status="READY",
            text_content=ep_data.get("description", "")
        )
        db.add(content)

        asset = Asset(
            id=asset_id,
            content_id=content_id,
            original_filename=download_res["filename"],
            storage_key=download_res["storage_key"],
            mime_type=ep_data.get("mime_type", "audio/mpeg"),
            file_size=download_res["file_size"],
            duration=ep_data.get("duration_seconds")
        )
        db.add(asset)
        await db.flush()

        logger.info(f"Created Content {content_id} from podcast episode '{ep_data['title']}'")
        return content

    async def _ingest_local_file(self, db: AsyncSession, source: InboundSource, feed_item: SourceFeedItem, fpath: str, fname: str) -> Content:
        """Copies local watched file into Reflow storage and creates Content."""
        content_id = f"cnt_{uuid.uuid4().hex[:12]}"
        asset_id = f"ast_{uuid.uuid4().hex[:12]}"

        is_video = fname.lower().endswith((".mp4", ".mov", ".mkv"))
        content_type = "VIDEO" if is_video else "AUDIO"
        mime_type = "video/mp4" if is_video else "audio/mpeg"

        storage_key = f"content/{content_id}/original/{asset_id}_{fname}"
        full_dest_path = storage_service.get_full_path(storage_key)
        os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)

        with open(fpath, "rb") as src_f, open(full_dest_path, "wb") as dst_f:
            while chunk := src_f.read(65536):
                dst_f.write(chunk)

        content = Content(
            id=content_id,
            title=os.path.splitext(fname)[0],
            content_type=content_type,
            status="READY"
        )
        db.add(content)

        asset = Asset(
            id=asset_id,
            content_id=content_id,
            original_filename=fname,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=os.path.getsize(full_dest_path)
        )
        db.add(asset)
        await db.flush()

        logger.info(f"Ingested watched file '{fname}' -> Content {content_id}")
        return content

source_ingestion_service = SourceIngestionService()
