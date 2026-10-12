import os
import uuid
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from utils.logging import get_logger
from utils.security import is_safe_external_url
from services.storage_service import storage_service

logger = get_logger("PodcastIngestionService")

class PodcastIngestionService:
    """
    Ingests podcasts from RSS 2.0 / iTunes XML feeds.
    Parses channel metadata, detects new audio episodes, validates media enclosures,
    and downloads audio into Reflow storage.
    """

    ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

    async def fetch_and_parse_feed(self, feed_url: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fetches an RSS feed, enforces SSRF validation, and extracts channel + episode metadata.
        """
        is_safe, error = is_safe_external_url(feed_url)
        if not is_safe:
            logger.error(f"Blocked unsafe podcast feed URL '{feed_url}': {error}")
            raise ValueError(f"Security check failed for podcast feed: {error}")

        headers = {
            "User-Agent": "Reflow-Podcast-Ingester/1.0 (+https://github.com/JayantOlhyan/Reflow)"
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(feed_url, headers=headers)
            response.raise_for_status()
            xml_text = response.text

        return self.parse_feed_xml(xml_text, limit=limit)

    def parse_feed_xml(self, xml_content: str, limit: int = 10) -> Dict[str, Any]:
        """
        Parses raw RSS XML content and extracts channel info and episodes.
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"XML parse error for podcast feed: {e}")
            raise ValueError(f"Malformed podcast RSS XML: {e}")

        channel = root.find("channel")
        if channel is None:
            raise ValueError("Invalid RSS feed: missing <channel> element.")

        channel_title = (channel.findtext("title") or "Untitled Podcast").strip()
        channel_desc = (channel.findtext("description") or "").strip()
        channel_link = (channel.findtext("link") or "").strip()

        # Channel image
        channel_image_url = ""
        itunes_image = channel.find(f"{self.ITUNES_NS}image")
        if itunes_image is not None and "href" in itunes_image.attrib:
            channel_image_url = itunes_image.attrib["href"]
        else:
            img = channel.find("image")
            if img is not None:
                channel_image_url = img.findtext("url") or ""

        episodes: List[Dict[str, Any]] = []

        for item in channel.findall("item"):
            if len(episodes) >= limit:
                break

            title = (item.findtext("title") or "Untitled Episode").strip()
            desc = (item.findtext("description") or "").strip()
            guid = (item.findtext("guid") or "").strip()
            pub_date_str = (item.findtext("pubDate") or "").strip()

            # Find media enclosure
            enclosure = item.find("enclosure")
            media_url = ""
            media_type = "audio/mpeg"
            media_length = 0

            if enclosure is not None:
                media_url = enclosure.attrib.get("url", "").strip()
                media_type = enclosure.attrib.get("type", "audio/mpeg").strip()
                try:
                    media_length = int(enclosure.attrib.get("length", 0))
                except ValueError:
                    media_length = 0

            # Fallback guid
            if not guid:
                guid = media_url or title

            if not media_url:
                continue # Skip items without media

            # Duration from itunes tag
            duration_str = item.findtext(f"{self.ITUNES_NS}duration") or ""
            duration_seconds = self._parse_duration(duration_str)

            # Episode image
            ep_image = ""
            ep_itunes_img = item.find(f"{self.ITUNES_NS}image")
            if ep_itunes_img is not None and "href" in ep_itunes_img.attrib:
                ep_image = ep_itunes_img.attrib["href"]
            else:
                ep_image = channel_image_url

            episodes.append({
                "guid": guid,
                "title": title,
                "description": desc,
                "media_url": media_url,
                "mime_type": media_type,
                "file_size": media_length,
                "duration_seconds": duration_seconds,
                "published_at_str": pub_date_str,
                "image_url": ep_image
            })

        return {
            "title": channel_title,
            "description": channel_desc,
            "link": channel_link,
            "image_url": channel_image_url,
            "episode_count": len(episodes),
            "episodes": episodes
        }

    async def download_episode_audio(self, media_url: str, content_id: str, asset_id: str) -> Dict[str, Any]:
        """
        Downloads the remote audio file securely into local Reflow storage.
        """
        is_safe, error = is_safe_external_url(media_url)
        if not is_safe:
            raise ValueError(f"Unsafe media URL '{media_url}': {error}")

        parsed = urlparse(media_url)
        filename = os.path.basename(parsed.path) or f"{asset_id}.mp3"
        if not any(filename.lower().endswith(ext) for ext in [".mp3", ".m4a", ".wav", ".aac", ".ogg", ".mp4"]):
            filename = f"{filename}.mp3"

        storage_key = f"content/{content_id}/original/{asset_id}_{filename}"
        full_dest_path = storage_service.get_full_path(storage_key)
        os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)

        headers = {
            "User-Agent": "Reflow-Podcast-Ingester/1.0"
        }

        bytes_written = 0
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", media_url, headers=headers) as response:
                response.raise_for_status()
                with open(full_dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        bytes_written += len(chunk)

        logger.info(f"Downloaded podcast episode audio ({bytes_written} bytes) -> {storage_key}")

        return {
            "storage_key": storage_key,
            "filename": filename,
            "file_size": bytes_written,
            "full_path": full_dest_path
        }

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        if not duration_str:
            return None
        parts = duration_str.strip().split(":")
        try:
            if len(parts) == 3: # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2: # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1: # seconds
                return int(float(parts[0]))
        except ValueError:
            return None
        return None

podcast_ingestion_service = PodcastIngestionService()
