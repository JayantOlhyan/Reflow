import os
import json
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from config import settings
from database import async_session_factory
from models.entities import Content, Asset, ContentVariant, Clip, ClipVariant, Carousel, CarouselSlide, CarouselExport, PlatformConnection, Publication, Job
from services.encryption_service import encryption_service
from services.media_service import media_processor
from services.storage_service import storage_service
from connectors.youtube import youtube_connector, youtube_oauth
from connectors.instagram import instagram_connector, instagram_oauth
from connectors.linkedin import linkedin_connector, linkedin_oauth
from connectors.x_twitter import x_connector, x_oauth
from connectors.facebook import facebook_connector, facebook_oauth
from connectors.tiktok import tiktok_connector, tiktok_oauth
from connectors.pinterest import pinterest_connector, pinterest_oauth
from connectors.threads import threads_connector, threads_oauth
from utils.logging import get_logger

logger = get_logger("PublishingService")

class PublishingService:
    def __init__(self):
        # In-memory single-use OAuth states with expiration
        self._oauth_states: Dict[str, Tuple[str, datetime]] = {} # state -> (platform, expires_at)
        
        # Connector registry
        self.connectors = {
            "youtube": youtube_connector,
            "instagram": instagram_connector,
            "linkedin": linkedin_connector,
            "x": x_connector,
            "facebook": facebook_connector,
            "tiktok": tiktok_connector,
            "pinterest": pinterest_connector,
            "threads": threads_connector
        }
        
        # OAuth provider registry
        self.oauth_providers = {
            "youtube": youtube_oauth,
            "instagram": instagram_oauth,
            "linkedin": linkedin_oauth,
            "x": x_oauth,
            "facebook": facebook_oauth,
            "tiktok": tiktok_oauth,
            "pinterest": pinterest_oauth,
            "threads": threads_oauth
        }

    def get_connector(self, platform: str):
        return self.connectors.get(platform.lower())

    def get_oauth_provider(self, platform: str):
        return self.oauth_providers.get(platform.lower())

    def create_oauth_state(self, platform: str, ttl_minutes: int = 15) -> str:
        """Generates an unpredictable single-use CSRF OAuth state token."""
        state = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        self._oauth_states[state] = (platform.lower(), expires_at)
        return state

    def validate_and_consume_oauth_state(self, state: str, expected_platform: str) -> bool:
        """Validates that an OAuth state is present, unexpired, and single-use."""
        if not state or state not in self._oauth_states:
            logger.warning(f"OAuth state rejected: unknown or already consumed ({state})")
            return False

        platform, expires_at = self._oauth_states.pop(state)
        if datetime.utcnow() > expires_at:
            logger.warning(f"OAuth state rejected: expired ({state})")
            return False

        if platform.lower() != expected_platform.lower():
            logger.warning(f"OAuth state platform mismatch: expected {expected_platform}, got {platform}")
            return False

        return True

    def compute_idempotency_hash(
        self,
        content_id: str,
        variant_id: Optional[str],
        platform_connection_id: str,
        title: str,
        privacy: str
    ) -> str:
        """Computes deterministic SHA-256 hash for publication intent to prevent duplicate posts."""
        raw_key = f"{content_id}:{variant_id or 'none'}:{platform_connection_id}:{title.strip()}:{privacy.upper()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def get_valid_access_token(self, connection: PlatformConnection, session: Any) -> str:
        """
        Retrieves the decrypted access token for a connection, refreshing automatically if expired.
        """
        if not connection.access_token_encrypted:
            connection.status = "REAUTH_REQUIRED"
            await session.commit()
            raise PermissionError("Connection has no credentials. Reauthentication required.")

        access_token = encryption_service.decrypt_token(connection.access_token_encrypted)
        refresh_token = encryption_service.decrypt_token(connection.refresh_token_encrypted) if connection.refresh_token_encrypted else None

        # Check token expiration
        is_expired = False
        if connection.token_expires_at:
            # Refresh 5 minutes before actual expiration
            if datetime.utcnow() >= connection.token_expires_at - timedelta(minutes=5):
                is_expired = True

        if is_expired:
            if not refresh_token:
                connection.status = "REAUTH_REQUIRED"
                await session.commit()
                raise PermissionError("Access token expired and no refresh token present. Reauthentication required.")

            logger.info(f"Access token for connection {connection.id} ({connection.platform}) is expired. Refreshing token...")
            provider = self.get_oauth_provider(connection.platform)
            if not provider:
                raise NotImplementedError(f"OAuth provider for platform {connection.platform} is not available.")

            try:
                token_data = await provider.refresh_token(refresh_token)
                new_access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)

                connection.access_token_encrypted = encryption_service.encrypt_token(new_access_token)
                connection.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                connection.status = "CONNECTED"
                connection.updated_at = datetime.utcnow()
                await session.commit()
                return new_access_token
            except Exception as e:
                connection.status = "REAUTH_REQUIRED"
                await session.commit()
                logger.error(f"Failed to refresh token for connection {connection.id}: {e}")
                raise PermissionError(f"Token refresh failed: {e}")

        return access_token

    async def execute_publication_job(self, publication_id: str) -> Dict[str, Any]:
        """
        Executes publication to the external platform asynchronously from worker:
        1. Validates connection & publication state
        2. Routes media based on content/variant type (Video, Image, Carousel, Text)
        3. Obtains valid access token (refreshing if needed)
        4. Updates status to UPLOADING
        5. Calls platform connector
        6. Receives real external post ID & URL
        7. Persists PUBLISHED state
        """
        async with async_session_factory() as session:
            pub_res = await session.execute(
                select(Publication).options(selectinload(Publication.connection)).where(Publication.id == publication_id)
            )
            publication = pub_res.scalar_one_or_none()
            if not publication:
                raise ValueError(f"Publication {publication_id} not found.")

            if publication.status == "PUBLISHED":
                logger.info(f"Publication {publication_id} is already PUBLISHED. Idempotent return.")
                return {"status": "published", "external_post_id": publication.external_post_id, "external_url": publication.external_url}

            # Run Quality Control Validation Pipeline
            from services.quality_control_service import quality_control_service
            from models.entities import GovernanceOverride
            qc_result = await quality_control_service.run_pipeline(
                session=session,
                content_id=publication.content_id,
                variant_id=publication.variant_id,
                publication_id=publication.id,
                platform=publication.platform
            )

            if qc_result["status"] == "BLOCKED":
                publication.status = "FAILED"
                publication.error_code = "GOVERNANCE_BLOCKED"
                publication.error_message = "Publishing blocked by governance policy."
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise ValueError("Publishing blocked by governance policy.")
            elif qc_result["status"] == "PASS_WITH_WARNINGS":
                # Ensure all warnings are overridden
                warning_checks = [
                    c for c in qc_result["checks"]
                    if c.status == "WARNING" or (c.status == "FAILED" and c.severity == "WARNING")
                ]
                overridden_count = 0
                for wc in warning_checks:
                    ov_res = await session.execute(
                        select(GovernanceOverride).where(GovernanceOverride.quality_check_id == wc.id)
                    )
                    if ov_res.scalar_one_or_none():
                        overridden_count += 1
                if overridden_count < len(warning_checks):
                    publication.status = "FAILED"
                    publication.error_code = "GOVERNANCE_WARNING"
                    publication.error_message = "Publishing blocked by unresolved governance warnings."
                    publication.updated_at = datetime.utcnow()
                    await session.commit()
                    raise ValueError("Publishing blocked by unresolved governance warnings.")

            connection = publication.connection
            if not connection or connection.status != "CONNECTED":
                publication.status = "FAILED"
                publication.error_code = "AUTH_ERROR"
                publication.error_message = "Platform connection is missing or not in CONNECTED state."
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise PermissionError(publication.error_message)

            connector = self.get_connector(publication.platform)
            if not connector:
                publication.status = "FAILED"
                publication.error_code = "NOT_IMPLEMENTED"
                publication.error_message = f"Platform '{publication.platform}' has no registered connector."
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise NotImplementedError(publication.error_message)

            # Get Decrypted Access Token
            try:
                access_token = await self.get_valid_access_token(connection, session)
            except Exception as e:
                publication.status = "REAUTH_REQUIRED"
                publication.error_code = "AUTH_ERROR"
                publication.error_message = str(e)
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise

            # Determine Media Modality and Path
            media_path = None
            carousel_images: List[str] = []
            is_carousel = False
            is_pure_text = False

            if publication.variant_id:
                # Check ClipVariant
                var_res = await session.execute(select(ClipVariant).where(ClipVariant.id == publication.variant_id))
                var = var_res.scalar_one_or_none()
                if var:
                    media_path = storage_service.get_real_path(var.storage_key)
                else:
                    # Check ContentVariant
                    cvar_res = await session.execute(select(ContentVariant).where(ContentVariant.id == publication.variant_id))
                    cvar = cvar_res.scalar_one_or_none()
                    if cvar:
                        media_path = storage_service.get_real_path(cvar.storage_key)

            if not media_path:
                # Check if it is a Carousel export
                car_res = await session.execute(
                    select(Carousel).options(selectinload(Carousel.exports), selectinload(Carousel.slides)).where(Carousel.content_id == publication.content_id)
                )
                carousel = car_res.scalar_one_or_none()
                if carousel and carousel.exports:
                    png_exports = [e for e in carousel.exports if e.export_type == "PNG"]
                    if png_exports:
                        is_carousel = True
                        for exp in png_exports:
                            p = storage_service.get_real_path(exp.storage_key)
                            if os.path.exists(p):
                                carousel_images.append(p)

            if not media_path and not is_carousel:
                # Fallback to original content asset
                cnt_res = await session.execute(
                    select(Content).options(selectinload(Content.assets)).where(Content.id == publication.content_id)
                )
                cnt = cnt_res.scalar_one_or_none()
                if cnt and cnt.assets:
                    media_path = storage_service.get_real_path(cnt.assets[0].storage_key)
                elif cnt and cnt.content_type == "TEXT":
                    is_pure_text = True

            # If connector supports text and no media, publish text
            caps = connector.get_capabilities()
            if not media_path and not is_carousel and caps.text_post:
                is_pure_text = True

            # Pre-upload verification for video
            if media_path and not is_carousel and not is_pure_text:
                if not os.path.exists(media_path):
                    publication.status = "FAILED"
                    publication.error_code = "MEDIA_ERROR"
                    publication.error_message = f"Physical media file missing: {media_path}"
                    publication.updated_at = datetime.utcnow()
                    await session.commit()
                    raise FileNotFoundError(publication.error_message)

                if media_path.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                    try:
                        meta = await media_processor.probe_media(media_path)
                        if not meta.get("codec") and not meta.get("width"):
                            raise ValueError("FFprobe did not find valid video stream in media file.")
                    except Exception as e:
                        publication.status = "FAILED"
                        publication.error_code = "MEDIA_ERROR"
                        publication.error_message = f"Media validation failed: {e}"
                        publication.updated_at = datetime.utcnow()
                        await session.commit()
                        raise

            # Update status to UPLOADING
            publication.status = "UPLOADING"
            publication.attempt_count += 1
            publication.updated_at = datetime.utcnow()
            await session.commit()

            # Dispatch to appropriate connector publish method
            metadata_payload = {
                "title": publication.title,
                "description": publication.description,
                "caption": publication.description,
                "tags": publication.tags,
                "privacy": publication.privacy,
                "external_account_id": connection.external_account_id
            }

            try:
                if is_pure_text and caps.text_post:
                    result = await connector.publish_text(metadata=metadata_payload, access_token=access_token)
                elif is_carousel and caps.carousel_upload and carousel_images:
                    result = await connector.publish_carousel(image_paths=carousel_images, metadata=metadata_payload, access_token=access_token)
                elif media_path and media_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and caps.image_upload:
                    result = await connector.publish_image(image_path=media_path, metadata=metadata_payload, access_token=access_token)
                elif media_path and caps.video_upload:
                    result = await connector.publish_video(video_path=media_path, metadata=metadata_payload, access_token=access_token)
                elif caps.text_post:
                    result = await connector.publish_text(metadata=metadata_payload, access_token=access_token)
                else:
                    raise NotImplementedError(f"No compatible publish method for platform {publication.platform} with the provided asset type.")

                publication.status = "PUBLISHED"
                publication.external_post_id = result.get("external_post_id")
                publication.external_url = result.get("external_url")
                publication.published_at = datetime.utcnow()
                publication.error_code = None
                publication.error_message = None
                publication.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"Publication {publication_id} on {publication.platform} succeeded -> {publication.external_url}")
                return result

            except PermissionError as e:
                publication.status = "REAUTH_REQUIRED"
                publication.error_code = "AUTH_ERROR"
                publication.error_message = str(e)
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise
            except ResourceWarning as e:
                publication.status = "FAILED"
                publication.error_code = "RATE_LIMIT"
                publication.error_message = str(e)
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise
            except NotImplementedError as e:
                publication.status = "FAILED"
                publication.error_code = "NOT_IMPLEMENTED"
                publication.error_message = str(e)
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise
            except Exception as e:
                publication.status = "FAILED"
                publication.error_code = "PLATFORM_ERROR"
                publication.error_message = str(e)
                publication.updated_at = datetime.utcnow()
                await session.commit()
                raise

publishing_service = PublishingService()
