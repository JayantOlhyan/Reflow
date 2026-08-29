import os
import json
import asyncio
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities, not_implemented_response
from utils.logging import get_logger

logger = get_logger("InstagramConnector")

class InstagramOAuthProvider(BaseOAuthProvider):
    platform_id = "instagram"

    def __init__(self):
        self.client_id = settings.META_CLIENT_ID or ""
        self.client_secret = settings.META_CLIENT_SECRET or ""
        self.redirect_uri = settings.INSTAGRAM_REDIRECT_URI
        self.scopes = settings.INSTAGRAM_SCOPES

    def get_authorization_url(self, state: str) -> str:
        """Constructs Meta / Instagram Graph API OAuth consent URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.scopes),
            "state": state
        }
        return f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchanges authorization code for short-lived token, then fetches long-lived token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code
                }
            )
            if resp.status_code != 200:
                logger.error(f"Instagram OAuth code exchange failed: {resp.status_code} {resp.text}")
                raise ValueError(f"OAuth code exchange failed: {resp.status_code}")

            short_token = resp.json().get("access_token")

            # Exchange for long-lived 60-day token
            long_resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "fb_exchange_token": short_token
                }
            )
            if long_resp.status_code == 200:
                data = long_resp.json()
                return {
                    "access_token": data.get("access_token"),
                    "expires_in": data.get("expires_in", 5184000), # 60 days
                    "token_type": "Bearer"
                }
            return resp.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes a long-lived access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "fb_exchange_token": refresh_token
                }
            )
            if resp.status_code != 200:
                raise ValueError(f"Instagram token refresh failed: {resp.status_code}")
            return resp.json()

    async def revoke_token(self, token: str) -> bool:
        """Revokes permissions on Meta Graph API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.delete(
                    f"https://graph.facebook.com/v19.0/me/permissions",
                    params={"access_token": token}
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """Retrieves linked Instagram Business Account identity."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/me/accounts",
                params={
                    "fields": "name,instagram_business_account{id,username,profile_picture_url}",
                    "access_token": access_token
                }
            )
            if resp.status_code != 200:
                raise ValueError(f"Failed to lookup Instagram account: {resp.status_code}")

            data = resp.json().get("data", [])
            for page in data:
                ig_acc = page.get("instagram_business_account")
                if ig_acc:
                    return {
                        "external_account_id": ig_acc.get("id"),
                        "account_name": page.get("name", "Instagram Account"),
                        "handle": f"@{ig_acc.get('username')}" if ig_acc.get('username') else "",
                        "avatar_url": ig_acc.get("profile_picture_url", ""),
                        "metadata": {"page_id": page.get("id")}
                    }

            # Fallback if no linked business account found
            raise ValueError("No Instagram Professional/Business account linked to this Meta login.")

class InstagramConnector(BasePlatformConnector):
    platform_id = "instagram"
    platform_name = "Instagram"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            carousel_upload=True,
            text_post=False,
            scheduled_publish=True,
            supported_aspect_ratios=["9:16", "1:1", "4:5"],
            supported_containers=["mp4", "mov"],
            max_video_size_mb=300,
            max_title_length=100,
            max_description_length=2200,
            max_images_per_carousel=10
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        desc = metadata.get("description") or metadata.get("caption") or ""
        if len(desc) > 2200:
            return False, f"Instagram caption exceeds 2200 characters ({len(desc)} chars)."
        return True, None

    async def publish_video(
        self,
        video_path: str,
        metadata: Dict[str, Any],
        access_token: str,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Publishes a 9:16 Reel to Instagram using the 3-step Graph API container workflow.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file missing: {video_path}")

        valid, err = self.validate_metadata(metadata)
        if not valid:
            raise ValueError(err)

        caption = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        tags = metadata.get("tags", [])
        if tags and "#" not in caption:
            tag_str = " ".join([f"#{t.lstrip('#')}" for t in tags])
            caption = f"{caption}\n\n{tag_str}".strip()

        # Step 1: Create Media Container for Reel
        async with httpx.AsyncClient(timeout=120.0) as client:
            container_resp = await client.post(
                "https://graph.facebook.com/v19.0/me/media",
                data={
                    "media_type": "REELS",
                    "caption": caption,
                    "access_token": access_token
                }
            )
            if container_resp.status_code not in [200, 201]:
                if container_resp.status_code in [401, 403]:
                    raise PermissionError(f"Instagram authorization error: {container_resp.text}")
                elif container_resp.status_code == 429:
                    raise ResourceWarning(f"Instagram rate limit reached: {container_resp.text}")
                raise ValueError(f"Failed to create Instagram container ({container_resp.status_code}): {container_resp.text}")

            creation_id = container_resp.json().get("id")
            if not creation_id:
                raise ValueError("Instagram API did not return container creation ID.")

            # Step 2: Poll Container Status
            for _ in range(30):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    f"https://graph.facebook.com/v19.0/{creation_id}",
                    params={"fields": "status_code", "access_token": access_token}
                )
                if status_resp.status_code == 200:
                    status_code = status_resp.json().get("status_code")
                    if status_code == "FINISHED":
                        break
                    elif status_code == "ERROR":
                        raise ValueError(f"Instagram container processing failed: {status_resp.text}")

            # Step 3: Publish Media Container
            publish_resp = await client.post(
                "https://graph.facebook.com/v19.0/me/media_publish",
                data={"creation_id": creation_id, "access_token": access_token}
            )
            if publish_resp.status_code not in [200, 201]:
                raise ValueError(f"Instagram media publish failed ({publish_resp.status_code}): {publish_resp.text}")

            media_id = publish_resp.json().get("id")
            external_url = f"https://www.instagram.com/p/{media_id}"
            logger.info(f"Published Instagram Reel: {media_id} -> {external_url}")

            return {
                "status": "published",
                "external_post_id": media_id,
                "external_url": external_url,
                "raw_response": publish_resp.json()
            }

    async def publish_image(
        self,
        image_path: str,
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a single photo post to Instagram."""
        caption = metadata.get("description") or metadata.get("caption", "")
        async with httpx.AsyncClient(timeout=60.0) as client:
            container_resp = await client.post(
                "https://graph.facebook.com/v19.0/me/media",
                data={"image_url": image_path, "caption": caption, "access_token": access_token}
            )
            if container_resp.status_code not in [200, 201]:
                raise ValueError(f"Failed to create Instagram photo container: {container_resp.text}")

            creation_id = container_resp.json().get("id")
            publish_resp = await client.post(
                "https://graph.facebook.com/v19.0/me/media_publish",
                data={"creation_id": creation_id, "access_token": access_token}
            )
            media_id = publish_resp.json().get("id")
            return {
                "status": "published",
                "external_post_id": media_id,
                "external_url": f"https://www.instagram.com/p/{media_id}"
            }

    async def publish_carousel(
        self,
        image_paths: List[str],
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a multi-image carousel to Instagram."""
        if not image_paths:
            raise ValueError("No slide images provided for Instagram carousel.")

        caption = metadata.get("description") or metadata.get("caption", "")
        children_ids = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            # 1. Create sub-containers for each slide
            for idx, img_path in enumerate(image_paths[:10]):
                sub_resp = await client.post(
                    "https://graph.facebook.com/v19.0/me/media",
                    data={"image_url": img_path, "is_carousel_item": "true", "access_token": access_token}
                )
                if sub_resp.status_code in [200, 201]:
                    children_ids.append(sub_resp.json().get("id"))

            if not children_ids:
                raise ValueError("Failed to create carousel slide containers on Instagram.")

            # 2. Create parent carousel container
            parent_resp = await client.post(
                "https://graph.facebook.com/v19.0/me/media",
                data={
                    "media_type": "CAROUSEL",
                    "caption": caption,
                    "children": ",".join(children_ids),
                    "access_token": access_token
                }
            )
            parent_id = parent_resp.json().get("id")

            # 3. Publish carousel
            pub_resp = await client.post(
                "https://graph.facebook.com/v19.0/me/media_publish",
                data={"creation_id": parent_id, "access_token": access_token}
            )
            media_id = pub_resp.json().get("id")
            return {
                "status": "published",
                "external_post_id": media_id,
                "external_url": f"https://www.instagram.com/p/{media_id}"
            }

instagram_oauth = InstagramOAuthProvider()
instagram_connector = InstagramConnector()
